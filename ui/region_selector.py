"""
Region Selector
Fullscreen overlay for selecting a region of the screen
Used by Quest Video Helper to select quest name area
"""

import tkinter as tk
from typing import Callable, Optional, Tuple

class RegionSelector:
    """
    Fullscreen overlay to let user select a region on screen
    
    Features:
    - Semi-transparent dark overlay
    - Clear instructions
    - Rectangle highlight when dragging
    - Crosshair cursor
    - ESC to cancel
    """
    
    def __init__(self, parent: tk.Tk, 
                 on_select: Callable[[int, int, int, int], None],
                 on_cancel: Optional[Callable[[], None]] = None,
                 instruction_text: str = "Kéo chuột để chọn vùng chứa tên quest"):
        """
        Initialize region selector
        
        Args:
            parent: Parent Tk window
            on_select: Callback(x, y, width, height) when region selected
            on_cancel: Callback when selection cancelled
            instruction_text: Text to show as instructions
        """
        self.parent = parent
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.instruction_text = instruction_text
        
        self.root: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.start_x: Optional[int] = None
        self.start_y: Optional[int] = None
        self.current_rect: Optional[int] = None
        self.is_active = False
    
    def show(self) -> None:
        """Show the region selector overlay"""
        if self.is_active:
            return
        
        self.is_active = True
        
        # Create fullscreen overlay
        self.root = tk.Toplevel(self.parent)
        self.root.title("")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.4)
        self.root.configure(bg="black")
        self.root.attributes("-topmost", True)
        
        # Canvas for drawing
        self.canvas = tk.Canvas(
            self.root, 
            cursor="cross",
            bg="black",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Instructions label - top center
        instruction_frame = tk.Frame(self.root, bg="#1a1a2e", padx=20, pady=10)
        instruction_frame.place(relx=0.5, y=50, anchor="center")
        
        instruction_label = tk.Label(
            instruction_frame,
            text=self.instruction_text,
            font=("Segoe UI", 14, "bold"),
            fg="#00d4ff",
            bg="#1a1a2e"
        )
        instruction_label.pack()
        
        # Hotkey hint
        hint_label = tk.Label(
            instruction_frame,
            text="ESC để hủy",
            font=("Segoe UI", 10),
            fg="#888888",
            bg="#1a1a2e"
        )
        hint_label.pack(pady=(5, 0))
        
        # Bind events
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", self._on_escape)
        self.canvas.bind("<Escape>", self._on_escape)  # Also bind to canvas
        
        # Force focus to ensure ESC key works
        self.root.focus_force()
        self.root.grab_set()  # Grab all input
        self.canvas.focus_set()
    
    def _on_press(self, event: tk.Event) -> None:
        """Handle mouse button press"""
        self.start_x = event.x
        self.start_y = event.y
        
        # Clear previous rectangle
        if self.current_rect:
            self.canvas.delete(self.current_rect)
            self.current_rect = None
    
    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag"""
        if self.start_x is None or self.start_y is None:
            return
        
        # Delete previous rectangle
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        
        # Draw new rectangle
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            event.x, event.y,
            outline="#00d4ff",
            width=2,
            dash=(5, 3)
        )
        
        # Draw corner markers
        self._draw_corner_markers(self.start_x, self.start_y, event.x, event.y)
    
    def _draw_corner_markers(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Draw small corner markers on the selection rectangle"""
        self.canvas.delete("corner_marker")
        
        marker_size = 8
        color = "#00d4ff"
        
        corners = [
            (x1, y1),  # Top-left
            (x2, y1),  # Top-right
            (x1, y2),  # Bottom-left
            (x2, y2),  # Bottom-right
        ]
        
        for cx, cy in corners:
            self.canvas.create_rectangle(
                cx - marker_size//2, cy - marker_size//2,
                cx + marker_size//2, cy + marker_size//2,
                fill=color, outline=color,
                tags="corner_marker"
            )
    
    def _on_release(self, event: tk.Event) -> None:
        """Handle mouse button release"""
        if self.start_x is None or self.start_y is None:
            return
        
        end_x, end_y = event.x, event.y
        
        # Calculate normalized coordinates
        x = min(self.start_x, end_x)
        y = min(self.start_y, end_y)
        w = abs(end_x - self.start_x)
        h = abs(end_y - self.start_y)
        
        # Minimum size check (very small to allow text lines)
        if w < 3 or h < 3:
            # Too small, ignore
            self.start_x = None
            self.start_y = None
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None
            self.canvas.delete("corner_marker")
            return
        
        # Close overlay
        self._close()
        
        # Callback with coordinates
        if self.on_select:
            self.on_select(x, y, w, h)
    
    def _on_escape(self, event: tk.Event) -> None:
        """Handle ESC key"""
        self._close()
        
        if self.on_cancel:
            self.on_cancel()
    
    def _close(self) -> None:
        """Close the overlay"""
        self.is_active = False
        
        if self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass
            self.root = None
        
        self.canvas = None
        self.start_x = None
        self.start_y = None
        self.current_rect = None
