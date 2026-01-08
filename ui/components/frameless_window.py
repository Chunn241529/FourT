"""
Frameless Window Base Class (Modern Rounded Style)
Complete rewrite with robust drag and resize logic.
"""

import tkinter as tk
import ctypes
from ..theme import colors, FONTS

# Windows API constants for taskbar icon support
try:
    GWL_EXSTYLE = -20
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080
except:
    GWL_EXSTYLE = None


class FramelessWindow(tk.Toplevel):
    """
    Base class for a borderless window with custom rounded design.
    Uses transparency key to create true rounded corners.
    """

    # Constants
    CORNER_RADIUS = 16
    TITLE_HEIGHT = 48
    RESIZE_MARGIN = 6

    # Transparency key color
    TRANSPARENT_KEY = "#000001"

    def __init__(self, parent, title="Window", icon_path=None, **kwargs):
        # Extract initial size
        width = kwargs.pop("width", None)
        height = kwargs.pop("height", None)

        super().__init__(parent, **kwargs)

        # Set initial geometry if provided
        if width and height:
            self.geometry(f"{width}x{height}")

        # Window Setup
        self.overrideredirect(True)
        self.configure(bg=self.TRANSPARENT_KEY)
        self.attributes("-transparentcolor", self.TRANSPARENT_KEY)

        # Hide window initially to prevent flicker during setup
        self.withdraw()

        # State
        self._maximized = False
        self._prev_geom = None
        self._title = title
        self._icon_path = icon_path

        # Callback for before close (allows child frames to save state)
        self._on_close_callback = None
        # Interaction state
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_win_x = 0
        self._drag_start_win_y = 0
        self._resize_mode = None
        self._resize_start_geom = None

        # Main Canvas
        self.canvas = tk.Canvas(self, bg=self.TRANSPARENT_KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Content Container
        self.content_frame = tk.Frame(self.canvas, bg=colors["bg"])
        self._content_window_id = None

        # Window controls
        self._create_controls()

        # Bindings for canvas
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Leave>", self._on_leave)

        # Reset cursor when mouse enters content area
        self.content_frame.bind("<Enter>", self._on_content_enter)

        # Configure event for redraw
        self.bind("<Configure>", self._on_configure)

        # Set window icon (for taskbar)
        if icon_path:
            try:
                self.iconbitmap(icon_path)
            except:
                pass

        # Delayed setup: initial draw, taskbar icon, then show window
        self.after(10, self._initial_draw)
        self.after(30, self._setup_taskbar_icon)
        self.after(80, self._show_window)

    def geometry(self, geo_string=None):
        """Override geometry to auto-center after setting size"""
        if geo_string:
            result = super().geometry(geo_string)
            # If geometry string contains size (WxH), center the window
            if "x" in geo_string and "+" not in geo_string:
                self.after(20, self.center_on_screen)
            return result
        return super().geometry()

    def center_on_screen(self):
        """Center the window on screen"""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        super().geometry(f"+{x}+{y}")

    def center_relative(self, parent):
        """Center the window relative to a parent window"""
        self.update_idletasks()
        if not parent:
            self.center_on_screen()
            return

        w = self.winfo_width()
        h = self.winfo_height()

        # Get parent geometry
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        # Calculate center
        x = parent_x + (parent_w - w) // 2
        y = parent_y + (parent_h - h) // 2

        # Ensure within screen bounds
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = max(0, min(x, screen_w - w))
        y = max(0, min(y, screen_h - h))

        super().geometry(f"+{x}+{y}")

    def _setup_taskbar_icon(self):
        """Setup Windows taskbar icon for frameless window"""
        if GWL_EXSTYLE is None:
            return

        try:
            # Get the window handle
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

            # Get current extended style
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

            # Add WS_EX_APPWINDOW (show in taskbar) and remove WS_EX_TOOLWINDOW (hide from taskbar)
            style = style | WS_EX_APPWINDOW
            style = style & ~WS_EX_TOOLWINDOW

            # Apply new style
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

            # Note: We don't call withdraw/deiconify here to avoid flicker
            # The window will be shown via _show_window after all setup is done
        except Exception as e:
            print(f"[FramelessWindow] Could not setup taskbar icon: {e}")

    def _show_window(self):
        """Show the window after initial setup (prevents flicker)"""
        self.deiconify()
        # Ensure alpha is 1.0 if not managed externally
        if self.attributes("-alpha") == 0.0:
            self.attributes("-alpha", 1.0)

    def _initial_draw(self):
        """Initial draw after window geometry is set"""
        self._draw_window()
        self._update_layout()

    def set_title(self, title):
        """Update the window title"""
        self._title = title
        self._draw_window()

    def _draw_window(self):
        """Draw the rounded window background and title"""
        self.canvas.delete("bg", "title", "icon")

        w = self.winfo_width()
        h = self.winfo_height()
        r = self.CORNER_RADIUS

        if w < 50 or h < 50:
            return

        # Draw background
        if self._maximized:
            self.canvas.create_rectangle(
                0, 0, w, h, fill=colors["bg"], outline="", tags="bg"
            )
        else:
            self._draw_rounded_rect(
                0,
                0,
                w,
                h,
                radius=r,
                fill=colors["bg"],
                outline=colors["border"],
                width=1,
                tags="bg",
            )

        # Icon
        if self._icon_path:
            self.canvas.create_text(
                18,
                self.TITLE_HEIGHT // 2,
                text="⚔",
                fill=colors["accent"],
                font=("Segoe UI Emoji", 12),
                anchor="w",
                tags="icon",
            )

        # Title
        title_x = 40 if self._icon_path else 15
        self.canvas.create_text(
            title_x,
            self.TITLE_HEIGHT // 2,
            text=self._title,
            fill=colors["fg"],
            font=FONTS["bold"],
            anchor="w",
            tags="title",
        )

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        """Draw rounded rectangle"""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _create_controls(self):
        """Create window control buttons"""
        self.controls_frame = tk.Frame(self.canvas, bg=colors["bg"])

        # Create buttons
        buttons = [
            ("─", self.minimize, colors["card_hover"]),
            ("□", self.toggle_maximize, colors["card_hover"]),
            ("✕", self.close, "#ff4757"),
        ]

        for text, command, hover_color in buttons:
            btn = tk.Label(
                self.controls_frame,
                text=text,
                font=("Segoe UI", 10),
                bg=colors["bg"],
                fg=colors["fg"],
                width=4,
                height=1,
                cursor="hand2",
            )
            btn.pack(side="left", padx=1)

            # Bind events
            btn.bind(
                "<Enter>",
                lambda e, b=btn, hc=hover_color: b.configure(bg=hc, fg="white"),
            )
            btn.bind(
                "<Leave>",
                lambda e, b=btn: b.configure(bg=colors["bg"], fg=colors["fg"]),
            )
            btn.bind("<Button-1>", lambda e, cmd=command: cmd())

    def _update_layout(self):
        """Update content and controls positions"""
        w = self.winfo_width()
        h = self.winfo_height()

        if w < 50 or h < 50:
            return

        # Delete old window placements
        self.canvas.delete("controls_win", "content_win")

        # Place controls
        self.canvas.create_window(
            w - 10, 5, window=self.controls_frame, anchor="ne", tags="controls_win"
        )

        # Place content frame
        content_height = h - self.TITLE_HEIGHT - (8 if not self._maximized else 0)
        self._content_window_id = self.canvas.create_window(
            4,
            self.TITLE_HEIGHT,
            window=self.content_frame,
            anchor="nw",
            width=w - 8,
            height=max(1, content_height),
            tags="content_win",
        )

    def _on_configure(self, event):
        """Handle window resize"""
        if event.widget == self:
            self._draw_window()
            self._update_layout()

    # === Drag and Resize ===

    def _get_resize_edge(self, x, y):
        """Determine which edge (if any) the mouse is on"""
        if self._maximized:
            return None

        w = self.winfo_width()
        h = self.winfo_height()
        m = self.RESIZE_MARGIN

        edge = ""
        if y < m:
            edge += "n"
        elif y > h - m:
            edge += "s"
        if x < m:
            edge += "w"
        elif x > w - m:
            edge += "e"

        return edge if edge else None

    def _on_hover(self, event):
        """Update cursor based on position"""
        edge = self._get_resize_edge(event.x, event.y)

        if edge:
            cursor_map = {
                "n": "top_side",
                "s": "bottom_side",
                "w": "left_side",
                "e": "right_side",
                "nw": "top_left_corner",
                "ne": "top_right_corner",
                "sw": "bottom_left_corner",
                "se": "bottom_right_corner",
            }
            self.canvas.config(cursor=cursor_map.get(edge, ""))
        else:
            self.canvas.config(cursor="")

    def _on_leave(self, event):
        """Reset cursor when mouse leaves canvas"""
        self.canvas.config(cursor="")

    def _on_content_enter(self, event):
        """Reset cursor when mouse enters content area"""
        self.canvas.config(cursor="")

    def _on_press(self, event):
        """Handle mouse press - start drag or resize"""
        edge = self._get_resize_edge(event.x, event.y)

        if edge:
            # Start resize
            self._resize_mode = edge
            self._resize_start_geom = self._parse_geometry()
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
        elif event.y < self.TITLE_HEIGHT:
            # Start drag (in title bar area)
            self._resize_mode = None
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._drag_start_win_x = self.winfo_x()
            self._drag_start_win_y = self.winfo_y()
        else:
            self._resize_mode = None

    def _on_motion(self, event):
        """Handle mouse motion - perform drag or resize"""
        if self._maximized:
            return

        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y

        if self._resize_mode:
            # Resize
            x, y, w, h = self._resize_start_geom

            if "e" in self._resize_mode:
                w += dx
            if "w" in self._resize_mode:
                w -= dx
                x += dx
            if "s" in self._resize_mode:
                h += dy
            if "n" in self._resize_mode:
                h -= dy
                y += dy

            # Minimum size
            w = max(200, w)
            h = max(100, h)

            self.geometry(f"{w}x{h}+{x}+{y}")
        elif self._drag_start_win_x is not None:
            # Drag
            new_x = self._drag_start_win_x + dx
            new_y = self._drag_start_win_y + dy
            self.geometry(f"+{new_x}+{new_y}")

    def _on_release(self, event):
        """Handle mouse release"""
        self._resize_mode = None

    def _on_double_click(self, event):
        """Handle double click on title bar"""
        if event.y < self.TITLE_HEIGHT:
            self.toggle_maximize()

    def _parse_geometry(self):
        """Parse current geometry into (x, y, w, h)"""
        geom = self.geometry()
        # Format: WxH+X+Y
        parts = geom.replace("x", "+").split("+")
        w = int(parts[0])
        h = int(parts[1])
        x = int(parts[2]) if len(parts) > 2 else self.winfo_x()
        y = int(parts[3]) if len(parts) > 3 else self.winfo_y()
        return x, y, w, h

    # === Window Actions ===

    def minimize(self):
        """Minimize window to taskbar"""
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._on_map)

    def _on_map(self, event):
        """Restore window decorations on unminimize"""
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<Map>")

    def toggle_maximize(self):
        """Toggle maximize state"""
        if self._maximized:
            # Restore
            if self._prev_geom:
                self.geometry(self._prev_geom)
            self._maximized = False
        else:
            # Maximize
            self._prev_geom = self.geometry()
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            self.geometry(f"{screen_w}x{screen_h}+0+0")
            self._maximized = True

        # Redraw
        self._draw_window()
        self._update_layout()

    def set_on_close(self, callback):
        """Set callback to be called before window is closed.
        This allows child frames to save their state before destruction.
        """
        self._on_close_callback = callback

    def close(self):
        """Close window - calls on_close_callback first if set"""
        # Call the close callback first (allows child frames to save state)
        if self._on_close_callback:
            try:
                self._on_close_callback()
            except Exception as e:
                print(f"[FramelessWindow] Error in on_close callback: {e}")
        self.destroy()
