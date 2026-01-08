"""
Video Overlay Window
Shows YouTube video in an embedded overlay using subprocess
Supports both YouTube embed and local video files
"""

import os
import sys
import subprocess
from typing import Optional

class VideoOverlayWindow:
    """
    Video player overlay using pywebview in subprocess
    Spawns a separate process to avoid main thread issues
    """
    
    def __init__(self, video_url: str, title: str = "Video Guide",
                 width: int = 480, height: int = 360,
                 autoplay: bool = True, embed_html: str = None,
                 is_local: bool = False):
        """
        Initialize video overlay
        
        Args:
            video_url: YouTube video URL or local file path
            title: Window title
            width: Initial window width
            height: Initial window height
            autoplay: Whether to autoplay the video
            embed_html: Official embed HTML from oEmbed API
            is_local: True if video_url is a local file path
        """
        self.video_url = video_url
        self.title = title
        self.width = width
        self.height = height
        self.autoplay = autoplay
        self.embed_html = embed_html
        self.is_local = is_local
        
        self._process: Optional[subprocess.Popen] = None
        self._is_open = False
    
    def show(self) -> None:
        """Show the video overlay window"""
        if self._is_open:
            return
        
        self._is_open = True
        
        try:
            # Get path to launcher script
            launcher_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "video_overlay_launcher.py"
            )
            
            if not os.path.exists(launcher_path):
                print(f"[VideoOverlay] Launcher not found: {launcher_path}")
                self._open_in_browser()
                return
            
            # Build command with arguments
            cmd = [
                sys.executable,
                launcher_path,
                self.video_url,
                self.title,
                str(self.width),
                str(self.height),
                str(self.autoplay),
                self.embed_html or "",  # Pass embed HTML 
                str(self.is_local)  # Pass is_local flag
            ]
            
            print(f"[VideoOverlay] Opening overlay: {self.title} (local={self.is_local})")
            
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
        except Exception as e:
            print(f"[VideoOverlay] Error spawning overlay: {e}")
            import traceback
            traceback.print_exc()
            self._open_in_browser()
    
    def _open_in_browser(self) -> None:
        """Fallback: open in browser"""
        import webbrowser
        
        if self.is_local:
            # Can't open local file in browser easily, just print path
            print(f"[VideoOverlay] Local video: {self.video_url}")
            return
        
        watch_url = self._get_watch_url()
        print(f"[VideoOverlay] Fallback - opening in browser: {watch_url}")
        webbrowser.open(watch_url)
    
    def _get_watch_url(self) -> str:
        """Get YouTube watch URL"""
        url = self.video_url
        video_id = None
        
        if "youtube.com/embed/" in url:
            video_id = url.split("embed/")[1].split("?")[0]
        elif "youtube.com/watch?v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        
        return url
    
    def close(self) -> None:
        """Close the video overlay"""
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
        
        self._is_open = False
        self._process = None
    
    @property
    def is_open(self) -> bool:
        """Check if window is open"""
        if self._process:
            # Check if process is still running
            if self._process.poll() is not None:
                self._is_open = False
                self._process = None
        return self._is_open
