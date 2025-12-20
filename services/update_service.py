"""
Auto-update service - Professional update flow with Inno Setup integration
Flow: Check → Download → Dialog → Silent Install → Auto Restart
"""

import json
import os
import sys
import subprocess
import threading
import urllib.request
import urllib.error
import time
import tempfile
from enum import Enum
from typing import Optional, Callable

from core.config import UPDATE_SERVER_URL, VERSION_FILE
from utils import get_current_version, compare_versions, is_frozen, get_app_directory


class UpdateState(Enum):
    """Update state machine"""
    IDLE = "idle"
    CHECKING = "checking"
    UPDATE_FOUND = "update_found"
    DOWNLOADING = "downloading"
    READY_TO_INSTALL = "ready"
    INSTALLING = "installing"
    NO_UPDATE = "no_update"
    ERROR = "error"


class UpdateService:
    """
    Professional update service with clean state management.
    
    Flow:
    1. check_for_updates() - Check if update available
    2. download_update() - Download installer to temp
    3. show_update_dialog() - Show beautiful confirm dialog
    4. install_update() - Run Inno Setup with silent flags
    """

    # Inno Setup silent install flags
    INNO_SILENT_FLAGS = [
        '/SILENT',              # Silent mode - no wizard UI
        '/CLOSEAPPLICATIONS',   # Close running app automatically
        '/RESTARTAPPLICATIONS', # Restart app after install
        '/NORESTART',           # Don't restart Windows (only app)
    ]

    def __init__(self, 
                 on_status_change: Optional[Callable[[str, str], None]] = None,
                 on_progress: Optional[Callable[[float, float, int], None]] = None):
        """
        Initialize update service
        
        Args:
            on_status_change: Callback(status_message, color)
            on_progress: Callback(current_mb, total_mb, percent)
        """
        self.on_status_change = on_status_change
        self.on_progress = on_progress
        
        # State
        self.state = UpdateState.IDLE
        self.installer_path: Optional[str] = None
        self.new_version: Optional[str] = None
        self.changelog: str = ""
        self.installer_url: Optional[str] = None
        
        # Config
        self.max_retries = 3
        self.retry_delay = 2
        self.download_dir = os.path.join(tempfile.gettempdir(), "FourT_Update")

    def _update_status(self, message: str, color: str = "#ffffff"):
        """Thread-safe status update"""
        print(f"[Update] {message}")
        if self.on_status_change:
            self.on_status_change(message, color)

    # =========================================================================
    # CHECK FOR UPDATES
    # =========================================================================
    
    def check_for_updates_sync(self) -> bool:
        """
        Check for updates synchronously.
        Returns True if update is available.
        """
        self.state = UpdateState.CHECKING
        
        try:
            current_version = get_current_version()
            print(f"[Update] Current version: {current_version}")
            
            # Fetch update info from server
            data = self._fetch_json(UPDATE_SERVER_URL, timeout=10)
            if not data:
                self.state = UpdateState.ERROR
                return False
            
            server_version = data.get("version", "1.0.0")
            self.installer_url = data.get("installer_url", "")
            self.changelog = data.get("changelog", "")
            
            # Resolve relative URL
            if self.installer_url and not self.installer_url.startswith("http"):
                from urllib.parse import urljoin
                self.installer_url = urljoin(UPDATE_SERVER_URL, self.installer_url)
            
            print(f"[Update] Server version: {server_version}")
            
            # Compare versions
            if compare_versions(current_version, server_version) < 0:
                self.new_version = server_version
                self.state = UpdateState.UPDATE_FOUND
                print(f"[Update] Update available: v{server_version}")
                return True
            else:
                self.state = UpdateState.NO_UPDATE
                print("[Update] Already at latest version")
                return False
                
        except Exception as e:
            print(f"[Update] Check error: {e}")
            self.state = UpdateState.ERROR
            return False

    def check_for_updates_async(self, callback: Callable[[bool], None]):
        """
        Check for updates asynchronously.
        
        Args:
            callback: Called with True if update available, False otherwise
        """
        def worker():
            result = self.check_for_updates_sync()
            callback(result)
        
        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # DOWNLOAD UPDATE
    # =========================================================================
    
    def download_update_sync(self) -> bool:
        """
        Download the update installer synchronously.
        Returns True if download successful.
        """
        if not self.installer_url or not self.new_version:
            self._update_status("No update URL available", "red")
            return False
        
        self.state = UpdateState.DOWNLOADING
        
        try:
            # Clean up old downloads first
            self.cleanup()
            
            os.makedirs(self.download_dir, exist_ok=True)
            self.installer_path = os.path.join(
                self.download_dir, 
                f"FourT_Setup_{self.new_version}.exe"
            )
            
            # Download with progress
            success = self._download_file(self.installer_url, self.installer_path)
            
            if success and os.path.exists(self.installer_path):
                file_size = os.path.getsize(self.installer_path)
                if file_size < 10000:
                    raise Exception("Downloaded file too small, may be corrupted")
                
                self.state = UpdateState.READY_TO_INSTALL
                self._update_status("Download complete! Ready to install.", "#2ecc71")
                print(f"[Update] Downloaded: {self.installer_path} ({file_size} bytes)")
                return True
            else:
                raise Exception("Download failed")
                
        except Exception as e:
            print(f"[Update] Download error: {e}")
            self.state = UpdateState.ERROR
            self._update_status(f"Tải thất bại: {e}", "red")
            return False

    def download_update_async(self, callback: Callable[[bool], None]):
        """
        Download update asynchronously.
        
        Args:
            callback: Called with True if download successful
        """
        def worker():
            result = self.download_update_sync()
            callback(result)
        
        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # INSTALL UPDATE
    # =========================================================================
    
    def install_update(self, silent: bool = True) -> bool:
        """
        Run the installer with Inno Setup flags.
        This will close the current app and install the update.
        
        Args:
            silent: If True, run in silent mode (no wizard UI)
        
        Returns:
            True if installer started successfully
        """
        if not self.installer_path or not os.path.exists(self.installer_path):
            self._update_status("Installer not found", "red")
            return False
        
        self.state = UpdateState.INSTALLING
        
        try:
            # Build command
            cmd = [self.installer_path]
            
            if silent:
                cmd.extend(self.INNO_SILENT_FLAGS)
            
            print(f"[Update] Running installer: {' '.join(cmd)}")
            self._update_status("Đang cài đặt...", "#3498db")
            
            # Start installer process (non-blocking)
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Give installer time to start
            time.sleep(1)
            
            # Exit current app - installer will handle the rest
            print("[Update] Exiting for update installation...")
            sys.exit(0)
            
        except Exception as e:
            print(f"[Update] Install error: {e}")
            self.state = UpdateState.ERROR
            self._update_status(f"Lỗi cài đặt: {e}", "red")
            return False

    def install_update_manual(self) -> bool:
        """
        Open installer for manual installation (shows Inno Setup wizard).
        """
        return self.install_update(silent=False)

    # =========================================================================
    # UI INTEGRATION
    # =========================================================================
    
    def show_update_dialog(self, parent_window):
        """
        Show beautiful update confirmation dialog.
        
        Args:
            parent_window: Parent tkinter window
        """
        if not self.installer_path or not self.new_version:
            print("[Update] No update available to show dialog")
            return
        
        from ui.update_complete_dialog import show_update_complete
        
        def on_install():
            """User chose to install now"""
            self.install_update(silent=True)
        
        def on_later():
            """User chose to install later"""
            self._update_status(
                f"Cập nhật v{self.new_version} đã sẵn sàng. Khởi động lại để cài đặt.",
                "#f1c40f"
            )
        
        show_update_complete(
            parent_window,
            self.installer_path,
            self.new_version,
            on_install=on_install,
            on_later=on_later
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _fetch_json(self, url: str, timeout: int = 10) -> Optional[dict]:
        """Fetch JSON data from URL with retry"""
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'FourT-Helper/1.0'})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode())
            except Exception as e:
                print(f"[Update] Fetch attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        return None

    def _download_file(self, url: str, destination: str) -> bool:
        """Download file with progress tracking"""
        for attempt in range(self.max_retries):
            try:
                self._update_status(f"Đang tải... (lần {attempt + 1})", "#f1c40f")
                
                # Get file size
                req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'FourT-Helper/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    file_size = int(response.headers.get('Content-Length', 0))
                
                # Download in chunks
                chunk_size = 8192
                downloaded = 0
                
                req = urllib.request.Request(url, headers={'User-Agent': 'FourT-Helper/1.0'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    with open(destination, 'wb') as f:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress
                            if file_size > 0 and self.on_progress:
                                percent = int((downloaded / file_size) * 100)
                                mb_downloaded = downloaded / (1024 * 1024)
                                mb_total = file_size / (1024 * 1024)
                                self.on_progress(mb_downloaded, mb_total, percent)
                
                # Verify size
                if file_size > 0 and os.path.getsize(destination) != file_size:
                    raise Exception("File size mismatch")
                
                return True
                
            except Exception as e:
                print(f"[Update] Download attempt {attempt + 1} failed: {e}")
                if os.path.exists(destination):
                    try:
                        os.remove(destination)
                    except:
                        pass
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        return False

    def cleanup(self):
        """Clean up downloaded files"""
        try:
            if self.installer_path and os.path.exists(self.installer_path):
                os.remove(self.installer_path)
            if os.path.exists(self.download_dir):
                import shutil
                shutil.rmtree(self.download_dir, ignore_errors=True)
        except Exception as e:
            print(f"[Update] Cleanup error: {e}")
