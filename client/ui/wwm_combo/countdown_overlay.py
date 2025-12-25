"""
Countdown Overlay - Transparent floating countdown timer for skill cooldowns

Displays a transparent overlay on the right side of the screen showing
the skill image with a countdown timer. Always on top and click-through.
"""

import tkinter as tk
from typing import Optional, Callable
from pathlib import Path
import threading


class CountdownOverlay:
    """Transparent floating countdown overlay"""
    
    _instance: Optional['CountdownOverlay'] = None
    _active_countdowns: list = []
    
    def __init__(self, root: tk.Tk):
        """Initialize the countdown overlay system"""
        self.root = root
        self._overlays = []  # List of active overlay windows
        
    @classmethod
    def get_instance(cls, root: tk.Tk = None) -> 'CountdownOverlay':
        """Get or create singleton instance"""
        if root is not None:
            # If root changed (new window created), update the instance
            if cls._instance is not None:
                try:
                    # Check if old root still exists
                    if cls._instance.root != root:
                        # New window, update root and clear old overlays
                        cls._instance.clear_all()
                        cls._instance.root = root
                except:
                    pass
            else:
                cls._instance = cls(root)
        return cls._instance
    
    def show_countdown(self, skill_name: str, image_path: str, countdown_seconds: float,
                       on_complete: Callable = None):
        """Show a countdown overlay for a skill"""
        if countdown_seconds <= 0:
            return
        
        # Check if root window still exists
        try:
            if not self.root.winfo_exists():
                return
        except:
            return
            
        # Create overlay window on main thread
        def create_overlay():
            try:
                if not self.root.winfo_exists():
                    return
                overlay = _CountdownWindow(
                    self.root,
                    skill_name=skill_name,
                    image_path=image_path,
                    countdown_seconds=countdown_seconds,
                    on_complete=on_complete,
                    on_destroy=lambda w: self._remove_overlay(w)
                )
                self._overlays.append(overlay)
                self._reposition_overlays()
            except Exception as e:
                print(f"[CountdownOverlay] Error creating overlay: {e}")
            
        if threading.current_thread() is threading.main_thread():
            create_overlay()
        else:
            self.root.after(0, create_overlay)
    
    def _remove_overlay(self, overlay):
        """Remove overlay from list and reposition remaining"""
        if overlay in self._overlays:
            self._overlays.remove(overlay)
            self._reposition_overlays()
    
    def _reposition_overlays(self):
        """Reposition all overlays to stack vertically"""
        screen_height = self.root.winfo_screenheight()
        screen_width = self.root.winfo_screenwidth()
        
        overlay_height = 55
        total_height = len(self._overlays) * (overlay_height + 5)
        start_y = (screen_height - total_height) // 2
        
        for i, overlay in enumerate(self._overlays):
            x = screen_width - 120  # Right side with margin
            y = start_y + i * (overlay_height + 5)
            overlay.set_position(x, y)
    
    def clear_all(self):
        """Clear all active countdowns"""
        for overlay in list(self._overlays):
            overlay.close()
        self._overlays.clear()


class _CountdownWindow:
    """Individual countdown overlay window"""
    
    def __init__(self, parent: tk.Tk, skill_name: str, image_path: str,
                 countdown_seconds: float, on_complete: Callable = None,
                 on_destroy: Callable = None):
        self.parent = parent
        self.countdown_seconds = countdown_seconds
        self.remaining = countdown_seconds
        self.on_complete = on_complete
        self.on_destroy = on_destroy
        self.closed = False
        
        # Create toplevel window
        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)  # Frameless
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', 0.85)  # Slightly transparent
        
        # Make window click-through on Windows
        try:
            self.window.attributes('-transparentcolor', '')
        except:
            pass
        
        # Dark semi-transparent background
        self.window.configure(bg='#1a1a2e')
        
        # Container frame
        frame = tk.Frame(self.window, bg='#1a1a2e', padx=5, pady=5)
        frame.pack(fill='both', expand=True)
        
        # Image label
        self.image_label = tk.Label(frame, bg='#1a1a2e', width=40, height=40)
        self.image_label.pack(side='left', padx=(0, 5))
        self._load_image(image_path)
        
        # Countdown timer (no name, just timer)
        self.timer_label = tk.Label(
            frame,
            text=self._format_time(self.remaining),
            font=('Segoe UI', 14, 'bold'),
            fg='#00ff88',
            bg='#1a1a2e'
        )
        self.timer_label.pack(side='left', anchor='center')
        
        # Set initial size (smaller)
        self.window.geometry('110x55')
        
        # Start countdown
        self._tick()
    
    def _load_image(self, image_path: str):
        """Load and display skill image"""
        if not image_path:
            self._show_fallback_image()
            return
            
        try:
            from PIL import Image, ImageTk
            
            # Find image in wwm_resources
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up to project root, then to wwm_resources
            project_root = os.path.dirname(os.path.dirname(current_dir))
            wwm_resources = os.path.join(project_root, 'wwm_resources')
            
            paths_to_try = [
                os.path.join(wwm_resources, image_path),
                os.path.join(wwm_resources, os.path.basename(image_path)),
                image_path
            ]
            
            img = None
            for path in paths_to_try:
                if os.path.exists(path):
                    img = Image.open(path)
                    break
            
            if img:
                img = img.resize((50, 50), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                self._photo = ImageTk.PhotoImage(img)
                self.image_label.config(image=self._photo, width=50, height=50)
            else:
                self._show_fallback_image()
                
        except Exception as e:
            self._show_fallback_image()
    
    def _show_fallback_image(self):
        """Show fallback when image not available"""
        self.image_label.config(
            text="⏱",
            font=('Segoe UI', 24),
            fg='#00ff88',
            width=4,
            height=2
        )
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as M:SS or S.s"""
        if seconds >= 60:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}:{secs:02d}"
        elif seconds >= 10:
            return f"{int(seconds)}s"
        else:
            return f"{seconds:.1f}s"
    
    def _tick(self):
        """Update countdown every 100ms"""
        if self.closed:
            return
            
        self.remaining -= 0.1
        
        if self.remaining <= 0:
            self.remaining = 0
            self.timer_label.config(text="0.0s", fg='#ff4444')
            self.window.after(500, self.close)
            if self.on_complete:
                self.on_complete()
        else:
            # Change color as countdown progresses
            if self.remaining <= 3:
                self.timer_label.config(fg='#ff4444')  # Red when low
            elif self.remaining <= 5:
                self.timer_label.config(fg='#ffaa00')  # Orange
            else:
                self.timer_label.config(fg='#00ff88')  # Green
                
            self.timer_label.config(text=self._format_time(self.remaining))
            self.window.after(100, self._tick)
    
    def set_position(self, x: int, y: int):
        """Set window position"""
        if not self.closed:
            self.window.geometry(f'+{x}+{y}')
    
    def close(self):
        """Close the overlay"""
        if self.closed:
            return
        self.closed = True
        
        try:
            self.window.destroy()
        except:
            pass
        
        if self.on_destroy:
            self.on_destroy(self)


# Global function to show countdown (convenience)
def show_skill_countdown(root: tk.Tk, skill_name: str, image_path: str, 
                         countdown_seconds: float, on_complete: Callable = None):
    """Show a skill countdown overlay"""
    overlay = CountdownOverlay.get_instance(root)
    if overlay:
        overlay.show_countdown(skill_name, image_path, countdown_seconds, on_complete)
