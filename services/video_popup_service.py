"""
Video Popup Service
Handles opening video in browser popup with size and position
"""

import os
import subprocess
import shutil
import webbrowser
from typing import Optional, Tuple


class VideoPopupService:
    """Service for opening video in browser popup"""
    
    # Default browser paths on Windows
    CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    
    EDGE_PATHS = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    
    def __init__(self):
        self._browser_path: Optional[str] = None
        self._detect_browser()
    
    def _detect_browser(self) -> None:
        """Detect available browser (Chrome preferred, then Edge)"""
        # Check Chrome first
        for path in self.CHROME_PATHS:
            if os.path.exists(path):
                self._browser_path = path
                print(f"[VideoPopup] Found Chrome: {path}")
                return
        
        # Then Edge
        for path in self.EDGE_PATHS:
            if os.path.exists(path):
                self._browser_path = path
                print(f"[VideoPopup] Found Edge: {path}")
                return
        
        print("[VideoPopup] No Chrome/Edge found, will use default browser")
    
    @property
    def has_app_mode_browser(self) -> bool:
        """Check if app mode browser is available"""
        return self._browser_path is not None
    
    def open_video_popup(
        self,
        url: str,
        title: str = "Video",
        x: int = 100,
        y: int = 100,
        width: int = 480,
        height: int = 360
    ) -> bool:
        """
        Open video URL in browser popup
        
        Args:
            url: YouTube video URL
            title: Window title (for logging)
            x: Window X position
            y: Window Y position
            width: Window width
            height: Window height
        
        Returns:
            True if opened with app mode, False if fallback to default browser
        """
        print(f"[VideoPopup] Opening: {title}")
        print(f"[VideoPopup] URL: {url}")
        print(f"[VideoPopup] Position: ({x}, {y}), Size: {width}x{height}")
        
        if self._browser_path:
            try:
                cmd = [
                    self._browser_path,
                    f"--app={url}",
                    f"--window-size={width},{height}",
                    f"--window-position={x},{y}",
                ]
                subprocess.Popen(cmd, shell=False)
                return True
            except Exception as e:
                print(f"[VideoPopup] Error launching app mode: {e}")
        
        # Fallback to default browser
        webbrowser.open(url)
        return False
    
    def calculate_popup_position(
        self,
        selection: Tuple[int, int, int, int],
        popup_width: int,
        popup_height: int,
        screen_width: int,
        screen_height: int
    ) -> Tuple[int, int]:
        """
        Calculate popup position near selection region
        
        Args:
            selection: (x, y, width, height) of selected region
            popup_width: Width of popup
            popup_height: Height of popup
            screen_width: Screen width
            screen_height: Screen height
        
        Returns:
            (x, y) position for popup
        """
        sel_x, sel_y, sel_w, sel_h = selection
        
        # Try right of selection first
        popup_x = sel_x + sel_w + 20
        popup_y = sel_y
        
        # Check screen bounds - try left if no space on right
        if popup_x + popup_width > screen_width:
            popup_x = sel_x - popup_width - 20
        
        # Keep in screen bounds
        if popup_x < 0:
            popup_x = 50
        if popup_y + popup_height > screen_height:
            popup_y = screen_height - popup_height - 50
        if popup_y < 0:
            popup_y = 50
        
        return popup_x, popup_y


# Singleton instance
_instance: Optional[VideoPopupService] = None


def get_video_popup_service() -> VideoPopupService:
    """Get singleton instance of VideoPopupService"""
    global _instance
    if _instance is None:
        _instance = VideoPopupService()
    return _instance
