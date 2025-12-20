"""
Ping Optimizer Frame
Modern UI for network optimization with animated ping display
"""

import tkinter as tk
from tkinter import Canvas, messagebox
import math
import time
from typing import Optional, Callable

from .theme import COLORS, FONTS, ModernButton, GradientCard
from .animations import (
    FadeEffect, ColorTransition, 
    hex_to_rgb, rgb_to_hex, interpolate_color, draw_rounded_rect
)


class AnimatedPingDisplay(Canvas):
    """
    Large animated ping display with:
    - Count-up animation
    - Color transition based on quality
    - Glow/pulse effect while measuring
    """
    
    def __init__(self, parent, width=280, height=200, **kwargs):
        super().__init__(
            parent, 
            width=width, 
            height=height,
            bg=COLORS['bg'],
            highlightthickness=0,
            **kwargs
        )
        
        self.display_width = width
        self.display_height = height
        self._current_ping = 0
        self._target_ping = 0
        self._animation_id = None
        self._pulse_id = None
        self._pulse_phase = 0
        self._is_measuring = False
        self._quality_color = COLORS['success']
        
        self._draw_display()
    
    def _draw_display(self):
        """Draw the ping display"""
        self.delete('all')
        
        cx = self.display_width / 2
        cy = self.display_height / 2 - 10
        
        # Background card
        draw_rounded_rect(
            self, 10, 10, 
            self.display_width - 10, self.display_height - 10,
            radius=16,
            fill=COLORS['card'],
            outline=COLORS['border']
        )
        
        # Glow effect (when measuring)
        if self._is_measuring:
            glow_alpha = 0.3 + 0.2 * math.sin(self._pulse_phase)
            glow_color = interpolate_color(COLORS['card'], self._quality_color, glow_alpha)
            draw_rounded_rect(
                self, 15, 15,
                self.display_width - 15, self.display_height - 15,
                radius=14,
                fill=glow_color,
                outline=''
            )
        
        # Ping number (large)
        ping_text = f"{int(self._current_ping)}"
        self.create_text(
            cx, cy,
            text=ping_text,
            font=("Segoe UI", 56, "bold"),
            fill=self._quality_color,
            tags='ping_value'
        )
        
        # "ms" unit
        self.create_text(
            cx + 70, cy + 10,
            text="ms",
            font=("Segoe UI", 18),
            fill=COLORS['fg_dim'],
            tags='ping_unit'
        )
        
        # Quality indicator bar
        bar_y = cy + 50
        bar_width = 180
        bar_height = 6
        bar_x1 = (self.display_width - bar_width) / 2
        bar_x2 = bar_x1 + bar_width
        
        # Background bar
        draw_rounded_rect(
            self, bar_x1, bar_y,
            bar_x2, bar_y + bar_height,
            radius=3,
            fill=COLORS['input_bg'],
            outline=''
        )
        
        # Fill bar (based on ping quality - inversely proportional)
        fill_ratio = max(0, min(1, 1 - (self._current_ping / 200)))
        fill_width = bar_width * fill_ratio
        if fill_width > 0:
            draw_rounded_rect(
                self, bar_x1, bar_y,
                bar_x1 + fill_width, bar_y + bar_height,
                radius=3,
                fill=self._quality_color,
                outline=''
            )
        
        # Quality label
        quality_label = self._get_quality_label()
        self.create_text(
            cx, bar_y + 20,
            text=quality_label,
            font=("Segoe UI", 10),
            fill=COLORS['fg_dim'],
            tags='quality_label'
        )
    
    def _get_quality_label(self) -> str:
        """Get quality label based on ping"""
        ping = self._current_ping
        if ping < 30:
            return "Xuất sắc"
        elif ping < 60:
            return "Tốt"
        elif ping < 100:
            return "Trung bình"
        elif ping < 150:
            return "Kém"
        else:
            return "Rất kém"
    
    def _get_quality_color(self, ping: float) -> str:
        """Get color based on ping value"""
        if ping < 30:
            return "#00d9a0"  # Teal
        elif ping < 60:
            return "#a6e3a1"  # Green
        elif ping < 100:
            return "#f9e2af"  # Yellow
        elif ping < 150:
            return "#fab387"  # Orange
        else:
            return "#f38ba8"  # Red
    
    def set_ping(self, value: float, animate: bool = True):
        """Set ping value with optional animation"""
        self._target_ping = value
        self._quality_color = self._get_quality_color(value)
        
        if animate and abs(self._current_ping - value) > 1:
            self._animate_to_value()
        else:
            self._current_ping = value
            self._draw_display()
    
    def _animate_to_value(self):
        """Animate ping counter to target value"""
        if self._animation_id:
            self.after_cancel(self._animation_id)
        
        def step():
            diff = self._target_ping - self._current_ping
            
            if abs(diff) < 1:
                self._current_ping = self._target_ping
                self._draw_display()
                return
            
            # Ease out
            step_size = diff * 0.15
            if abs(step_size) < 0.5:
                step_size = 0.5 if diff > 0 else -0.5
            
            self._current_ping += step_size
            self._draw_display()
            
            self._animation_id = self.after(30, step)
        
        step()
    
    def start_measuring(self):
        """Start pulse animation for measuring state"""
        self._is_measuring = True
        self._pulse_phase = 0
        self._run_pulse()
    
    def stop_measuring(self):
        """Stop measuring animation"""
        self._is_measuring = False
        if self._pulse_id:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None
        self._draw_display()
    
    def _run_pulse(self):
        """Run pulse animation frame"""
        if not self._is_measuring:
            return
        
        self._pulse_phase += 0.15
        self._draw_display()
        
        self._pulse_id = self.after(50, self._run_pulse)


class AnimatedActionButton(Canvas):
    """
    Action button with special click animation:
    - Ripple effect on click
    - Icon spin animation
    - Success pulse when complete
    """
    
    def __init__(self, parent, text: str, icon: str, 
                 command: Optional[Callable] = None,
                 width=100, height=70, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS['bg'],
            highlightthickness=0,
            **kwargs
        )
        
        self.btn_width = width
        self.btn_height = height
        self.text = text
        self.icon = icon
        self.command = command
        
        self._is_hovered = False
        self._is_animating = False
        self._animation_phase = 0
        self._ripple_radius = 0
        self._animation_id = None
        self._spin_angle = 0
        
        self._draw_button()
        
        # Bindings
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _draw_button(self):
        """Draw the button"""
        self.delete('all')
        
        w, h = self.btn_width, self.btn_height
        cx, cy = w / 2, h / 2
        
        # Background - check for success flash first
        if getattr(self, '_success_flash', False):
            bg_color = COLORS['success']
            outline_color = COLORS['success']
        elif self._is_hovered:
            bg_color = COLORS['card_hover']
            outline_color = COLORS['accent']
        else:
            bg_color = COLORS['card']
            outline_color = COLORS['border']
        
        draw_rounded_rect(
            self, 4, 4, w - 4, h - 4,
            radius=12,
            fill=bg_color,
            outline=outline_color
        )
        
        # Ripple effect (when animating)
        if self._is_animating and self._ripple_radius > 0:
            alpha = max(0, 1 - (self._ripple_radius / (w / 2)))
            ripple_color = interpolate_color(bg_color, COLORS['accent'], alpha * 0.5)
            self.create_oval(
                cx - self._ripple_radius, cy - self._ripple_radius,
                cx + self._ripple_radius, cy + self._ripple_radius,
                fill=ripple_color, outline=''
            )
        
        # Icon (with rotation if spinning)
        icon_y = cy - 8
        self.create_text(
            cx, icon_y,
            text=self.icon,
            font=("Segoe UI Emoji", 20),
            fill=COLORS['accent'] if self._is_hovered else COLORS['fg'],
            tags='icon'
        )
        
        # Text
        self.create_text(
            cx, h - 16,
            text=self.text,
            font=("Segoe UI", 9),
            fill=COLORS['fg'] if not self._is_hovered else 'white',
            tags='text'
        )
        
        self.config(cursor='hand2')
    
    def _on_enter(self, event):
        self._is_hovered = True
        self._draw_button()
    
    def _on_leave(self, event):
        self._is_hovered = False
        self._draw_button()
    
    def _on_click(self, event):
        """Handle click with animation"""
        if self._is_animating:
            return
        
        self._is_animating = True
        self._ripple_radius = 0
        self._animation_phase = 0
        
        self._run_click_animation()
    
    def _run_click_animation(self):
        """Run the click animation sequence"""
        # Phase 0-10: Ripple expansion
        if self._animation_phase < 10:
            self._ripple_radius = (self._animation_phase / 10) * (self.btn_width / 2)
            self._animation_phase += 1
            self._draw_button()
            self._animation_id = self.after(40, self._run_click_animation)
        
        # Phase 10: Execute command
        elif self._animation_phase == 10:
            self._animation_phase += 1
            if self.command:
                self.command()
            self._animation_id = self.after(200, self._run_click_animation)
        
        # Phase 11-15: Fade out ripple
        elif self._animation_phase < 15:
            self._ripple_radius = (1 - (self._animation_phase - 10) / 5) * (self.btn_width / 2)
            self._animation_phase += 1
            self._draw_button()
            self._animation_id = self.after(50, self._run_click_animation)
        
        # Done
        else:
            self._is_animating = False
            self._ripple_radius = 0
            self._draw_button()
    
    def show_success(self):
        """Flash success state by redrawing with success color"""
        self._success_flash = True
        self._draw_button()
        
        # Reset after delay
        def reset():
            self._success_flash = False
            self._draw_button()
        
        self.after(300, reset)


class PingOptimizerFrame(tk.Frame):
    """Main Ping Optimizer UI"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg'], **kwargs)
        
        # Import service
        from services.ping_optimizer_service import (
            get_ping_optimizer, DNS_SERVERS, 
            get_quality_color, get_quality_label
        )
        
        self.optimizer = get_ping_optimizer()
        self.dns_servers = DNS_SERVERS
        
        self._status_text = ""
        
        self._create_ui()
        
        # Initial ping measurement
        self.after(500, self._measure_ping)
    
    def _create_ui(self):
        """Create the UI components"""
        # Ping Display (centered)
        display_container = tk.Frame(self, bg=COLORS['bg'])
        display_container.pack(fill='x', pady=(15, 15))
        self.ping_display = AnimatedPingDisplay(display_container, width=320, height=200)
        self.ping_display.pack(anchor='center')
        
        # Action Buttons Row (centered)
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=(0, 15))
        
        # Center the buttons using grid
        btn_container = tk.Frame(btn_frame, bg=COLORS['bg'])
        btn_container.pack(anchor='center')
        
        self.optimize_btn = AnimatedActionButton(
            btn_container,
            text="Optimize",
            icon="⚡",
            command=self._optimize_network,
            width=85, height=70
        )
        self.optimize_btn.pack(side='left', padx=4)
        
        self.flush_btn = AnimatedActionButton(
            btn_container,
            text="Flush DNS",
            icon="🔄",
            command=self._flush_network,
            width=85, height=70
        )
        self.flush_btn.pack(side='left', padx=4)
        
        self.dns_btn = AnimatedActionButton(
            btn_container,
            text="Best DNS",
            icon="🌐",
            command=self._find_best_dns,
            width=95, height=70
        )
        self.dns_btn.pack(side='left', padx=5)
        
        # DNS Selection (centered)
        dns_outer = tk.Frame(self, bg=COLORS['bg'])
        dns_outer.pack(fill='x', pady=(10, 15))
        
        dns_frame = tk.Frame(dns_outer, bg=COLORS['bg'])
        dns_frame.pack(anchor='center')
        
        tk.Label(
            dns_frame,
            text="DNS Server:",
            font=FONTS['body'],
            bg=COLORS['bg'],
            fg=COLORS['fg_dim']
        ).pack(side='left')
        
        self.dns_var = tk.StringVar(value="cloudflare")
        
        dns_options = [f"{dns.icon} {dns.name}" for dns in self.dns_servers.values()]
        self.dns_menu = tk.OptionMenu(
            dns_frame,
            self.dns_var,
            *self.dns_servers.keys(),
        )
        self.dns_menu.config(
            bg=COLORS['input_bg'],
            fg=COLORS['fg'],
            activebackground=COLORS['accent'],
            activeforeground='white',
            highlightthickness=0,
            bd=0,
            font=FONTS['body'],
            width=15
        )
        self.dns_menu["menu"].config(
            bg=COLORS['input_bg'],
            fg=COLORS['fg'],
            activebackground=COLORS['accent'],
            activeforeground='white',
            font=FONTS['body']
        )
        self.dns_menu.pack(side='left', padx=10)
        
        apply_dns_btn = ModernButton(
            dns_frame,
            text="Apply",
            command=self._apply_dns,
            kind='secondary'
        )
        apply_dns_btn.pack(side='left')
    
    def _set_status(self, text: str, color: str = None):
        """Update status text (hidden - no log display)"""
        pass  # Status display removed per user request
    
    def _measure_ping(self):
        """Measure ping to default target"""
        self.ping_display.start_measuring()
        self._set_status("Đang đo ping...")
        
        def on_complete(result):
            self.after(0, lambda: self._on_ping_result(result))
        
        self.optimizer.estimate_ping(on_complete=on_complete)
    
    def _on_ping_result(self, result):
        """Handle ping result"""
        self.ping_display.stop_measuring()
        
        if result.success:
            self.ping_display.set_ping(result.latency_ms)
            self._set_status(f"Ping: {result.latency_ms}ms → {result.target}")
        else:
            self.ping_display.set_ping(999)
            self._set_status(f"Lỗi: {result.error}", COLORS['error'])
    
    def _optimize_network(self):
        """Run TCP optimization"""
        self._set_status("Đang tối ưu TCP/IP...", COLORS['accent'])
        
        from services.ping_optimizer_service import PingOptimizer
        
        def on_complete(success, message):
            self.after(0, lambda: self._on_optimize_complete(success, message))
        
        PingOptimizer.optimize_tcp(on_complete=on_complete)
    
    def _on_optimize_complete(self, success: bool, message: str):
        """Handle optimization result"""
        if success:
            self._set_status("✅ Tối ưu thành công!\n" + message, COLORS['success'])
            self.optimize_btn.show_success()
            # Re-measure ping
            self.after(1000, self._measure_ping)
        else:
            self._set_status("⚠️ Cần chạy với quyền Admin\n" + message, COLORS['warning'])
    
    def _flush_network(self):
        """Flush network cache"""
        self._set_status("Đang flush network...", COLORS['accent'])
        
        from services.ping_optimizer_service import PingOptimizer
        
        def on_complete(success, message):
            self.after(0, lambda: self._on_flush_complete(success, message))
        
        PingOptimizer.flush_network(on_complete=on_complete)
    
    def _on_flush_complete(self, success: bool, message: str):
        """Handle flush result"""
        if success:
            self._set_status("✅ Flush thành công!\n" + message, COLORS['success'])
            self.flush_btn.show_success()
            self.after(1000, self._measure_ping)
        else:
            self._set_status("⚠️ Một số lệnh cần Admin\n" + message, COLORS['warning'])
    
    def _find_best_dns(self):
        """Benchmark DNS servers"""
        self._set_status("Đang benchmark DNS...", COLORS['accent'])
        
        def on_progress(name, latency):
            self.after(0, lambda: self._set_status(f"Testing {name}: {latency:.0f}ms"))
        
        def on_complete(results):
            self.after(0, lambda: self._on_dns_benchmark_complete(results))
        
        self.optimizer.benchmark_dns(
            on_progress=on_progress,
            on_complete=on_complete
        )
    
    def _on_dns_benchmark_complete(self, results):
        """Handle DNS benchmark results"""
        if results:
            best = results[0]
            self._set_status(
                f"🏆 DNS nhanh nhất: {best[0]} ({best[1]:.0f}ms)\n"
                f"#2: {results[1][0]} ({results[1][1]:.0f}ms)",
                COLORS['success']
            )
            # Set the dropdown to best DNS
            self.dns_var.set(best[2])
            self.dns_btn.show_success()
        else:
            self._set_status("Không thể benchmark DNS", COLORS['error'])
    
    def _apply_dns(self):
        """Apply selected DNS"""
        dns_key = self.dns_var.get()
        self._set_status(f"Đang đổi DNS...", COLORS['accent'])
        
        from services.ping_optimizer_service import PingOptimizer
        
        def on_complete(success, message):
            self.after(0, lambda: self._on_dns_apply_complete(success, message))
        
        PingOptimizer.set_dns(dns_key, on_complete=on_complete)
    
    def _on_dns_apply_complete(self, success: bool, message: str):
        """Handle DNS apply result"""
        if success:
            self._set_status("✅ Đã đổi DNS!\n" + message, COLORS['success'])
            self.after(1000, self._measure_ping)
        else:
            self._set_status("⚠️ Cần chạy với quyền Admin\n" + message, COLORS['warning'])
