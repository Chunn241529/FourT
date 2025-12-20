"""
Upgrade Window - Fetch packages from server and display
All package definitions come from server API, client only displays
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests

from core.config import Packages, COLOR_BG, COLOR_TEXT, COLOR_PRIMARY, get_license_server_url
from .theme import ModernButton, colors, FONTS
from .payment_window import PaymentWindow
from feature_manager import get_feature_manager


class UpgradeWindow:
    """Professional Upgrade Window - Fetches packages from server"""
    
    def __init__(self, parent):
        self.parent = parent
        from .components import FramelessWindow
        self.window = FramelessWindow(parent, title="Nâng cấp FourT Suite")
        self.window.geometry("1200x780")
        # bg handled by FramelessWindow
        
        # Package data will be fetched from server
        self.packages_data = {}
        self.loading = True
        
        # Center window
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 1200) // 2
        y = (screen_height - 780) // 2
        self.window.geometry(f"+{x}+{y}")
        
        self._create_loading_ui()
        self._fetch_packages()
        
    def _create_loading_ui(self):
        """Show loading screen while fetching packages"""
        self.loading_frame = tk.Frame(self.window.content_frame, bg=COLOR_BG)
        self.loading_frame.pack(fill='both', expand=True)
        
        tk.Label(
            self.loading_frame,
            text="⏳ Đang tải thông tin gói...",
            font=("Segoe UI", 16),
            bg=COLOR_BG, fg="white"
        ).pack(expand=True)
        
    def _fetch_packages(self):
        """Fetch package definitions from server"""
        def fetch():
            try:
                url = f"{get_license_server_url()}/features/config"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self.packages_data = data.get('packages', {})
                    self.window.after(0, self._on_packages_loaded)
                else:
                    raise Exception(f"Server returned {response.status_code}")
                    
            except Exception as e:
                print(f"[Upgrade] Error fetching packages: {e}")
                # Fallback to local config
                self.window.after(0, self._on_fetch_error)
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def _on_fetch_error(self):
        """Handle fetch error - use local fallback"""
        from core.config import PACKAGE_DETAILS, PACKAGE_PRICES, PACKAGE_FEATURES
        
        # Build fallback from local config
        for pkg_id in [Packages.BASIC, Packages.PLUS, Packages.PRO, Packages.PREMIUM]:
            details = PACKAGE_DETAILS.get(pkg_id, {})
            self.packages_data[pkg_id] = {
                "name": details.get("name", pkg_id),
                "description": details.get("description", ""),
                "price": details.get("price", PACKAGE_PRICES.get(pkg_id, 0)),
                "duration_days": 30,
                "features": details.get("features", []),
                "color": details.get("color", "#3498db"),
                "recommended": details.get("recommended", False)
            }
        
        self._on_packages_loaded()
        
    def _on_packages_loaded(self):
        """Called when packages are loaded - build UI"""
        self.loading = False
        self.loading_frame.destroy()
        self._create_widgets()
        
    def _create_widgets(self):
        # Header
        header_frame = tk.Frame(self.window.content_frame, bg=COLOR_BG)
        header_frame.pack(fill='x', pady=(20, 10))
        
        tk.Label(
            header_frame, 
            text="Chọn gói phù hợp với bạn", 
            font=("Segoe UI", 22, "bold"),
            bg=COLOR_BG, fg="white"
        ).pack()
        
        tk.Label(
            header_frame, 
            text="Mở khóa toàn bộ tiềm năng của FourT Suite", 
            font=("Segoe UI", 11),
            bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(pady=3)
        
        # Cards Container
        cards_container = tk.Frame(self.window.content_frame, bg=COLOR_BG)
        cards_container.pack(fill='both', padx=20, pady=10)
        
        # Filter out 'free' package and sort by order
        display_packages = [
            (pkg_id, pkg_data) 
            for pkg_id, pkg_data in self.packages_data.items() 
            if pkg_id not in ['free', 'trial']  # Don't show free/trial in upgrade window
        ]
        display_packages.sort(key=lambda x: x[1].get('order', 99))
        
        # Grid configuration for centering
        for i in range(len(display_packages)):
            cards_container.grid_columnconfigure(i, weight=1, uniform="equal")
        
        # Create cards
        for col_index, (pkg_id, pkg_data) in enumerate(display_packages):
            self._create_card(cards_container, pkg_id, pkg_data, col_index)
        
        # Divider with "or" text
        divider_frame = tk.Frame(self.window.content_frame, bg=COLOR_BG)
        divider_frame.pack(fill='x', padx=100, pady=(0, 15))
        
        tk.Frame(divider_frame, height=1, bg="#3a3a5e").pack(side='left', fill='x', expand=True, pady=8)
        tk.Label(divider_frame, text="  hoặc  ", bg=COLOR_BG, fg="#6a6a8e", 
                font=("Segoe UI", 10)).pack(side='left')
        tk.Frame(divider_frame, height=1, bg="#3a3a5e").pack(side='left', fill='x', expand=True, pady=8)
        
        # License Key Input Section
        license_outer = tk.Frame(self.window.content_frame, bg=COLOR_BG)
        license_outer.pack(pady=(0, 25))
        
        license_frame = tk.Frame(license_outer, bg="#1e1e2e", 
                                 highlightbackground="#4a9eff", highlightthickness=1)
        license_frame.pack(padx=20, pady=5)
        
        inner = tk.Frame(license_frame, bg="#1e1e2e")
        inner.pack(padx=25, pady=18)
        
        # Icon + Title Row
        title_row = tk.Frame(inner, bg="#1e1e2e")
        title_row.pack(fill='x')  # fill='x' để frame chiếm hết chiều ngang
        
        tk.Label(title_row, text="Đã có License Key?", font=("Segoe UI", 13, "bold"),
                bg="#1e1e2e", fg="white").pack(anchor='w')  # anchor='w' căn trái trong frame
        
        # Input Row
        input_row = tk.Frame(inner, bg="#1e1e2e")
        input_row.pack(pady=(12, 0))
        
        self.license_entry = tk.Entry(
            input_row,
            font=("Segoe UI", 12),
            bg="#2a2a4e", fg="white",
            insertbackground="white",
            bd=2, relief='solid',
            highlightbackground="#4a4a6e",
            highlightcolor="#4a9eff",
            highlightthickness=1,
            width=32,
            state='normal'
        )
        self.license_entry.pack(side='left', padx=(0, 12), ipady=6, ipadx=8)
        self.license_entry.bind('<Return>', lambda e: self._activate_license())
        
        ModernButton(input_row, text="Kích hoạt", command=self._activate_license,
                    kind='accent', width=12).pack(side='left')
    
    def _activate_license(self):
        """Activate entered license key"""
        license_key = self.license_entry.get().strip()
        
        if not license_key:
            messagebox.showwarning("Thiếu License Key", "Vui lòng nhập license key.")
            return
        
        fm = get_feature_manager()
        
        # Show loading
        self.license_entry.config(state='disabled')
        
        def activate():
            success = fm.activate_license(license_key)
            
            def on_result():
                self.license_entry.config(state='normal')
                
                if success:
                    messagebox.showinfo(
                        "Thành công", 
                        f"License đã được kích hoạt!\nGói: {fm.current_package.upper()}"
                    )
                    self.window.destroy()
                else:
                    messagebox.showerror(
                        "Lỗi", 
                        "License key không hợp lệ hoặc đã được sử dụng trên thiết bị khác."
                    )
            
            self.window.after(0, on_result)
        
        threading.Thread(target=activate, daemon=True).start()
        
    def _create_card(self, parent, package_id, pkg_data, col_index):
        """Create a package card from server data"""
        is_recommended = pkg_data.get("recommended", False)
        accent_color = pkg_data.get("color", COLOR_PRIMARY)
        
        # Card Frame
        card = tk.Frame(
            parent, 
            bg="#1e1e2e", 
            highlightbackground=accent_color if is_recommended else "#2a2a3e",
            highlightthickness=2 if is_recommended else 1,
            padx=20, pady=20
        )
        card.grid(row=0, column=col_index, padx=15, sticky="nsew")
        
        # Recommended Badge
        if is_recommended:
            tk.Label(
                card, text="RECOMMENDED", 
                bg=accent_color, fg="black",
                font=("Segoe UI", 8, "bold"),
                padx=8, pady=2
            ).pack(anchor="ne")
        else:
            tk.Label(card, text="", bg="#1e1e2e", font=("Segoe UI", 8)).pack(pady=2)

        # Package Name
        tk.Label(
            card, text=pkg_data.get("name", package_id), 
            font=("Segoe UI", 16, "bold"),
            bg="#1e1e2e", fg=accent_color
        ).pack(pady=(10, 5))
        
        # Price
        price = pkg_data.get("price", 0)
        price_str = f"{price:,} VND"
        tk.Label(
            card, text=price_str, 
            font=("Segoe UI", 20, "bold"),
            bg="#1e1e2e", fg="white"
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
            card, text=duration_text, 
            font=("Segoe UI", 10),
            bg="#1e1e2e", fg=COLOR_TEXT
        ).pack(pady=(0, 15))
        
        # Divider
        tk.Frame(card, height=1, bg="#2a2a3e").pack(fill="x", pady=10)
        
        # Features
        features_frame = tk.Frame(card, bg="#1e1e2e")
        features_frame.pack(fill="both", expand=True)
        
        # Features can be a list of strings or feature IDs
        features = pkg_data.get("features", [])
        feature_display = pkg_data.get("feature_display", features)  # Use display list if available
        
        for feature in feature_display[:8]:  # Limit to 8 features
            f_row = tk.Frame(features_frame, bg="#1e1e2e")
            f_row.pack(fill="x", pady=5)
            
            tk.Label(
                f_row, text="✓", 
                font=("Segoe UI", 10, "bold"),
                bg="#1e1e2e", fg=COLOR_PRIMARY
            ).pack(side="left")
            
            tk.Label(
                f_row, text=feature, 
                font=("Segoe UI", 10),
                bg="#1e1e2e", fg="white",
                wraplength=200, justify="left"
            ).pack(side="left", padx=10)
            
        # Select Button
        btn_kind = "success" if is_recommended else "secondary"
        
        ModernButton(
            card, 
            text="Chọn gói này", 
            command=lambda pid=package_id, pdata=pkg_data: self._select_package(pid, pdata),
            kind=btn_kind,
            width=15
        ).pack(side="bottom", pady=20)
        
    def _select_package(self, package_id, pkg_data):
        """Select a package and open payment window"""
        # Close upgrade window
        self.window.destroy()
        
        # Open payment window with server data
        fm = get_feature_manager()
        PaymentWindow(
            self.parent,
            fm,
            {
                "id": package_id, 
                "name": pkg_data.get("name", package_id), 
                "price": pkg_data.get("price", 0)
            },
            on_success=lambda: messagebox.showinfo("Thành công", "Cảm ơn bạn đã nâng cấp! Vui lòng khởi động lại ứng dụng.")
        )
