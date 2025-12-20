"""
OCR Addon Manager
Manages multiple OCR engines for Quest Video Helper:
- Windows OCR (built-in, uses winocr package)
- Tesseract OCR (portable, requires download)
"""

import os
import sys
import subprocess
import threading
import asyncio
from typing import Callable, Optional, Tuple, List, Dict, Any
from PIL import Image

class OCREngine:
    """Base class for OCR engines"""
    
    def __init__(self):
        pass
    
    def is_available(self) -> bool:
        """Check if engine is available/installed"""
        raise NotImplementedError
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text from image"""
        raise NotImplementedError


class WindowsOCREngine(OCREngine):
    """
    Windows OCR using winocr package
    Available on Windows 10/11
    """
    
    def __init__(self):
        super().__init__()
        self._available = None
    
    def is_available(self) -> bool:
        """Check if Windows OCR is available"""
        if self._available is not None:
            return self._available
        
        # Check Windows version (Windows 10+) and winocr availability
        try:
            import platform
            version = platform.version()
            major = int(version.split('.')[0])
            
            if major < 10:
                self._available = False
                return False
            
            # Check if winocr is importable
            try:
                import winocr
                self._available = True
            except ImportError:
                # winocr not installed, but Windows OCR might still work
                # Mark as available, will install on demand
                self._available = True
                
        except Exception as e:
            print(f"[WindowsOCR] Availability check error: {e}")
            self._available = False
        
        return self._available
    
    def _ensure_winocr(self) -> bool:
        """Ensure winocr is installed"""
        try:
            import winocr
            return True
        except ImportError:
            # Try to install
            try:
                print("[WindowsOCR] Installing winocr...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "winocr", "--quiet"],
                    capture_output=True,
                    timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                import winocr
                return True
            except Exception as e:
                print(f"[WindowsOCR] Failed to install winocr: {e}")
                return False
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text using Windows OCR via winocr"""
        print(f"[WindowsOCR] extract_text called, image size: {image.size}")
        
        if not self.is_available():
            print("[WindowsOCR] Not available!")
            raise RuntimeError("Windows OCR not available")
        
        if not self._ensure_winocr():
            print("[WindowsOCR] winocr not available, trying fallback...")
            return self._extract_text_fallback(image)
        
        try:
            import winocr
            print("[WindowsOCR] winocr imported successfully")
            
            # winocr.recognize_pil is async, need to run in event loop
            async def do_ocr():
                print("[WindowsOCR] Running OCR async...")
                result = await winocr.recognize_pil(image, lang='en')
                print(f"[WindowsOCR] OCR result type: {type(result)}")
                return result
            
            # Run async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            print("[WindowsOCR] Running event loop...")
            result = loop.run_until_complete(do_ocr())
            print(f"[WindowsOCR] Result: {result}")
            
            # Extract text from result
            if result and hasattr(result, 'text'):
                text = result.text.strip()
                print(f"[WindowsOCR] Extracted (result.text): '{text}'")
                return text
            elif isinstance(result, dict) and 'text' in result:
                text = result['text'].strip()
                print(f"[WindowsOCR] Extracted (dict): '{text}'")
                return text
            elif isinstance(result, str):
                text = result.strip()
                print(f"[WindowsOCR] Extracted (str): '{text}'")
                return text
            
            # Try getting lines
            if hasattr(result, 'lines'):
                texts = [line.text for line in result.lines if hasattr(line, 'text')]
                text = ' '.join(texts).strip()
                print(f"[WindowsOCR] Extracted (lines): '{text}'")
                return text
            
            text = str(result).strip() if result else ""
            print(f"[WindowsOCR] Extracted (fallback str): '{text}'")
            return text
            
        except Exception as e:
            print(f"[WindowsOCR] Error: {e}")
            import traceback
            traceback.print_exc()
            return self._extract_text_fallback(image)
    
    def _extract_text_fallback(self, image: Image.Image) -> str:
        """Fallback: try using pytesseract if available"""
        try:
            import pytesseract
            return pytesseract.image_to_string(image, lang='eng+chi_sim')
        except ImportError:
            print("[WindowsOCR] Fallback pytesseract not available")
            return ""
        except Exception as e:
            print(f"[WindowsOCR] Fallback error: {e}")
            return ""


class TesseractEngine(OCREngine):
    """
    Tesseract OCR - portable version
    Requires download but works offline
    """
    
    def __init__(self):
        super().__init__()
        self._tesseract_path = self._get_addon_path()
    
    def _get_addon_path(self) -> str:
        """Get path to tesseract addon folder"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "addons", "tesseract")
    
    def _get_tesseract_exe(self) -> Optional[str]:
        """Get path to tesseract.exe"""
        exe_path = os.path.join(self._tesseract_path, "tesseract.exe")
        if os.path.exists(exe_path):
            return exe_path
        return None
    
    def is_available(self) -> bool:
        """Check if Tesseract is installed (executable or pytesseract)"""
        if self._get_tesseract_exe() is not None:
            return True
        
        # Check pytesseract fallback
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except:
            return False
    
    def get_download_size(self) -> str:
        """Get estimated download size"""
        return "~40 MB"
    
    def install(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> bool:
        """Download and install portable Tesseract automatically"""
        try:
            import urllib.request
            import zipfile
            import shutil
            
            addon_path = self._get_addon_path()
            os.makedirs(addon_path, exist_ok=True)
            
            if progress_callback:
                progress_callback("Đang cài đặt pytesseract...", 10)
            
            # Install pytesseract package first
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "pytesseract", "--quiet"],
                capture_output=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if progress_callback:
                progress_callback("Đang tải Tesseract OCR...", 20)
            
            # Check if portable tesseract already exists
            tesseract_exe = os.path.join(addon_path, "tesseract.exe")
            
            if not os.path.exists(tesseract_exe):
                # Download portable tesseract from our server
                try:
                    # Primary: Use npapi.io server
                    # Fallback: Use refresh_server_url() from config
                    server_urls_to_try = [
                        "https://npapi.io",  # New primary server
                    ]
                    
                    # Add dynamic server URL as fallback
                    try:
                        from core.config import refresh_server_url
                        dynamic_url = refresh_server_url()
                        if dynamic_url and dynamic_url not in server_urls_to_try:
                            server_urls_to_try.append(dynamic_url)
                    except Exception as e:
                        print(f"[Tesseract] Could not get dynamic server URL: {e}")
                    
                    download_success = False
                    last_error = None
                    
                    for server_url in server_urls_to_try:
                        try:
                            portable_url = f"{server_url}/addons/tesseract-portable.zip"
                            print(f"[Tesseract] Trying download from: {portable_url}")
                            
                            if progress_callback:
                                progress_callback(f"Đang thử tải từ server {server_urls_to_try.index(server_url) + 1}...", 30)
                            
                            zip_path = os.path.join(addon_path, "tesseract-portable.zip")
                            
                            # Download with progress
                            def download_progress(block_num, block_size, total_size):
                                if total_size > 0:
                                    percent = min(30 + int(block_num * block_size * 50 / total_size), 80)
                                    if progress_callback:
                                        progress_callback(f"Đang tải... {percent}%", percent)
                            
                            urllib.request.urlretrieve(portable_url, zip_path, download_progress)
                            download_success = True
                            print(f"[Tesseract] Download successful from {server_url}")
                            break
                            
                        except Exception as e:
                            last_error = e
                            print(f"[Tesseract] Failed download from {server_url}: {e}")
                            continue

                    if not download_success:
                        raise last_error or Exception("All download servers failed")
                    
                    if progress_callback:
                        progress_callback("Đang giải nén...", 85)
                    
                    # Extract zip
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(addon_path)
                    
                    # Handle nested folder - move contents up if needed
                    # Check if tesseract.exe is in a subfolder
                    if not os.path.exists(tesseract_exe):
                        # Look for tesseract.exe in subfolders
                        for root, dirs, files in os.walk(addon_path):
                            if "tesseract.exe" in files:
                                # Move all files from this folder to addon_path
                                for item in os.listdir(root):
                                    src = os.path.join(root, item)
                                    dst = os.path.join(addon_path, item)
                                    if not os.path.exists(dst):
                                        shutil.move(src, dst)
                                break
                    
                    # Clean up zip
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    
                    print(f"[Tesseract] Extracted to: {addon_path}")
                    print(f"[Tesseract] tesseract.exe exists: {os.path.exists(tesseract_exe)}")
                    
                except Exception as e:
                    print(f"[Tesseract] Server download failed: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback: Try system tesseract
                    try:
                        import pytesseract
                        pytesseract.get_tesseract_version()
                        if progress_callback:
                            progress_callback("Sử dụng Tesseract hệ thống!", 100)
                        return True
                    except:
                        if progress_callback:
                            progress_callback("Không tải được Tesseract", 0)
                        return False
            
            # Verify installation
            if os.path.exists(tesseract_exe):
                # Configure pytesseract to use portable version
                try:
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = tesseract_exe
                    
                    if progress_callback:
                        progress_callback("Hoàn tất!", 100)
                    return True
                except Exception as e:
                    print(f"[Tesseract] Config error: {e}")
            
            # Final fallback - check system tesseract
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                if progress_callback:
                    progress_callback("Hoàn tất!", 100)
                return True
            except:
                if progress_callback:
                    progress_callback("Cần cài Tesseract thủ công", 0)
                return False
                
        except Exception as e:
            print(f"[Tesseract] Install error: {e}")
            if progress_callback:
                progress_callback(f"Lỗi: {str(e)[:50]}", 0)
            return False
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract text using Tesseract"""
        tesseract_exe = self._get_tesseract_exe()
        
        if tesseract_exe:
            return self._extract_with_portable(image, tesseract_exe)
        else:
            return self._extract_with_pytesseract(image)
    
    def _extract_with_portable(self, image: Image.Image, tesseract_exe: str) -> str:
        """Extract text using portable tesseract.exe"""
        try:
            import tempfile
            import uuid
            
            temp_input = os.path.join(tempfile.gettempdir(), f"tess_in_{uuid.uuid4().hex}.png")
            temp_output = os.path.join(tempfile.gettempdir(), f"tess_out_{uuid.uuid4().hex}")
            
            image.save(temp_input, "PNG")
            
            try:
                cmd = [tesseract_exe, temp_input, temp_output, "-l", "eng+chi_sim"]
                
                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                output_file = temp_output + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                
                return ""
                
            finally:
                for f in [temp_input, temp_output + ".txt"]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass
                        
        except Exception as e:
            print(f"[Tesseract] Extract error: {e}")
            return ""
    
    def _extract_with_pytesseract(self, image: Image.Image) -> str:
        """Extract text using pytesseract package"""
        try:
            import pytesseract
            return pytesseract.image_to_string(image, lang='eng+chi_sim')
        except ImportError:
            print("[Tesseract] pytesseract not installed")
            return ""
        except Exception as e:
            print(f"[Tesseract] pytesseract error: {e}")
            return ""


class OCRAddonManager:
    """Manage multiple OCR engines"""
    
    ENGINES = {
        "windows": {
            "name": "Windows OCR",
            "description": "Built-in Windows 10/11 OCR",
            "size": "~5 MB (tự động tải)",
            "requires_download": False,
        },
        "tesseract": {
            "name": "Tesseract OCR",
            "description": "Open-source OCR engine",
            "size": "~40 MB",
            "requires_download": True,
        }
    }
    
    def __init__(self):
        self._engines: Dict[str, OCREngine] = {
            "windows": WindowsOCREngine(),
            "tesseract": TesseractEngine(),
        }
        self._install_lock = threading.Lock()
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engine IDs"""
        return list(self.ENGINES.keys())
    
    def get_engine_info(self, engine_id: str) -> Dict[str, Any]:
        """Get engine info"""
        info = self.ENGINES.get(engine_id, {}).copy()
        info["is_ready"] = self.is_engine_ready(engine_id)
        return info
    
    def is_engine_ready(self, engine_id: str) -> bool:
        """Check if specific engine is ready to use"""
        engine = self._engines.get(engine_id)
        if engine:
            return engine.is_available()
        return False
    
    def get_status(self, engine_id: str = None) -> Tuple[bool, str]:
        """Get status of engine(s)"""
        if engine_id:
            info = self.get_engine_info(engine_id)
            if info.get("is_ready"):
                return True, f"✓ {info.get('name', engine_id)} sẵn sàng"
            return False, f"⚠ {info.get('name', engine_id)} chưa sẵn sàng"
        
        for eid in self._engines:
            if self.is_engine_ready(eid):
                info = self.ENGINES[eid]
                return True, f"✓ {info['name']} sẵn sàng"
        
        return False, "⚠ Chưa có OCR engine nào sẵn sàng"
    
    def is_installed(self) -> bool:
        """Check if any engine is ready (backward compatibility)"""
        return any(self.is_engine_ready(eid) for eid in self._engines)
    
    def install_engine(self, engine_id: str, 
                       progress_callback: Optional[Callable[[str, int], None]] = None) -> bool:
        """Install specific engine"""
        with self._install_lock:
            engine = self._engines.get(engine_id)
            
            if engine_id == "windows":
                # For Windows OCR, ensure winocr is installed
                if progress_callback:
                    progress_callback("Đang cài đặt winocr...", 30)
                
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "winocr", "--quiet"],
                        capture_output=True,
                        timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    if progress_callback:
                        progress_callback("Hoàn tất!", 100)
                    return True
                except Exception as e:
                    print(f"[WindowsOCR] Install error: {e}")
                    if progress_callback:
                        progress_callback(f"Lỗi: {str(e)[:40]}", 0)
                    return False
            
            elif engine_id == "tesseract":
                tess_engine: TesseractEngine = engine
                return tess_engine.install(progress_callback)
            
            return False
    
    def install_engine_async(self, engine_id: str,
                             progress_callback: Optional[Callable[[str, int], None]] = None,
                             on_complete: Optional[Callable[[bool], None]] = None) -> None:
        """Install engine asynchronously"""
        def task():
            result = self.install_engine(engine_id, progress_callback)
            if on_complete:
                on_complete(result)
        
        thread = threading.Thread(target=task, daemon=True)
        thread.start()
    
    def extract_text(self, image: Image.Image, engine_id: str = None, preprocess: bool = True) -> str:
        """Extract text from image using specified or available engine
        
        Args:
            image: PIL Image to extract text from
            engine_id: Specific engine to use, or None to auto-select
            preprocess: Whether to preprocess image for better small region detection
        """
        if engine_id is None:
            for eid in ["windows", "tesseract"]:
                if self.is_engine_ready(eid):
                    engine_id = eid
                    break
        
        if engine_id is None:
            raise RuntimeError("No OCR engine available")
        
        engine = self._engines.get(engine_id)
        if not engine:
            raise RuntimeError(f"Unknown engine: {engine_id}")
        
        # Preprocess image for better small region detection
        if preprocess:
            image = self._preprocess_image(image)
        
        return engine.extract_text(image)
    
    def extract_text_from_region(self, x: int, y: int, w: int, h: int, 
                                  engine_id: str = None) -> str:
        """Capture screen region and extract text"""
        try:
            import dxcam
            
            camera = dxcam.create(output_color="RGB")
            region = (x, y, x + w, y + h)
            frame = camera.grab(region=region)
            
            if frame is None:
                print("[OCRAddon] Failed to capture screen region")
                return ""
            
            image = Image.fromarray(frame)
            
            # Preprocess image for better OCR
            image = self._preprocess_image(image)
            
            # Debug: save captured image
            import tempfile
            debug_path = os.path.join(tempfile.gettempdir(), "ocr_debug.png")
            image.save(debug_path)
            print(f"[OCRAddon] Captured image saved to: {debug_path}")
            
            # Pass preprocess=False since we already preprocessed above
            return self.extract_text(image, engine_id, preprocess=False)
            
        except Exception as e:
            print(f"[OCRAddon] Capture error: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy:
        - Scale up small images (OCR works better on larger text)
        - Enhance contrast
        """
        from PIL import ImageEnhance
        
        original_size = image.size
        width, height = image.size
        
        # Scale up small images for better OCR
        # Very small regions need aggressive scaling
        MIN_HEIGHT = 100  # Reduced from 200 to handle smaller regions
        MIN_WIDTH = 50    # Also check width
        
        scale_factor = 1.0
        
        # Calculate scale based on smallest dimension
        if height < MIN_HEIGHT:
            scale_factor = max(scale_factor, MIN_HEIGHT / height)
        if width < MIN_WIDTH:
            scale_factor = max(scale_factor, MIN_WIDTH / width)
        
        # For very tiny regions, scale up even more
        if height < 30 or width < 30:
            scale_factor = max(scale_factor, 4.0)  # 4x minimum for tiny regions
        elif height < 50 or width < 50:
            scale_factor = max(scale_factor, 3.0)  # 3x for small regions
        
        if scale_factor > 1.0:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            # Use LANCZOS for high quality upscale
            image = image.resize((new_width, new_height), Image.LANCZOS)
            print(f"[OCRAddon] Scaled image from {original_size} to {image.size} (factor: {scale_factor:.1f}x)")
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # 1.5x contrast
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)  # 1.3x sharpness
        
        return image
