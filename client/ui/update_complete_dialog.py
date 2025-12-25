"""
Update Complete Dialog
A beautiful borderless popup to notify user that update is downloaded and ready to install
"""

import os
import tkinter as tk
from .theme import colors, FONTS, COLORS, ModernButton
from .animations import FadeEffect, draw_rounded_rect


class UpdateCompleteDialog(tk.Toplevel):
    """
    Custom update complete dialog with modern UI.
    - Borderless (no title bar)
    - Rounded corners effect
    - Fade in/out animations
    - Beautiful gradient and shadow effects
    """
    
    CORNER_RADIUS = 16
    WIDTH = 400
    HEIGHT = 240
    
    def __init__(self, parent, installer_path: str, new_version: str, 
                 on_install=None, on_later=None):
        super().__init__(parent)
        self.parent = parent
        self.installer_path = installer_path
        self.new_version = new_version
        self.on_install_callback = on_install
        self.on_later_callback = on_later
        self.result = False
        
        # Window setup - borderless
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(bg='black')
        self.attributes('-transparentcolor', 'black')
        
        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.WIDTH) // 2
        y = (screen_height - self.HEIGHT) // 2
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
        
        # Canvas for rounded background
        self.canvas = tk.Canvas(
            self, 
            width=self.WIDTH, 
            height=self.HEIGHT,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Draw background
        self._draw_background()
        
        # Build UI
        self._build_ui()
        
        # Bindings
        self.bind('<Escape>', lambda e: self._on_later())
        self.bind('<Return>', lambda e: self._on_install())
        
        # Grab focus
        self.grab_set()
        self.focus_force()
        
        # Animate in
        self.attributes('-alpha', 0)
        FadeEffect.fade_in(self, duration=150, end_alpha=0.98)
    
    def _draw_background(self):
        """Draw rounded rectangle background with shadow effect"""
        w, h = self.WIDTH, self.HEIGHT
        r = self.CORNER_RADIUS
        pad = 8  # Padding for shadow
        
        # Shadow layers (multiple offset layers for soft shadow)
        shadow_colors = ['#0a0a0a', '#111111', '#181818']
        for i, shadow_color in enumerate(shadow_colors):
            offset = 6 - i * 2
            draw_rounded_rect(
                self.canvas,
                pad + offset, pad + offset,
                w - pad + offset, h - pad + offset,
                radius=r,
                fill=shadow_color,
                outline=''
            )
        
        # Main background with gradient-like effect (darker at bottom)
        draw_rounded_rect(
            self.canvas,
            pad, pad,
            w - pad, h - pad,
            radius=r,
            fill=COLORS['card'],
            outline=COLORS['border'],
            width=1
        )
        
        # Top highlight strip for glass effect
        highlight_height = 50
        draw_rounded_rect(
            self.canvas,
            pad, pad,
            w - pad, pad + highlight_height,
            radius=r,
            fill='#1a2e1a',  # Green tint for success
            outline=''
        )
    
    def _build_ui(self):
        """Build the dialog UI elements"""
        pad = 8
        
        # Container frame (placed on top of canvas)
        container = tk.Frame(self, bg=COLORS['card'])
        container.place(
            x=pad + 15,
            y=pad + 15,
            width=self.WIDTH - 2 * pad - 30,
            height=self.HEIGHT - 2 * pad - 30
        )
        
        # Icon + Title row
        title_frame = tk.Frame(container, bg=COLORS['card'])
        title_frame.pack(fill='x', pady=(5, 10))
        
        # Success icon
        icon_label = tk.Label(
            title_frame,
            text="✅",
            font=("Segoe UI Emoji", 24),
            bg=COLORS['card'],
            fg=COLORS['success']
        )
        icon_label.pack(side='left', padx=(0, 12))
        
        # Title
        title_label = tk.Label(
            title_frame,
            text="Đã tải xong bản cập nhật!",
            font=FONTS['h1'],
            bg=COLORS['card'],
            fg=COLORS['fg']
        )
        title_label.pack(side='left', anchor='w')
        
        # Version info
        version_label = tk.Label(
            container,
            text=f"Phiên bản mới: v{self.new_version}",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS['card'],
            fg=COLORS['success']
        )
        version_label.pack(fill='x', pady=(0, 8))
        
        # Message
        message_label = tk.Label(
            container,
            text="Nhấn 'Cài đặt ngay' để mở trình cài đặt.\nỨng dụng sẽ đóng và cài đặt bản cập nhật mới.",
            font=FONTS['body'],
            bg=COLORS['card'],
            fg=COLORS['fg_dim'],
            wraplength=self.WIDTH - 80,
            justify='left'
        )
        message_label.pack(fill='x', pady=(0, 20))
        
        # Button row - right aligned with buttons close together
        btn_frame = tk.Frame(container, bg=COLORS['card'])
        btn_frame.pack(fill='x', side='bottom')
        
        # Inner frame to keep buttons close together (right aligned)
        btn_inner = tk.Frame(btn_frame, bg=COLORS['card'])
        btn_inner.pack(side='right')
        
        # Later button
        later_btn = ModernButton(
            btn_inner,
            text="Để sau",
            command=self._on_later,
            kind='secondary',
            width=10
        )
        later_btn.pack(side='left', padx=(0, 10))
        
        # Install button (success style)
        install_btn = ModernButton(
            btn_inner,
            text="Cài đặt ngay",
            command=self._on_install,
            kind='success',
            width=12
        )
        install_btn.pack(side='left')
        
        # Focus on install by default
        install_btn.focus_set()
    
    def _on_install(self):
        """Handle install action"""
        self.result = True
        callback = self.on_install_callback
        self._close_immediately(callback)
    
    def _on_later(self):
        """Handle later action"""
        self.result = False
        callback = self.on_later_callback
        self._close(callback)
    
    def _close_immediately(self, callback=None):
        """Close immediately and execute callback"""
        try:
            self.grab_release()
            self.destroy()
        except tk.TclError:
            pass
        # Call callback directly
        if callback:
            callback()
    
    def _close(self, callback=None):
        """Close with fade out animation"""
        def do_destroy():
            try:
                self.grab_release()
                self.destroy()
            except tk.TclError:
                pass
            if callback:
                callback()
        
        FadeEffect.fade_out(self, duration=80, on_complete=do_destroy)


def show_update_complete(parent, installer_path: str, new_version: str, 
                        on_install=None, on_later=None):
    """
    Convenience function to show update complete dialog.
    
    Args:
        parent: Parent window
        installer_path: Path to downloaded installer
        new_version: Version string
        on_install: Callback when user clicks install
        on_later: Callback when user clicks later
    
    Returns:
        UpdateCompleteDialog instance
    """
    return UpdateCompleteDialog(
        parent, installer_path, new_version,
        on_install=on_install, on_later=on_later
    )
