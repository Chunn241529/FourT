"""
Animation Utilities for Tkinter
Provides smooth animations for UI components
"""

import tkinter as tk
from typing import Callable, Optional
from functools import lru_cache
import colorsys


@lru_cache(maxsize=256)
def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple (cached for performance)"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color"""
    return f'#{r:02x}{g:02x}{b:02x}'


def interpolate_color(color1: str, color2: str, t: float) -> str:
    """Interpolate between two colors. t=0 gives color1, t=1 gives color2"""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return rgb_to_hex(r, g, b)


def lighten_color(hex_color: str, amount: float = 0.2) -> str:
    """Lighten a color by a given amount (0-1)"""
    r, g, b = hex_to_rgb(hex_color)
    # Convert to HLS, increase lightness, convert back
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    l = min(1.0, l + amount)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(int(r*255), int(g*255), int(b*255))


def darken_color(hex_color: str, amount: float = 0.2) -> str:
    """Darken a color by a given amount (0-1)"""
    r, g, b = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    l = max(0.0, l - amount)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(int(r*255), int(g*255), int(b*255))


class AnimationMixin:
    """Mixin class providing animation capabilities to widgets"""
    
    def animate_property(self, property_name: str, start_val: float, end_val: float, 
                        duration: int = 200, easing: str = 'ease_out',
                        on_complete: Optional[Callable] = None):
        """
        Animate a numeric property from start to end value
        
        Args:
            property_name: Name of the property to animate
            start_val: Starting value
            end_val: Ending value  
            duration: Duration in milliseconds
            easing: Easing function ('linear', 'ease_in', 'ease_out', 'ease_in_out')
            on_complete: Callback when animation completes
        """
        steps = max(1, duration // 16)  # ~60fps
        step_time = duration // steps
        
        def ease(t: float) -> float:
            if easing == 'ease_out':
                return 1 - (1 - t) ** 3
            elif easing == 'ease_in':
                return t ** 3
            elif easing == 'ease_in_out':
                return 3 * t ** 2 - 2 * t ** 3
            return t  # linear
        
        def step(current_step: int):
            if current_step >= steps:
                setattr(self, property_name, end_val)
                if on_complete:
                    on_complete()
                return
            
            t = ease(current_step / steps)
            value = start_val + (end_val - start_val) * t
            setattr(self, property_name, value)
            
            self.after(step_time, lambda: step(current_step + 1))
        
        step(0)


class FadeEffect:
    """Fade in/out effect for Toplevel windows"""
    
    @staticmethod
    def fade_in(window: tk.Toplevel, duration: int = 100, 
                start_alpha: float = 0.0, end_alpha: float = 1.0,
                on_complete: Optional[Callable] = None):
        """Fade in a toplevel window (optimized: 100ms default)"""
        steps = max(1, duration // 16)
        step_time = duration // steps
        
        def step(current: int):
            if current >= steps:
                try:
                    window.attributes('-alpha', end_alpha)
                except tk.TclError:
                    pass
                if on_complete:
                    on_complete()
                return
            
            t = 1 - (1 - current / steps) ** 2  # ease_out
            alpha = start_alpha + (end_alpha - start_alpha) * t
            
            try:
                window.attributes('-alpha', alpha)
                window.after(step_time, lambda: step(current + 1))
            except tk.TclError:
                pass  # Window was destroyed
        
        window.attributes('-alpha', start_alpha)
        step(0)
    
    @staticmethod
    def fade_out(window: tk.Toplevel, duration: int = 80,
                 on_complete: Optional[Callable] = None):
        """Fade out and optionally destroy window (optimized: 80ms default)"""
        try:
            start_alpha = window.attributes('-alpha')
        except tk.TclError:
            return
            
        steps = max(1, duration // 16)
        step_time = duration // steps
        
        def step(current: int):
            if current >= steps:
                if on_complete:
                    on_complete()
                return
            
            t = current / steps
            alpha = start_alpha * (1 - t)
            
            try:
                window.attributes('-alpha', alpha)
                window.after(step_time, lambda: step(current + 1))
            except tk.TclError:
                pass
        
        step(0)


class SlideEffect:
    """Slide in/out effect for Toplevel windows"""
    
    @staticmethod
    def slide_in(window: tk.Toplevel, target_x: int, target_y: int,
                 direction: str = 'left', distance: int = 20, 
                 duration: int = 100, on_complete: Optional[Callable] = None):
        """
        Slide window in from a direction (optimized: 100ms default)
        
        Args:
            window: The toplevel window
            target_x, target_y: Final position
            direction: 'left', 'right', 'up', 'down'
            distance: How far to slide from
            duration: Animation duration in ms
        """
        # Calculate start position
        if direction == 'left':
            start_x, start_y = target_x - distance, target_y
        elif direction == 'right':
            start_x, start_y = target_x + distance, target_y
        elif direction == 'up':
            start_x, start_y = target_x, target_y - distance
        else:  # down
            start_x, start_y = target_x, target_y + distance
        
        steps = max(1, duration // 16)
        step_time = duration // steps
        
        def ease_out(t: float) -> float:
            return 1 - (1 - t) ** 3
        
        def step(current: int):
            if current >= steps:
                try:
                    window.geometry(f"+{target_x}+{target_y}")
                except tk.TclError:
                    pass
                if on_complete:
                    on_complete()
                return
            
            t = ease_out(current / steps)
            x = int(start_x + (target_x - start_x) * t)
            y = int(start_y + (target_y - start_y) * t)
            
            try:
                window.geometry(f"+{x}+{y}")
                window.after(step_time, lambda: step(current + 1))
            except tk.TclError:
                pass
        
        window.geometry(f"+{start_x}+{start_y}")
        step(0)


class ScaleEffect:
    """Scale animation for canvas-based widgets"""
    
    @staticmethod
    def pulse(canvas: tk.Canvas, tag: str, center_x: float, center_y: float,
              scale_factor: float = 1.1, duration: int = 150):
        """Create a pulse effect on canvas items"""
        # This is a simplified version - full implementation would
        # need to track original coordinates
        pass


class ColorTransition:
    """Smooth color transitions for widgets"""
    
    @staticmethod
    def transition(widget, property_name: str, from_color: str, to_color: str,
                   duration: int = 100, on_complete: Optional[Callable] = None):
        """
        Smoothly transition a widget's color property (optimized: 100ms default)
        
        Args:
            widget: The tkinter widget
            property_name: 'bg', 'fg', 'fill', etc.
            from_color: Starting color (hex)
            to_color: Ending color (hex)
            duration: Duration in milliseconds
        """
        steps = max(1, duration // 16)
        step_time = duration // steps
        
        def step(current: int):
            if current >= steps:
                try:
                    widget.configure(**{property_name: to_color})
                except tk.TclError:
                    pass
                if on_complete:
                    on_complete()
                return
            
            t = 1 - (1 - current / steps) ** 2  # ease_out
            color = interpolate_color(from_color, to_color, t)
            
            try:
                widget.configure(**{property_name: color})
                widget.after(step_time, lambda: step(current + 1))
            except tk.TclError:
                pass
        
        step(0)


def draw_rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                      radius: int = 10, **kwargs) -> int:
    """
    Draw a rounded rectangle on a canvas
    
    Returns the canvas item id
    """
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_soft_shadow(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                     radius: int = 10, blur_radius: int = 5, 
                     shadow_color: str = '#000000', alpha_steps: int = 3):
    """
    Draw a soft shadow effect using multiple semi-transparent layers
    """
    for i in range(alpha_steps, 0, -1):
        offset = i * (blur_radius // alpha_steps)
        # Calculate shadow alpha (darker closer to shape)
        r, g, b = hex_to_rgb(shadow_color)
        factor = (alpha_steps - i + 1) / (alpha_steps * 3)
        shadow = rgb_to_hex(
            min(255, int(r + (255 - r) * (1 - factor))),
            min(255, int(g + (255 - g) * (1 - factor))),
            min(255, int(b + (255 - b) * (1 - factor)))
        )
        draw_rounded_rect(canvas, 
                         x1 + offset, y1 + offset, 
                         x2 + offset, y2 + offset,
                         radius=radius, fill=shadow, outline='')
