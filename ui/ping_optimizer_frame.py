"""
Ping Optimizer Frame
Dashboard UI with Before/After comparison and Status
"""

import tkinter as tk
from tkinter import Canvas
import math
from typing import Optional, Callable

from .theme import COLORS, FONTS, ModernButton
from .animations import draw_rounded_rect, interpolate_color
from .i18n import t


class PingOptimizerFrame(tk.Frame):
    """Ping Optimizer Dashboard UI"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)

        from services.ping_optimizer_service import get_ping_optimizer

        self.optimizer = get_ping_optimizer()
        self._keep_running_on_close = True

        self._create_ui()
        self.after(500, self._initial_ping)

        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget != self:
            return
        if not self._keep_running_on_close:
            self.optimizer.stop_realtime_monitor()

    def _create_ui(self):
        """Create Dashboard UI with hidden scroll"""

        # =========== SCROLLABLE CONTAINER ===========
        # Canvas for scrolling
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Scrollbar (hidden)
        self.scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        # Don't pack scrollbar - keep it hidden

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Content frame inside canvas
        self.content_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw"
        )

        # Bind resize and scroll events
        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # =========== BEFORE/AFTER CARD ===========
        comparison_frame = tk.Frame(
            self.content_frame, bg=COLORS["card"], padx=15, pady=12
        )
        comparison_frame.pack(fill="x", padx=20, pady=(15, 10))

        # Title
        tk.Label(
            comparison_frame,
            text="📊 PING COMPARISON",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        # Before/After row
        compare_row = tk.Frame(comparison_frame, bg=COLORS["card"])
        compare_row.pack(fill="x", pady=(10, 5))

        # Before
        before_frame = tk.Frame(compare_row, bg=COLORS["card"])
        before_frame.pack(side="left", expand=True)

        tk.Label(
            before_frame,
            text="Trước",
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack()

        self.before_label = tk.Label(
            before_frame,
            text="--",
            font=("Segoe UI", 28, "bold"),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        )
        self.before_label.pack()

        tk.Label(
            before_frame,
            text="ms",
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack()

        # Arrow
        tk.Label(
            compare_row,
            text="→",
            font=("Segoe UI", 24),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(side="left", padx=15)

        # After
        after_frame = tk.Frame(compare_row, bg=COLORS["card"])
        after_frame.pack(side="left", expand=True)

        tk.Label(
            after_frame,
            text="Sau",
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack()

        self.after_label = tk.Label(
            after_frame,
            text="--",
            font=("Segoe UI", 28, "bold"),
            bg=COLORS["card"],
            fg="#00d9a0",  # Green
        )
        self.after_label.pack()

        tk.Label(
            after_frame,
            text="ms",
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack()

        # Improvement
        self.improvement_label = tk.Label(
            comparison_frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["card"],
            fg="#00d9a0",
        )
        self.improvement_label.pack(pady=(5, 0))

        # =========== STATUS CARD ===========
        status_frame = tk.Frame(self.content_frame, bg=COLORS["card"], padx=15, pady=12)
        status_frame.pack(fill="x", padx=20, pady=(5, 10))

        tk.Label(
            status_frame,
            text="⚙️ OPTIMIZATION STATUS",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        # Status items
        self.status_dns = tk.Label(
            status_frame,
            text="○ DNS: Chưa tối ưu",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
            anchor="w",
        )
        self.status_dns.pack(fill="x", pady=(8, 2))

        self.status_tcp = tk.Label(
            status_frame,
            text="○ TCP Throttling: Chưa tối ưu",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
            anchor="w",
        )
        self.status_tcp.pack(fill="x", pady=2)

        self.status_cache = tk.Label(
            status_frame,
            text="○ DNS Cache: Chưa flush",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
            anchor="w",
        )
        self.status_cache.pack(fill="x", pady=2)

        # =========== BOOST BUTTON ===========
        boost_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        boost_frame.pack(fill="x", padx=20, pady=(10, 5))

        self.boost_btn = tk.Button(
            boost_frame,
            text="⚡ BOOST NETWORK",
            font=("Segoe UI", 14, "bold"),
            bg="#8b5cf6",
            fg="white",
            activebackground="#7c3aed",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._one_click_boost,
        )
        self.boost_btn.pack(fill="x", ipady=12)

        # Progress label
        self.boost_progress = tk.Label(
            boost_frame,
            text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["accent"],
        )
        self.boost_progress.pack(pady=(5, 0))

        # =========== QUOTE PANEL ===========
        quote_frame = tk.Frame(self.content_frame, bg=COLORS["card"], padx=15, pady=12)
        quote_frame.pack(fill="x", padx=20, pady=(10, 15))

        tk.Label(
            quote_frame,
            text="💡 CÁCH HOẠT ĐỘNG",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        quote_text = """• DNS Optimization: Tìm DNS server nhanh nhất (Cloudflare, Google...) và áp dụng vào hệ thống

• TCP Throttling: Tắt giới hạn băng thông của Windows để game nhận data nhanh hơn

• DNS Cache: Xóa cache DNS cũ/lỗi để kết nối trực tiếp đến server mới

⚠️ Một số tính năng cần chạy với quyền Admin"""

        tk.Label(
            quote_frame,
            text=quote_text,
            font=("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
            justify="left",
            anchor="w",
            wraplength=280,
        ).pack(fill="x", pady=(8, 0))

    def _on_content_configure(self, event):
        """Update scrollregion when content changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Update content frame width when canvas resizes"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _initial_ping(self):
        """Measure initial ping"""

        def on_complete(result):
            if result.success:
                self.after(
                    0,
                    lambda: self.before_label.config(text=str(int(result.latency_ms))),
                )

        self.optimizer.ping_game_server(on_complete=on_complete)

    def _one_click_boost(self):
        """Run boost and update dashboard"""
        self.boost_btn.config(state="disabled", text="⏳ Đang tối ưu...")
        self.boost_progress.config(text="Bắt đầu...")

        def on_progress(step_name, percent):
            self.after(
                0, lambda: self.boost_progress.config(text=f"{step_name} ({percent}%)")
            )

        def on_complete(success, summary):
            def update_ui():
                self.boost_btn.config(state="normal", text="⚡ BOOST NETWORK")
                self.boost_progress.config(text="")

                # Update dashboard from service state
                status = self.optimizer.get_optimization_status()

                # Update Before/After
                if status["ping_before"]:
                    self.before_label.config(text=str(int(status["ping_before"])))
                if status["ping_after"]:
                    self.after_label.config(text=str(int(status["ping_after"])))

                # Update improvement %
                improvement = self.optimizer.get_improvement_percent()
                if improvement is not None:
                    if improvement > 0:
                        self.improvement_label.config(
                            text=f"↓ {improvement}% nhanh hơn", fg="#00d9a0"
                        )
                    elif improvement < 0:
                        self.improvement_label.config(
                            text=f"↑ {abs(improvement)}% chậm hơn", fg="#f38ba8"
                        )
                    else:
                        self.improvement_label.config(
                            text="Không đổi", fg=COLORS["fg_dim"]
                        )

                # Update status items
                opts = status["optimizations"]

                if opts["dns"]["active"]:
                    dns_name = opts["dns"]["name"] or "?"
                    dns_lat = opts["dns"]["latency"]
                    self.status_dns.config(
                        text=f"✅ DNS: {dns_name} ({dns_lat:.0f}ms)", fg="#00d9a0"
                    )

                if opts["tcp"]["active"]:
                    self.status_tcp.config(
                        text="✅ TCP Throttling: Đã tắt", fg="#00d9a0"
                    )

                if opts["dns_cache"]["active"]:
                    self.status_cache.config(
                        text="✅ DNS Cache: Đã flush", fg="#00d9a0"
                    )

            self.after(0, update_ui)

        self.optimizer.one_click_boost(on_progress=on_progress, on_complete=on_complete)
