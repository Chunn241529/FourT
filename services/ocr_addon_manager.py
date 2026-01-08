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
import re
from typing import Callable, Optional, Tuple, List, Dict, Any
from PIL import Image, ImageEnhance, ImageOps
from utils.version import get_app_directory


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy:
    1. Convert to Grayscale
    2. Upscale (x2)
    3. Increase Contrast
    """
    try:
        # 1. Grayscale
        img = image.convert("L")

        # 2. Invert (White text on dark bg -> Black text on white bg)
        # Most game text is light on dark.
        img = ImageOps.invert(img)

        # 3. Upscale (x3) - Higher upscale for small text
        w, h = img.size
        # Cap max size
        if w < 2000 and h < 2000:
            img = img.resize((w * 3, h * 3), Image.Resampling.LANCZOS)

        # 4. Enhance Contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # 5. Binarize (Thresholding)
        # Make everything either black or white, no gray
        thresh = 128
        fn = lambda x: 255 if x > thresh else 0
        img = img.convert("L").point(fn, mode="1")
        # convert back to L so it is compatible with opencv (uint8), otherwise it becomes bool
        img = img.convert("L")

        # DEBUG: Save processed image to check what OCR sees
        try:
            debug_path = os.path.join(get_app_directory(), "ocr_debug.png")
            img.save(debug_path)
        except Exception:
            pass

        return img
    except Exception as e:
        print(f"[OCR] Preprocess warning: {e}")
        return image


def is_valid_text(text: str) -> bool:
    """
    Validate OCR text - reject garbage/incomplete text before translation.
    Returns True only if text is meaningful enough for translation.

    Filters:
    - Too short text (< 2 chars, unless CJK)
    - Low letter ratio (< 15% letters/CJK) - Relaxed from 40%
    - Garbage patterns (mostly pure symbols)
    """
    if not text:
        return False

    text_clean = text.strip()

    # Minimum length check - Relaxed for CJK (can be 1 char)
    if len(text_clean) < 2:
        # Check if it's a CJK character (which can mean something on its own)
        if any("\u4e00" <= c <= "\u9fff" for c in text_clean):
            pass
        else:
            print(f"[OCR] Rejected: Too short '{text_clean}'")
            return False

    # Calculate letter ratio (letters + CJK + Japanese kana)
    def is_meaningful_char(c):
        return (
            c.isalpha()
            or "\u4e00" <= c <= "\u9fff"  # CJK
            or "\u3040" <= c <= "\u309f"  # Hiragana
            or "\u30a0" <= c <= "\u30ff"  # Katakana
            or "\uac00" <= c <= "\ud7af"  # Korean
            or c.isdigit()  # Allowing numbers as meaningful (e.g. HP: 100)
        )

    letter_count = sum(1 for c in text_clean if is_meaningful_char(c))
    letter_ratio = letter_count / len(text_clean) if text_clean else 0

    if letter_ratio < 0.15:  # Relaxed to 15%
        print(f"[OCR] Rejected: Low letter ratio ({letter_ratio:.2f}) '{text_clean}'")
        return False

    # Check for strict garbage patterns (only if mostly symbols)
    garbage_patterns = [
        "|||",
        "---",
        "___",
        "\\\\\\",
        "///",
        "!!!",
        "???",
        "...",
        "~~~",
        "***",
        "###",
        "@@@",
        "$$$",
    ]

    # Only block if it STARTS with these strings (often UI borders)
    # AND the rest is not meaningful
    if any(
        text_clean.startswith(p) and len(text_clean) < len(p) + 3
        for p in garbage_patterns
    ):
        print(f"[OCR] Rejected: Garbage pattern '{text_clean}'")
        return False

    # Check for excessive repeated characters (> 80% same char) - Relaxed from 50%
    if len(text_clean) >= 6:
        char_counts = {}
        for c in text_clean:
            char_counts[c] = char_counts.get(c, 0) + 1
        max_repeat = max(char_counts.values())
        if max_repeat / len(text_clean) > 0.8:
            print(f"[OCR] Rejected: Excessive repeats '{text_clean}'")
            return False

    return True


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
        if os.name != "nt":
            self._available = False
            return False

        if self._available is not None:
            return self._available

        # Check Windows version (Windows 10+) and winocr availability
        try:
            import platform

            version = platform.version()
            # On Windows platform.version() is like '10.0.19041'
            parts = version.split(".")
            if len(parts) > 0 and parts[0].isdigit():
                major = int(parts[0])
                if major < 10:
                    self._available = False
                    return False
            else:
                # Fallback/Unsure
                pass

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
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )
                import winocr

                return True
            except Exception as e:
                print(f"[WindowsOCR] Failed to install winocr: {e}")
                return False

    def extract_text(self, image: Image.Image) -> str:
        """Extract text using Windows OCR via winocr"""
        if not self.is_available():
            raise RuntimeError("Windows OCR not available")

        if not self._ensure_winocr():
            return self._extract_text_fallback(image)

        try:
            import winocr

            # winocr.recognize_pil is async, need to run in event loop
            async def do_ocr():
                # Preprocess image
                processed_img = preprocess_image_for_ocr(image)
                # Try English first (most game text)
                result = await winocr.recognize_pil(processed_img, lang="en")
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

            result = loop.run_until_complete(do_ocr())

            # Extract text - PRIORITIZE lines to preserve line breaks
            if hasattr(result, "lines") and result.lines:
                # Join lines with newline to preserve structure
                texts = [line.text for line in result.lines if hasattr(line, "text")]
                if texts:
                    return "\n".join(texts).strip()

            # Fallback to text property
            if result and hasattr(result, "text"):
                return result.text.strip()
            elif isinstance(result, dict) and "text" in result:
                return result["text"].strip()
            elif isinstance(result, str):
                return result.strip()

            return str(result).strip() if result else ""

        except Exception as e:
            return self._extract_text_fallback(image)

    def _extract_text_fallback(self, image: Image.Image) -> str:
        """Fallback: try using pytesseract if available"""
        try:
            import pytesseract

            return pytesseract.image_to_string(image, lang="eng+chi_sim")
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
        base_dir = get_app_directory()
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

    def install(
        self, progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """Download and install portable Tesseract automatically"""
        try:
            import urllib.request
            import zipfile
            import shutil
            from utils.version import is_frozen

            addon_path = self._get_addon_path()
            os.makedirs(addon_path, exist_ok=True)

            # Skip pip install when running as frozen exe (no pip available)
            if not is_frozen():
                if progress_callback:
                    progress_callback("Đang cài đặt pytesseract...", 10)

                # Install pytesseract package first
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "pytesseract", "--quiet"],
                    capture_output=True,
                    timeout=120,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )
            else:
                print("[Tesseract] Running as frozen exe, skipping pip install")

            if progress_callback:
                progress_callback("Đang tải Tesseract OCR...", 20)

            # Check if portable tesseract already exists
            tesseract_exe = os.path.join(addon_path, "tesseract.exe")

            if not os.path.exists(tesseract_exe):
                # Download portable tesseract from our server
                try:
                    # Get server URL from config
                    from core.config import refresh_server_url

                    dynamic_url = refresh_server_url()

                    server_urls_to_try = []
                    if dynamic_url:
                        server_urls_to_try.append(dynamic_url)
                    # Fallback servers
                    server_urls_to_try.append("https://fourt.io.vn")
                    server_urls_to_try.append("https://npapi.io")

                    download_success = False
                    last_error = None

                    for server_url in server_urls_to_try:
                        try:
                            portable_url = f"{server_url}/addons/tesseract-portable.zip"
                            print(f"[Tesseract] Trying download from: {portable_url}")

                            if progress_callback:
                                progress_callback(
                                    f"Đang thử tải từ server {server_urls_to_try.index(server_url) + 1}...",
                                    30,
                                )

                            zip_path = os.path.join(
                                addon_path, "tesseract-portable.zip"
                            )

                            # Use requests for better SSL handling in frozen exe
                            try:
                                import requests

                                print(f"[Tesseract] Using requests library...")

                                response = requests.get(
                                    portable_url, stream=True, timeout=120
                                )
                                response.raise_for_status()

                                total_size = int(
                                    response.headers.get("content-length", 0)
                                )
                                downloaded = 0

                                with open(zip_path, "wb") as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                            downloaded += len(chunk)
                                            if total_size > 0:
                                                percent = min(
                                                    30
                                                    + int(downloaded * 50 / total_size),
                                                    80,
                                                )
                                                if progress_callback:
                                                    progress_callback(
                                                        f"Đang tải... {percent}%",
                                                        percent,
                                                    )

                                print(f"[Tesseract] Downloaded {downloaded} bytes")

                            except ImportError:
                                # Fallback to urllib with SSL context
                                print(
                                    f"[Tesseract] requests not available, using urllib..."
                                )
                                import ssl

                                ssl_context = ssl.create_default_context()
                                ssl_context.check_hostname = False
                                ssl_context.verify_mode = ssl.CERT_NONE

                                def download_progress(
                                    block_num, block_size, total_size
                                ):
                                    if total_size > 0:
                                        percent = min(
                                            30
                                            + int(
                                                block_num * block_size * 50 / total_size
                                            ),
                                            80,
                                        )
                                        if progress_callback:
                                            progress_callback(
                                                f"Đang tải... {percent}%", percent
                                            )

                                opener = urllib.request.build_opener(
                                    urllib.request.HTTPSHandler(context=ssl_context)
                                )
                                urllib.request.install_opener(opener)
                                urllib.request.urlretrieve(
                                    portable_url, zip_path, download_progress
                                )

                            download_success = True
                            print(f"[Tesseract] Download successful from {server_url}")
                            break

                        except Exception as e:
                            last_error = e
                            print(f"[Tesseract] Failed download from {server_url}: {e}")
                            import traceback

                            traceback.print_exc()
                            continue

                    if not download_success:
                        raise last_error or Exception("All download servers failed")

                    if progress_callback:
                        progress_callback("Đang giải nén...", 85)

                    # Extract zip
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
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
                    print(
                        f"[Tesseract] tesseract.exe exists: {os.path.exists(tesseract_exe)}"
                    )

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

            # Verify installation - just check if tesseract.exe exists and works
            if os.path.exists(tesseract_exe):
                # Test running tesseract directly
                try:
                    result = subprocess.run(
                        [tesseract_exe, "--version"],
                        capture_output=True,
                        timeout=10,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if hasattr(subprocess, "CREATE_NO_WINDOW")
                            else 0
                        ),
                    )
                    if result.returncode == 0:
                        print(
                            f"[Tesseract] Version: {result.stdout.decode('utf-8', errors='ignore')[:50]}"
                        )
                        if progress_callback:
                            progress_callback("Hoàn tất!", 100)
                        return True
                    else:
                        print(
                            f"[Tesseract] Test failed: {result.stderr.decode('utf-8', errors='ignore')}"
                        )
                except Exception as e:
                    print(f"[Tesseract] Test error: {e}")

                # Even if test fails, if exe exists, consider it installed
                if progress_callback:
                    progress_callback("Hoàn tất!", 100)
                return True

            if progress_callback:
                progress_callback("Không tìm thấy tesseract.exe", 0)
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
            # Preprocess
            processed_img = preprocess_image_for_ocr(image)
            return self._extract_with_portable(processed_img, tesseract_exe)
        else:
            # Preprocess
            processed_img = preprocess_image_for_ocr(image)
            return self._extract_with_pytesseract(processed_img)

    def _extract_with_portable(self, image: Image.Image, tesseract_exe: str) -> str:
        """Extract text using portable tesseract.exe"""
        try:
            import tempfile
            import uuid

            temp_input = os.path.join(
                tempfile.gettempdir(), f"tess_in_{uuid.uuid4().hex}.png"
            )
            temp_output = os.path.join(
                tempfile.gettempdir(), f"tess_out_{uuid.uuid4().hex}"
            )

            image.save(temp_input, "PNG")

            try:
                cmd = [tesseract_exe, temp_input, temp_output, "-l", "eng+chi_sim"]

                subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=30,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

                output_file = temp_output + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r", encoding="utf-8") as f:
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

            return pytesseract.image_to_string(image, lang="eng+chi_sim")
        except ImportError:
            print("[Tesseract] pytesseract not installed")
            return ""
        except Exception as e:
            print(f"[Tesseract] pytesseract error: {e}")
            return ""


class EasyOCREngine(OCREngine):
    """
    EasyOCR - High accuracy OCR with GPU support
    Best for game text and mixed languages
    """

    def __init__(self):
        super().__init__()
        self._reader = None
        self._addon_path = self._get_addon_path()

    def _get_addon_path(self) -> str:
        """Get path to easyocr addon folder"""
        base_dir = get_app_directory()
        return os.path.join(base_dir, "addons", "easyocr")

    def _get_libs_path(self) -> str:
        """Get path to external libraries folder"""
        base_dir = get_app_directory()
        return os.path.join(base_dir, "addons", "libs")

    def _mount_external_libs(self) -> bool:
        """Add external libs folder to sys.path"""
        libs_path = self._get_libs_path()
        if os.path.exists(libs_path) and libs_path not in sys.path:
            print(f"[EasyOCR] Mounting external libs: {libs_path}")
            sys.path.insert(0, libs_path)
            return True
        return False

    def is_available(self) -> bool:
        """Check if EasyOCR is available (lib installed + models present)"""
        # 1. Check library
        # 1. Check library
        self._mount_external_libs()
        try:
            import easyocr
        except ImportError:
            return False

        # 2. Check models
        # We need at least the English and detection models
        model_path = self._get_addon_path()
        if not os.path.exists(model_path):
            return False

        required_files = ["craft_mlt_25k.pth", "english_g2.pth"]
        for f in required_files:
            if not os.path.exists(os.path.join(model_path, f)):
                return False

        return True

    def get_download_size(self) -> str:
        """Get estimated download size"""
        return "~180 MB"

    def install(
        self, progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """Download and install EasyOCR models"""
        try:
            import urllib.request
            import zipfile
            import shutil
            from utils.version import is_frozen

            addon_path = self._get_addon_path()
            os.makedirs(addon_path, exist_ok=True)

            # 1. Install Library (if not present)
            try:
                import easyocr
            except ImportError:
                if not is_frozen():
                    if progress_callback:
                        progress_callback("Đang cài đặt thư viện easyocr...", 5)

                    # Install easyocr package
                    # We assume pytorch is already there (from setup.py or pre-packaged)
                    print("[EasyOCR] Installing easyocr package...")
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "easyocr", "--quiet"],
                        capture_output=True,
                        timeout=300,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if hasattr(subprocess, "CREATE_NO_WINDOW")
                            else 0
                        ),
                    )
                    if result.returncode != 0:
                        print(f"[EasyOCR] Pip install failed: {result.stderr.decode()}")
                        # Continue anyway? No, we need the lib.
                        return False
                else:
                    # Frozen build: Check for external libs
                    libs_path = self._get_libs_path()
                    if not os.path.exists(libs_path) or not os.listdir(libs_path):
                        print("[EasyOCR] External libs not found.")
                        if progress_callback:
                            progress_callback(
                                "Thiếu thư viện OCR! Vui lòng tải gói 'OCR Core' vào addons/libs.",
                                0,
                            )
                        # Here we would normally download the Libs Zip (~800MB)
                        # For now, return False and prompt user (handled by UI showing 'Install')
                        print(
                            f"[EasyOCR] Please populate {libs_path} with easyocr and torch."
                        )
                        # Create the directory to help the user
                        os.makedirs(libs_path, exist_ok=True)
                        if sys.platform == "win32":
                            subprocess.run(["explorer", libs_path])
                        return False

                    self._mount_external_libs()

                # Try to import newly installed package
                try:
                    import site
                    import importlib

                    importlib.invalidate_caches()
                    if sys.platform == "win32":
                        # Force reload of site-packages on Windows
                        from importlib.machinery import PathFinder

                        sys.path_importer_cache.clear()

                    import easyocr

                    print("[EasyOCR] Library imported successfully after install")
                    self._available = True  # Tentatively available (needs models)
                except ImportError:
                    print(
                        "[EasyOCR] Could not import easyocr immediately after install. Restart may be required."
                    )

            # 2. Download Models
            # URLs from JaidedAI releases
            models = [
                {
                    "name": "craft_mlt_25k",
                    "url": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
                    "file": "craft_mlt_25k.pth",
                },
                {
                    "name": "english_g2",
                    "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
                    "file": "english_g2.pth",
                },
                {
                    "name": "zh_sim_g2",
                    "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/zh_sim_g2.zip",
                    "file": "zh_sim_g2.pth",
                },
            ]

            total_steps = len(models)
            current_step = 0

            for model in models:
                current_step += 1
                model_file_path = os.path.join(addon_path, model["file"])

                if os.path.exists(model_file_path):
                    print(f"[EasyOCR] Model {model['name']} already exists.")
                    continue

                if progress_callback:
                    progress = 10 + int((current_step / total_steps) * 80)
                    progress_callback(f"Đang tải model {model['name']}...", progress)

                zip_path = os.path.join(addon_path, f"{model['name']}.zip")

                # Download
                try:
                    import requests

                    print(f"[EasyOCR] Downloading {model['url']}...")
                    response = requests.get(model["url"], stream=True, timeout=120)
                    response.raise_for_status()

                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(zip_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                    print(f"[EasyOCR] Downloaded {model['name']}")

                except Exception as e:
                    print(f"[EasyOCR] Failed to download {model['name']}: {e}")
                    # Try next one? Or fail? Best to fail if essential models missing.
                    if model["name"] in ["craft_mlt_25k", "english_g2"]:
                        raise e

                # Extract
                if progress_callback:
                    progress_callback(f"Đang giải nén {model['name']}...", progress + 5)

                try:
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(addon_path)

                    # Cleanup zip
                    os.remove(zip_path)

                except Exception as e:
                    print(f"[EasyOCR] Extract failed for {model['name']}: {e}")

            if progress_callback:
                progress_callback("Hoàn tất!", 100)

            # Reset reader to force reload
            self._reader = None
            self._available = True
            return True

        except Exception as e:
            print(f"[EasyOCR] Install error: {e}")
            import traceback

            traceback.print_exc()
            if progress_callback:
                progress_callback(f"Lỗi: {str(e)[:50]}", 0)
            return False

    def _get_reader(self):
        """Lazy init EasyOCR reader"""
        if self._reader is None:
            try:
                self._mount_external_libs()
                import easyocr

                model_path = self._get_addon_path()
                print(f"[EasyOCR] Initializing reader with model path: {model_path}")

                # Support English and Chinese, GPU if available
                # model_storage_directory: Path to store/load models
                # download_enabled: set to False to prevent auto-downloading if we manage it manually
                # but we can leave it True as fallback if we provided the files correctly
                self._reader = easyocr.Reader(
                    ["en", "ch_sim"],
                    gpu=True,
                    verbose=False,
                    model_storage_directory=model_path,
                    download_enabled=False,
                )
            except Exception as e:
                print(f"[EasyOCR] Failed to init reader: {e}")
                try:
                    import easyocr

                    self._reader = easyocr.Reader(
                        ["en"],
                        gpu=False,
                        verbose=False,
                        model_storage_directory=model_path,
                        download_enabled=False,
                    )
                except:
                    self._reader = None
        return self._reader

    def extract_text(self, image: Image.Image) -> str:
        """Extract text using EasyOCR"""
        if not self.is_available():
            return ""

        # Preprocess
        processed_img = preprocess_image_for_ocr(image)

        reader = self._get_reader()
        if reader is None:
            return ""

        try:
            import numpy as np

            # Convert PIL to numpy array
            img_array = np.array(processed_img)

            # Run OCR
            results = reader.readtext(img_array, detail=0, paragraph=True)

            # Join results
            text = "\n".join(results) if results else ""
            return text.strip()

        except Exception as e:
            print(f"[EasyOCR] Extract error: {e}")
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
        },
        # "easyocr": {
        #     "name": "EasyOCR ⭐",
        #     "description": "High accuracy, GPU accelerated",
        #     "size": "~150 MB (pip install)",
        #     "requires_download": True,
        # },
    }

    def __init__(self):
        self._engines: Dict[str, OCREngine] = {
            "windows": WindowsOCREngine(),
            "tesseract": TesseractEngine(),
            # "easyocr": EasyOCREngine(),
        }
        self._install_lock = threading.Lock()
        self._current_engine = (
            "windows" if os.name == "nt" else "tesseract"
        )  # Default engine

    def set_engine(self, engine_id: str):
        """Set current OCR engine to use"""
        if engine_id in self._engines:
            self._current_engine = engine_id
            print(f"[OCRAddon] Engine set to: {engine_id}")

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

    def install_engine(
        self,
        engine_id: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> bool:
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
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if hasattr(subprocess, "CREATE_NO_WINDOW")
                            else 0
                        ),
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

            elif engine_id == "easyocr":
                easy_engine: EasyOCREngine = engine
                return easy_engine.install(progress_callback)

            return False

    def install_engine_async(
        self,
        engine_id: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """Install engine asynchronously"""

        def task():
            result = self.install_engine(engine_id, progress_callback)
            if on_complete:
                on_complete(result)

        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def extract_text(
        self, image: Image.Image, engine_id: str = None, preprocess: bool = True
    ) -> str:
        """Extract text from image using specified or available engine

        Args:
            image: PIL Image to extract text from
            engine_id: Specific engine to use, or None to auto-select
            preprocess: Whether to preprocess image for better small region detection
        """
        if engine_id is None:
            # Use current engine if set and ready, otherwise fallback
            if self.is_engine_ready(self._current_engine):
                engine_id = self._current_engine
            else:
                # EasyOCR first (best quality), then windows, then tesseract
                for eid in ["easyocr", "windows", "tesseract"]:
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

    def extract_text_from_region(
        self, x: int, y: int, w: int, h: int, engine_id: str = None
    ) -> str:
        """Capture screen region and extract text"""
        image = None

        # Try dxcam first (faster, GPU-accelerated)
        try:
            import dxcam

            print(f"[OCRAddon] Trying dxcam capture for region ({x}, {y}, {w}x{h})...")

            camera = dxcam.create(output_color="RGB")
            if camera is None:
                print("[OCRAddon] dxcam.create() returned None")
                raise RuntimeError("dxcam camera is None")

            region = (x, y, x + w, y + h)
            frame = camera.grab(region=region)

            if frame is not None:
                image = Image.fromarray(frame)
                print(f"[OCRAddon] dxcam capture success, size: {image.size}")
            else:
                print("[OCRAddon] dxcam.grab() returned None")

        except Exception as e:
            print(f"[OCRAddon] dxcam failed: {e}")

        # Fallback to PIL.ImageGrab
        if image is None:
            try:
                from PIL import ImageGrab

                print(
                    f"[OCRAddon] Fallback to PIL.ImageGrab for region ({x}, {y}, {x+w}, {y+h})..."
                )

                bbox = (x, y, x + w, y + h)
                image = ImageGrab.grab(bbox=bbox)
                print(f"[OCRAddon] ImageGrab success, size: {image.size}")

            except Exception as e:
                print(f"[OCRAddon] ImageGrab failed: {e}")
                import traceback

                traceback.print_exc()
                return ""

        if image is None:
            print("[OCRAddon] Failed to capture screen region with any method")
            return ""

        try:
            # Preprocess image for better OCR
            image = self._preprocess_image(image)

            # Debug: save captured image
            import tempfile

            debug_path = os.path.join(tempfile.gettempdir(), "ocr_debug.png")
            image.save(debug_path)
            print(f"[OCRAddon] Captured image saved to: {debug_path}")

            # Pass preprocess=False since we already preprocessed above
            result = self.extract_text(image, engine_id, preprocess=False)
            print(
                f"[OCRAddon] OCR result: '{result[:100]}...'"
                if len(result) > 100
                else f"[OCRAddon] OCR result: '{result}'"
            )
            return result

        except Exception as e:
            print(f"[OCRAddon] Extract error: {e}")
            import traceback

            traceback.print_exc()
            return ""

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy:
        - Scale up small images aggressively for better recognition
        - Enhance contrast for game UI with colored backgrounds
        - Optional invert for light-on-dark text (common in games)
        - Sharpen text edges
        """
        from PIL import ImageEnhance, ImageOps, ImageFilter
        import numpy as np

        width, height = image.size

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # --- Scale up small images ---
        # OCR works much better on larger text
        min_height = 80  # Increased from 60
        if height < min_height:
            scale_factor = min_height / height
            scale_factor = min(scale_factor, 3.0)  # Cap at 3x
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.LANCZOS)
            width, height = new_width, new_height

        # --- Check if dark background (light text on dark) ---
        # Convert to numpy for analysis
        img_array = np.array(image)
        avg_brightness = np.mean(img_array)

        # If average brightness is low, likely dark background
        is_dark_bg = avg_brightness < 100

        if is_dark_bg:
            # For dark backgrounds, enhance contrast before potential inversion
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.3)  # Boost contrast

            # Optional: invert for tesseract (works better with black-on-white)
            # But Windows OCR handles colored text well, so only slight adjustment
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)  # Slight brightness boost
        else:
            # Light background - enhance contrast slightly
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.15)

        # --- Sharpen for cleaner text edges ---
        # Helps with anti-aliased game fonts
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)

        return image
