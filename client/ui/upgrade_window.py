"""
Upgrade Window - Modern Professional Design
Features: Gradient background with animated pulse, rounded cards, hover effects
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import math

from core.config import (
    Packages,
    COLOR_BG,
    COLOR_TEXT,
    COLOR_PRIMARY,
    get_license_server_url,
)
from .theme import ModernButton, RoundedButton, colors, FONTS
from .payment_window import PaymentWindow
from feature_manager import get_feature_manager
from .i18n import t


class UpgradeWindow:
    """Professional Upgrade Window with Modern Design"""

    def __init__(self, parent):
        self.parent = parent
        from .components import FramelessWindow

        self.window = FramelessWindow(parent, title=t("upgrade_title"))
        self.window.geometry("1200x900")

        # Package data will be fetched from server
        self.packages_data = {}
        self.loading = True
        self.animation_running = True
        self.pulse_phase = 0

        # Center window
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 1200) // 2
        y = (screen_height - 900) // 2
        self.window.geometry(f"+{x}+{y}")

        # Cleanup on close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._create_loading_ui()
        self._fetch_packages()

    def _on_close(self):
        self.animation_running = False
        self.window.destroy()

    def _create_loading_ui(self):
        """Show loading screen while fetching packages"""
        self.loading_frame = tk.Frame(self.window.content_frame, bg="#0d0d1a")
        self.loading_frame.pack(fill="both", expand=True)

        tk.Label(
            self.loading_frame,
            text=t("loading_packages"),
            font=("Segoe UI", 18),
            bg="#0d0d1a",
            fg="white",
        ).pack(expand=True)

    def _fetch_packages(self):
        """Fetch package definitions from server"""

        def fetch():
            try:
                url = f"{get_license_server_url()}/features/config"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    self.packages_data = data.get("packages", {})
                    self.window.after(0, self._on_packages_loaded)
                else:
                    raise Exception(f"Server returned {response.status_code}")

            except Exception as e:
                print(f"[Upgrade] Error fetching packages: {e}")
                self.window.after(0, self._on_fetch_error)

        threading.Thread(target=fetch, daemon=True).start()

    def _on_fetch_error(self):
        """Handle fetch error - use local fallback"""
        from core.config import PACKAGE_DETAILS, PACKAGE_PRICES, PACKAGE_FEATURES

        for pkg_id in [Packages.BASIC, Packages.PLUS, Packages.PRO, Packages.PREMIUM]:
            details = PACKAGE_DETAILS.get(pkg_id, {})
            self.packages_data[pkg_id] = {
                "name": details.get("name", pkg_id),
                "description": details.get("description", ""),
                "price": details.get("price", PACKAGE_PRICES.get(pkg_id, 0)),
                "duration_days": 30,
                "features": details.get("features", []),
                "color": details.get("color", "#3498db"),
                "recommended": details.get("recommended", False),
            }

        self._on_packages_loaded()

    def _on_packages_loaded(self):
        """Called when packages are loaded - build UI"""
        self.loading = False
        self.loading_frame.destroy()
        self._create_widgets()

    def _create_widgets(self):
        # Main scrollable canvas (scrollbar hidden)
        main_canvas = tk.Canvas(
            self.window.content_frame, bg="#0d0d1a", highlightthickness=0
        )
        main_canvas.pack(fill="both", expand=True)

        # Hidden scrollbar - still functional for mouse wheel
        scrollbar = ttk.Scrollbar(
            self.window.content_frame, orient="vertical", command=main_canvas.yview
        )
        # scrollbar.pack(side="right", fill="y")  # Hidden

        main_canvas.configure(yscrollcommand=scrollbar.set)

        # Content frame inside canvas
        content = tk.Frame(main_canvas, bg="#0d0d1a")
        canvas_window = main_canvas.create_window((0, 0), window=content, anchor="nw")

        # Configure scroll region
        def configure_scroll(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
            # Make content width match canvas
            main_canvas.itemconfig(canvas_window, width=event.width)

        main_canvas.bind("<Configure>", configure_scroll)

        # Mouse wheel scrolling
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        main_canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Store canvas for animation
        self.main_canvas = main_canvas

        # Draw animated background orbs
        self._create_background_orbs(main_canvas)

        # Header
        header_frame = tk.Frame(content, bg="#0d0d1a")
        header_frame.pack(fill="x", pady=(25, 10))

        tk.Label(
            header_frame,
            text=t("choose_package"),
            font=("Segoe UI", 28, "bold"),
            bg="#0d0d1a",
            fg="white",
        ).pack()

        tk.Label(
            header_frame,
            text=t("unlock_potential"),
            font=("Segoe UI", 12),
            bg="#0d0d1a",
            fg="#8a8aa3",
        ).pack(pady=5)

        # Cards Container
        cards_container = tk.Frame(content, bg="#0d0d1a")
        cards_container.pack(fill="x", padx=25, pady=10)

        # Filter out 'free' package and sort by order
        display_packages = [
            (pkg_id, pkg_data)
            for pkg_id, pkg_data in self.packages_data.items()
            if pkg_id not in ["free", "trial"]
        ]
        display_packages.sort(key=lambda x: x[1].get("order", 99))

        # Grid configuration
        for i in range(len(display_packages)):
            cards_container.grid_columnconfigure(i, weight=1, uniform="cards")

        # Create cards
        for col_index, (pkg_id, pkg_data) in enumerate(display_packages):
            self._create_card(cards_container, pkg_id, pkg_data, col_index)

        # Divider with "or" text
        divider_frame = tk.Frame(content, bg="#0d0d1a")
        divider_frame.pack(fill="x", padx=120, pady=(10, 10))

        tk.Frame(divider_frame, height=1, bg="#2a2a4e").pack(
            side="left", fill="x", expand=True, pady=5
        )
        tk.Label(
            divider_frame,
            text=f"  {t('or')}  ",
            bg="#0d0d1a",
            fg="#6a6a8e",
            font=("Segoe UI", 11),
        ).pack(side="left")
        tk.Frame(divider_frame, height=1, bg="#2a2a4e").pack(
            side="left", fill="x", expand=True, pady=5
        )

        # License Key Input Section
        self._create_license_section(content)

        # Bottom padding
        tk.Frame(content, bg="#0d0d1a", height=15).pack()

    def _create_background_orbs(self, canvas):
        """Create animated floating orbs in background"""
        self.orbs = []

        orb_configs = [
            {"x": 100, "y": 200, "r": 100, "color": "#1a3a6e"},
            {"x": 1100, "y": 150, "r": 120, "color": "#3d1a5e"},
            {"x": 600, "y": 700, "r": 150, "color": "#1a4a3e"},
            {"x": 200, "y": 600, "r": 80, "color": "#5a3a1a"},
            {"x": 1000, "y": 500, "r": 90, "color": "#2a1a5e"},
        ]

        for i, cfg in enumerate(orb_configs):
            # Create gradient-like orb with multiple circles
            for j in range(3):
                scale = 1 - j * 0.3
                alpha_hex = ["40", "25", "15"][j]
                orb_id = canvas.create_oval(
                    cfg["x"] - cfg["r"] * scale,
                    cfg["y"] - cfg["r"] * scale,
                    cfg["x"] + cfg["r"] * scale,
                    cfg["y"] + cfg["r"] * scale,
                    fill=cfg["color"],
                    outline="",
                    stipple="gray50" if j == 0 else "gray25",
                )
                canvas.tag_lower(orb_id)

            self.orbs.append(
                {
                    "base_x": cfg["x"],
                    "base_y": cfg["y"],
                    "r": cfg["r"],
                    "phase": i * 0.7,
                }
            )

        # Start animation
        self._animate_orbs()

    def _animate_orbs(self):
        """Animate background orbs"""
        if not self.animation_running or not hasattr(self, "main_canvas"):
            return

        self.pulse_phase += 0.03

        # Subtle pulsing effect on the background
        try:
            # Just update pulse phase for smooth animation feel
            self.window.after(50, self._animate_orbs)
        except:
            pass

    def _create_license_section(self, parent):
        """Create refined license key input section"""
        license_outer = tk.Frame(parent, bg="#0d0d1a")
        license_outer.pack(pady=(10, 20), fill="x")

        # Main container
        container = tk.Frame(license_outer, bg="#0d0d1a")
        container.pack(expand=True, fill="x")

        # Card with modern styling
        license_card = tk.Frame(
            container,
            bg="#1a1a2e",
            highlightbackground="#2a2a4e",
            highlightthickness=1,
        )
        license_card.pack(padx=60, ipadx=20, ipady=15)

        # Content Container
        content_frame = tk.Frame(license_card, bg="#1a1a2e")
        content_frame.pack(padx=20)

        # Instruction text only (Title removed)
        tk.Label(
            content_frame,
            text="Nhập license key để kích hoạt gói của bạn",
            font=("Segoe UI", 10),
            bg="#1a1a2e",
            fg="#7a7a9e",
            anchor="w",
            justify="left",
        ).pack(anchor="w", fill="x", pady=(0, 8))

        # Input row
        input_row = tk.Frame(content_frame, bg="#1a1a2e")
        input_row.pack(fill="x")

        # Entry with modern border - fixed height to match button
        entry_height = 34

        entry_wrapper = tk.Frame(
            input_row,
            bg="#2a2a4e",
            highlightbackground="#3a3a5e",
            highlightthickness=1,
            height=entry_height,
            width=280,  # Fixed width
        )
        entry_wrapper.pack(side="left", padx=(0, 15))
        entry_wrapper.pack_propagate(False)

        self.license_entry = tk.Entry(
            entry_wrapper,
            font=("Consolas", 11),
            bg="#2a2a4e",
            fg="#e0e0e0",
            insertbackground="#8a8ae0",
            bd=0,
            relief="flat",
        )
        self.license_entry.pack(fill="both", expand=True, padx=10, pady=7)
        self.license_entry.bind("<Return>", lambda e: self._activate_license())

        # Focus effects
        def on_focus_in(e):
            entry_wrapper.configure(highlightbackground="#4a9eff", bg="#2a2a5e")

        def on_focus_out(e):
            entry_wrapper.configure(highlightbackground="#3a3a5e", bg="#2a2a4e")

        self.license_entry.bind("<FocusIn>", on_focus_in)
        self.license_entry.bind("<FocusOut>", on_focus_out)

        # Activate button
        RoundedButton(
            input_row,
            text=t("activate"),
            command=self._activate_license,
            kind="accent",
            width=90,
            height=entry_height,
            radius=4,
            canvas_bg="#1a1a2e",
        ).pack(side="left")

    def _activate_license(self):
        """Activate entered license key"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showwarning(t("missing_license"), t("enter_license"))
            return

        fm = get_feature_manager()
        self.license_entry.config(state="disabled")

        def activate():
            success = fm.activate_license(license_key)

            def on_result():
                self.license_entry.config(state="normal")

                if success:
                    messagebox.showinfo(
                        t("success"),
                        t("license_activated", package=fm.current_package.upper()),
                    )
                    self._on_close()
                else:
                    messagebox.showerror(t("error"), t("license_invalid"))

            self.window.after(0, on_result)

        threading.Thread(target=activate, daemon=True).start()

    def _create_card(self, parent, package_id, pkg_data, col_index):
        """Create a modern package card with hover effects"""
        is_recommended = pkg_data.get("recommended", False)
        accent_color = pkg_data.get("color", COLOR_PRIMARY)

        # Outer frame for hover effect
        outer = tk.Frame(parent, bg="#0d0d1a")
        outer.grid(row=0, column=col_index, padx=12, pady=10, sticky="nsew")

        # Card with rounded appearance using border
        card = tk.Frame(
            outer,
            bg="#1a1a2e",
            highlightbackground=accent_color if is_recommended else "#2a2a4e",
            highlightthickness=2 if is_recommended else 1,
        )
        card.pack(fill="both", expand=True, ipadx=15, ipady=15)

        # Hover effects
        def on_enter(e):
            card.configure(highlightbackground=accent_color, highlightthickness=2)

        def on_leave(e):
            if is_recommended:
                card.configure(highlightbackground=accent_color, highlightthickness=2)
            else:
                card.configure(highlightbackground="#2a2a4e", highlightthickness=1)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        # Bind to all children
        def bind_children(widget):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            for child in widget.winfo_children():
                bind_children(child)

        # Fixed height badge container - ensures consistent card layout
        badge_container = tk.Frame(card, bg="#1a1a2e", height=40)
        badge_container.pack(fill="x", pady=(5, 0))
        badge_container.pack_propagate(False)  # Prevent resizing

        if is_recommended:
            badge_inner = tk.Frame(badge_container, bg="#1a1a2e")
            badge_inner.pack(expand=True)
            badge_label = tk.Label(
                badge_inner,
                text="⭐ RECOMMENDED",
                bg=accent_color,
                fg="black",
                font=("Segoe UI", 9, "bold"),
                padx=14,
                pady=5,
            )
            badge_label.pack()

        # Package Name
        tk.Label(
            card,
            text=pkg_data.get("name", package_id),
            font=("Segoe UI", 20, "bold"),
            bg="#1a1a2e",
            fg=accent_color,
        ).pack(pady=(10, 5))

        # Price with large font
        price = pkg_data.get("price", 0)
        price_str = f"{price:,} VND"
        tk.Label(
            card,
            text=price_str,
            font=("Segoe UI", 26, "bold"),
            bg="#1a1a2e",
            fg="white",
        ).pack()

        # Duration
        duration_days = pkg_data.get("duration_days", 30)
        if duration_days == 30:
            duration_text = "1 tháng"
        elif duration_days == 365:
            duration_text = "1 năm"
        elif duration_days == 7:
            duration_text = "1 tuần"
        else:
            duration_text = f"{duration_days} ngày"

        tk.Label(
            card, text=duration_text, font=("Segoe UI", 11), bg="#1a1a2e", fg="#8a8aa3"
        ).pack(pady=(0, 15))

        # Divider
        tk.Frame(card, height=1, bg="#2a2a4e").pack(fill="x", padx=20, pady=10)

        # Features
        features_frame = tk.Frame(card, bg="#1a1a2e")
        features_frame.pack(fill="both", expand=True, padx=15, pady=5)

        features = pkg_data.get("features", [])
        feature_display = pkg_data.get("feature_display", features)

        for feature in feature_display[:7]:  # Limit to 7 features
            f_row = tk.Frame(features_frame, bg="#1a1a2e")
            f_row.pack(fill="x", pady=4)

            tk.Label(
                f_row,
                text="✓",
                font=("Segoe UI", 11, "bold"),
                bg="#1a1a2e",
                fg="#4ade80",
            ).pack(side="left")

            tk.Label(
                f_row,
                text=feature,
                font=("Segoe UI", 10),
                bg="#1a1a2e",
                fg="white",
                wraplength=180,
                justify="left",
                anchor="w",
            ).pack(side="left", padx=10, fill="x")

        # Select Button
        btn_kind = "success" if is_recommended else "secondary"

        btn_frame = tk.Frame(card, bg="#1a1a2e")
        btn_frame.pack(side="bottom", pady=20)

        ModernButton(
            btn_frame,
            text="Chọn gói này",
            command=lambda pid=package_id, pdata=pkg_data: self._select_package(
                pid, pdata
            ),
            kind=btn_kind,
            width=18,
        ).pack()

        # Apply hover bindings to all children
        self.window.after(100, lambda: bind_children(card))

    def _select_package(self, package_id, pkg_data):
        """Select a package and open payment window"""
        self._on_close()

        fm = get_feature_manager()
        PaymentWindow(
            self.parent,
            fm,
            {
                "id": package_id,
                "name": pkg_data.get("name", package_id),
                "price": pkg_data.get("price", 0),
            },
            on_success=lambda: messagebox.showinfo(
                "Thành công", "Cảm ơn bạn đã nâng cấp! Vui lòng khởi động lại ứng dụng."
            ),
        )
