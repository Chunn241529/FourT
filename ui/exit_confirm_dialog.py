"""
Modern Exit Confirmation Dialog
A beautiful borderless popup with animations for confirming app exit
"""

import tkinter as tk
from .theme import colors, FONTS, COLORS, ModernButton
from .animations import FadeEffect, draw_rounded_rect


class ExitConfirmDialog(tk.Toplevel):
    """
    Custom exit confirmation dialog with modern UI.
    - Borderless (no title bar)
    - Rounded corners effect
    - Fade in/out animations
    - Beautiful gradient and shadow effects
    """
    
    CORNER_RADIUS = 16
    WIDTH = 320
    HEIGHT = 180
    
    def __init__(self, parent, on_confirm=None, on_cancel=None):
        super().__init__(parent)
        self.parent = parent
        self.on_confirm_callback = on_confirm
        self.on_cancel_callback = on_cancel
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
        self.bind('<Escape>', lambda e: self._on_cancel())
        self.bind('<Return>', lambda e: self._on_confirm())
        
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
        highlight_height = 40
        draw_rounded_rect(
            self.canvas,
            pad, pad,
            w - pad, pad + highlight_height,
            radius=r,
            fill='#1e1e35',
            outline=''
        )
    
    def _build_ui(self):
        """Build the dialog UI elements"""
        pad = 8
        
        # Container frame (placed on top of canvas)
        container = tk.Frame(self, bg=COLORS['card'])
        container.place(
            x=pad + 10,
            y=pad + 10,
            width=self.WIDTH - 2 * pad - 20,
            height=self.HEIGHT - 2 * pad - 20
        )
        
        # Icon + Title row
        title_frame = tk.Frame(container, bg=COLORS['card'])
        title_frame.pack(fill='x', pady=(5, 10))
        
        # Warning icon
        icon_label = tk.Label(
            title_frame,
            text="⚠️",
            font=("Segoe UI Emoji", 20),
            bg=COLORS['card'],
            fg=COLORS['warning']
        )
        icon_label.pack(side='left', padx=(0, 10))
        
        # Title
        title_label = tk.Label(
            title_frame,
            text="Xác nhận thoát",
            font=FONTS['h1'],
            bg=COLORS['card'],
            fg=COLORS['fg']
        )
        title_label.pack(side='left', anchor='w')
        
        # Message
        message_label = tk.Label(
            container,
            text="Bạn có chắc chắn muốn thoát ứng dụng?",
            font=FONTS['body'],
            bg=COLORS['card'],
            fg=COLORS['fg_dim'],
            wraplength=self.WIDTH - 60
        )
        message_label.pack(fill='x', pady=(0, 20))
        
        # Button row - right aligned with buttons close together
        btn_frame = tk.Frame(container, bg=COLORS['card'])
        btn_frame.pack(fill='x', side='bottom')
        
        # Inner frame to keep buttons close together (right aligned)
        btn_inner = tk.Frame(btn_frame, bg=COLORS['card'])
        btn_inner.pack(side='right')
        
        # Cancel button
        cancel_btn = ModernButton(
            btn_inner,
            text="Hủy",
            command=self._on_cancel,
            kind='secondary',
            width=10
        )
        cancel_btn.pack(side='left', padx=(0, 8))
        
        # Confirm button (accent style - more visible)
        confirm_btn = ModernButton(
            btn_inner,
            text="Thoát",
            command=self._on_confirm,
            kind='accent',
            width=10
        )
        confirm_btn.pack(side='left')
        
        # Focus on cancel by default (safer)
        cancel_btn.focus_set()
    
    def _on_confirm(self):
        """Handle confirm action"""
        self.result = True
        callback = self.on_confirm_callback
        # Close immediately without animation to ensure callback works
        self._close_immediately(callback)
    
    def _on_cancel(self):
        """Handle cancel action"""
        self.result = False
        callback = self.on_cancel_callback
        self._close(callback)
    
    def _close_immediately(self, callback=None):
        """Close immediately and execute callback (for exit)"""
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
        parent = self.parent  # Save reference before destroy
        
        def do_destroy():
            try:
                self.grab_release()
                self.destroy()
            except tk.TclError:
                pass
            # Call callback AFTER window is destroyed
            if callback:
                callback()
        
        FadeEffect.fade_out(self, duration=80, on_complete=do_destroy)


def show_exit_confirm(parent, on_confirm=None):
    """
    Convenience function to show exit confirmation dialog.
    
    Args:
        parent: Parent window
        on_confirm: Callback to execute if user confirms exit
    
    Returns:
        ExitConfirmDialog instance
    """
    return ExitConfirmDialog(parent, on_confirm=on_confirm)
