"""
Package Management Tab for Admin UI
"""

import re
import tkinter as tk
from tkinter import ttk, messagebox

from backend.admin.tabs.base_tab import BaseTab


class PackagesTab(BaseTab):
    """Package Management tab - CRUD for packages"""

    def setup(self):
        """Setup Package Management tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        # Available features (checkbox list)
        self.all_features = [
            ("midi_playback", "MIDI Playback"),
            ("loop_mode", "Loop Mode"),
            ("script_preview", "Script Preview"),
            ("mp3_conversion", "MP3 Conversion"),
            ("macro", "Macro"),
            ("macro_unlimited", "Macro Unlimited"),
            ("wwm_combo", "WWM Combo"),
            ("quest_video_helper", "Quest Video Helper"),
            ("ping_optimizer", "Ping Optimizer"),
            ("screen_translator", "Screen Translator"),
        ]

        # Package data
        self.packages_data = {}
        self.pkg_drag_data = {"index": None}

        # Main container - split left (list) and right (edit form)
        main_container = tk.PanedWindow(
            self.parent,
            orient=tk.HORIZONTAL,
            bg=COLORS["bg"],
            sashwidth=6,
            sashrelief=tk.RAISED,
        )
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === Left Panel - Package List ===
        left_panel = tk.Frame(main_container, bg=COLORS["card"])
        main_container.add(left_panel, minsize=250, width=300)

        # Header
        header = tk.Frame(left_panel, bg=COLORS["card"])
        header.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            header,
            text="📦 Danh sách gói",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        ModernButton(
            header, text="🔄", command=self._load_packages, kind="secondary", width=3
        ).pack(side=tk.RIGHT)

        # Package listbox
        list_frame = tk.Frame(left_panel, bg=COLORS["card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        vsb = ttk.Scrollbar(list_frame, orient="vertical")
        self.packages_listbox = tk.Listbox(
            list_frame,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            selectbackground=COLORS["accent"],
            selectforeground="white",
            yscrollcommand=vsb.set,
        )
        vsb.config(command=self.packages_listbox.yview)

        self.packages_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.packages_listbox.bind("<<ListboxSelect>>", self._on_package_select)

        # Buttons with move up/down
        btn_frame = tk.Frame(left_panel, bg=COLORS["card"])
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ModernButton(
            btn_frame,
            text="⬆",
            command=self._move_package_up,
            kind="secondary",
            width=3,
        ).pack(side=tk.LEFT, padx=(0, 2))
        ModernButton(
            btn_frame,
            text="⬇",
            command=self._move_package_down,
            kind="secondary",
            width=3,
        ).pack(side=tk.LEFT, padx=(0, 10))
        ModernButton(
            btn_frame, text="➕", command=self._add_package, kind="success", width=3
        ).pack(side=tk.LEFT, padx=(0, 2))
        ModernButton(
            btn_frame, text="❌", command=self._delete_package, kind="danger", width=3
        ).pack(side=tk.LEFT)

        # === Right Panel - Edit Form with Hidden Scroll ===
        right_panel = tk.Frame(main_container, bg=COLORS["card"])
        main_container.add(right_panel, minsize=400)

        tk.Label(
            right_panel,
            text="✏️ Chỉnh sửa gói",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 10))

        # Scrollable container (hidden scrollbar)
        scroll_container = tk.Frame(right_panel, bg=COLORS["card"])
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.pkg_form_canvas = tk.Canvas(
            scroll_container, bg=COLORS["card"], highlightthickness=0, bd=0
        )
        self.pkg_form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.pkg_form_inner = tk.Frame(self.pkg_form_canvas, bg=COLORS["card"])
        self.pkg_form_window = self.pkg_form_canvas.create_window(
            (0, 0), window=self.pkg_form_inner, anchor="nw"
        )

        # Mouse wheel scroll
        def _on_pkg_scroll(event):
            if (
                self.pkg_form_inner.winfo_reqheight()
                > self.pkg_form_canvas.winfo_height()
            ):
                self.pkg_form_canvas.yview_scroll(-1 * (event.delta // 120), "units")

        self.pkg_form_canvas.bind("<MouseWheel>", _on_pkg_scroll)
        self.pkg_form_inner.bind("<MouseWheel>", _on_pkg_scroll)

        def _on_inner_configure(event):
            self.pkg_form_canvas.configure(
                scrollregion=self.pkg_form_canvas.bbox("all")
            )
            # Bind scroll to all children
            for child in self.pkg_form_inner.winfo_children():
                child.bind("<MouseWheel>", _on_pkg_scroll, add="+")

        def _on_canvas_configure(event):
            self.pkg_form_canvas.itemconfig(self.pkg_form_window, width=event.width)

        self.pkg_form_inner.bind("<Configure>", _on_inner_configure)
        self.pkg_form_canvas.bind("<Configure>", _on_canvas_configure)

        form_frame = tk.Frame(self.pkg_form_inner, bg=COLORS["card"])
        form_frame.pack(fill=tk.X, padx=15, pady=5)

        # Package ID
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="ID:",
            width=12,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_id_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.pkg_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Name
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Tên:",
            width=12,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_name_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.pkg_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Price
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Giá (VND):",
            width=12,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_price_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=15,
        )
        self.pkg_price_entry.pack(side=tk.LEFT)

        # Duration (smart input)
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Thời hạn:",
            width=12,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_duration_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=10,
        )
        self.pkg_duration_entry.pack(side=tk.LEFT)
        tk.Label(
            row,
            text="(VD: 30, 1d, 7d, 1m, 1y, 30min)",
            font=FONTS.get("small", ("Segoe UI", 9)),
            bg=COLORS["card"],
            fg=COLORS.get("fg_dim", COLORS["fg"]),
        ).pack(side=tk.LEFT, padx=10)

        # Description
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Mô tả:",
            width=12,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_desc_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.pkg_desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Color
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Màu:",
            width=12,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_color_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=10,
        )
        self.pkg_color_entry.pack(side=tk.LEFT)
        self.pkg_color_preview = tk.Label(
            row, text="  ██  ", bg=COLORS["accent"], width=5
        )
        self.pkg_color_preview.pack(side=tk.LEFT, padx=10)

        # Recommended checkbox
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        self.pkg_recommended_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            row,
            text="Gói khuyến nghị (Recommended)",
            variable=self.pkg_recommended_var,
            bg=COLORS["card"],
            fg=COLORS["fg"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["fg"],
            font=FONTS["body"],
        ).pack(side=tk.LEFT)

        # Features section (checkboxes for feature IDs)
        features_frame = tk.LabelFrame(
            form_frame,
            text="Tính năng (Feature IDs)",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
            padx=10,
            pady=10,
        )
        features_frame.pack(fill=tk.X, pady=10)

        self.feature_vars = {}
        # Two columns for checkboxes
        features_inner = tk.Frame(features_frame, bg=COLORS["card"])
        features_inner.pack(fill=tk.X)

        for i, (feature_id, feature_name) in enumerate(self.all_features):
            var = tk.BooleanVar(value=False)
            self.feature_vars[feature_id] = var
            col = i % 2
            row_idx = i // 2
            cb = tk.Checkbutton(
                features_inner,
                text=feature_name,
                variable=var,
                bg=COLORS["card"],
                fg=COLORS["fg"],
                selectcolor=COLORS["input_bg"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["fg"],
                font=FONTS["body"],
            )
            cb.grid(row=row_idx, column=col, sticky="w", padx=5, pady=2)

        # Feature Display (custom descriptions for UI)
        display_frame = tk.LabelFrame(
            form_frame,
            text="Mô tả hiển thị (1 dòng = 1 tính năng)",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
            padx=10,
            pady=10,
        )
        display_frame.pack(fill=tk.X, pady=10)

        tk.Label(
            display_frame,
            text="Nhập mô tả cho client (mỗi dòng 1 tính năng):",
            font=FONTS.get("small", ("Segoe UI", 9)),
            bg=COLORS["card"],
            fg=COLORS.get("fg_dim", COLORS["fg"]),
        ).pack(anchor="w")

        self.pkg_feature_display = tk.Text(
            display_frame,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            height=5,
            width=40,
        )
        self.pkg_feature_display.pack(fill=tk.X, pady=5)

        # Limits section
        limits_frame = tk.LabelFrame(
            form_frame,
            text="Giới hạn",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
            padx=10,
            pady=10,
        )
        limits_frame.pack(fill=tk.X, pady=5)

        row = tk.Frame(limits_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=3)
        tk.Label(
            row,
            text="Macro save limit:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.pkg_macro_limit_entry = tk.Entry(
            row, font=FONTS["body"], bg=COLORS["input_bg"], fg=COLORS["fg"], width=8
        )
        self.pkg_macro_limit_entry.pack(side=tk.LEFT, padx=5)

        self.pkg_infinite_loop_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            row,
            text="Infinite Loop",
            variable=self.pkg_infinite_loop_var,
            bg=COLORS["card"],
            fg=COLORS["fg"],
            selectcolor=COLORS["input_bg"],
            font=FONTS["body"],
        ).pack(side=tk.LEFT, padx=15)

        # Save button
        save_frame = tk.Frame(right_panel, bg=COLORS["card"])
        save_frame.pack(fill=tk.X, padx=15, pady=15)

        ModernButton(
            save_frame,
            text="💾 Lưu gói",
            command=self._save_package,
            kind="primary",
            width=15,
        ).pack(side=tk.LEFT)

        # Load initial data
        self._load_packages()

    def _parse_duration(self, text: str) -> int:
        """Smart parse duration text to days."""
        text = text.strip().lower()

        # Pure number = days
        if text.isdigit():
            return int(text)

        # Try to extract number and unit
        match = re.match(r"^(\d+)\s*([a-z]+)?$", text)
        if not match:
            return 30  # Default to 30 days

        num = int(match.group(1))
        unit = match.group(2) or "d"

        # Map units to days
        unit_map = {
            "s": 1 / 86400,
            "sec": 1 / 86400,
            "second": 1 / 86400,
            "seconds": 1 / 86400,
            "min": 1 / 1440,
            "minute": 1 / 1440,
            "minutes": 1 / 1440,
            "h": 1 / 24,
            "hr": 1 / 24,
            "hour": 1 / 24,
            "hours": 1 / 24,
            "d": 1,
            "day": 1,
            "days": 1,
            "w": 7,
            "week": 7,
            "weeks": 7,
            "m": 30,
            "mo": 30,
            "month": 30,
            "months": 30,
            "y": 365,
            "yr": 365,
            "year": 365,
            "years": 365,
        }

        multiplier = unit_map.get(unit, 1)
        days = int(num * multiplier)
        return max(0, days)

    def _format_duration_display(self, days: int) -> str:
        """Format days back to readable string for display"""
        if days == 0:
            return "0"
        elif days == 1:
            return "1d"
        elif days == 7:
            return "1w"
        elif days == 30:
            return "1m"
        elif days == 365:
            return "1y"
        elif days % 365 == 0:
            return f"{days // 365}y"
        elif days % 30 == 0:
            return f"{days // 30}m"
        elif days % 7 == 0:
            return f"{days // 7}w"
        else:
            return f"{days}d"

    def _load_packages(self):
        """Load packages from server or local config"""
        self.packages_listbox.delete(0, tk.END)

        # Admin uses localhost directly (server runs locally)
        admin_api_url = "http://localhost:8000"

        # Try to load from server first
        try:
            import requests

            url = f"{admin_api_url}/features/admin/packages"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                self.packages_data = response.json().get("packages", {})
            else:
                raise Exception("Server error")
        except:
            # Fallback to local config
            from core.config import (
                PACKAGE_FEATURES,
                PACKAGE_PRICES,
                PACKAGE_DETAILS,
                Packages,
            )

            self.packages_data = {}
            for pkg_id in [
                Packages.FREE,
                Packages.BASIC,
                Packages.PLUS,
                Packages.PRO,
                Packages.PREMIUM,
            ]:
                details = PACKAGE_DETAILS.get(pkg_id, {})
                self.packages_data[pkg_id] = {
                    "name": details.get("name", pkg_id),
                    "description": details.get("description", ""),
                    "price": PACKAGE_PRICES.get(pkg_id, 0),
                    "features": [
                        f.split(".")[-1] if "." in str(f) else str(f)
                        for f in PACKAGE_FEATURES.get(pkg_id, [])
                    ],
                    "color": details.get("color", "#95a5a6"),
                    "recommended": details.get("recommended", False),
                }

        # Populate listbox
        for pkg_id in sorted(
            self.packages_data.keys(),
            key=lambda x: self.packages_data[x].get("order", 99),
        ):
            pkg = self.packages_data[pkg_id]
            display = f"{pkg.get('name', pkg_id)} - {pkg.get('price', 0):,}₫"
            self.packages_listbox.insert(tk.END, f"{pkg_id}: {display}")

    def _on_package_select(self, event):
        """Handle package selection"""
        selection = self.packages_listbox.curselection()
        if not selection:
            return

        item = self.packages_listbox.get(selection[0])
        pkg_id = item.split(":")[0]

        if pkg_id not in self.packages_data:
            return

        pkg = self.packages_data[pkg_id]

        # Populate form
        self.pkg_id_entry.delete(0, tk.END)
        self.pkg_id_entry.insert(0, pkg_id)

        self.pkg_name_entry.delete(0, tk.END)
        self.pkg_name_entry.insert(0, pkg.get("name", ""))

        self.pkg_price_entry.delete(0, tk.END)
        self.pkg_price_entry.insert(0, str(pkg.get("price", 0)))

        self.pkg_duration_entry.delete(0, tk.END)
        # Check for minutes-based duration (Trial) or days-based
        if pkg.get("duration_minutes"):
            self.pkg_duration_entry.insert(0, f"{pkg.get('duration_minutes')}min")
        else:
            self.pkg_duration_entry.insert(
                0, self._format_duration_display(pkg.get("duration_days", 30))
            )

        self.pkg_desc_entry.delete(0, tk.END)
        self.pkg_desc_entry.insert(0, pkg.get("description", ""))

        self.pkg_color_entry.delete(0, tk.END)
        self.pkg_color_entry.insert(0, pkg.get("color", "#95a5a6"))
        try:
            self.pkg_color_preview.config(bg=pkg.get("color", "#95a5a6"))
        except:
            pass

        self.pkg_recommended_var.set(pkg.get("recommended", False))

        # Set feature checkboxes
        pkg_features = pkg.get("features", [])
        for feature_id, var in self.feature_vars.items():
            var.set(feature_id in pkg_features)

        # Set feature display text
        self.pkg_feature_display.delete("1.0", tk.END)
        feature_display = pkg.get("feature_display", [])
        if feature_display:
            self.pkg_feature_display.insert("1.0", "\n".join(feature_display))

        # Set limits
        limits = pkg.get("limits", {})
        self.pkg_macro_limit_entry.delete(0, tk.END)
        self.pkg_macro_limit_entry.insert(0, str(limits.get("macro_save_limit", 0)))
        self.pkg_infinite_loop_var.set(limits.get("macro_infinite_loop", False))

    def _add_package(self):
        """Add a new package"""
        # Clear form
        self.pkg_id_entry.delete(0, tk.END)
        self.pkg_name_entry.delete(0, tk.END)
        self.pkg_price_entry.delete(0, tk.END)
        self.pkg_duration_entry.delete(0, tk.END)
        self.pkg_duration_entry.insert(0, "30")
        self.pkg_desc_entry.delete(0, tk.END)
        self.pkg_color_entry.delete(0, tk.END)
        self.pkg_color_entry.insert(0, "#95a5a6")
        self.pkg_recommended_var.set(False)
        for var in self.feature_vars.values():
            var.set(False)
        self.pkg_feature_display.delete("1.0", tk.END)
        self.pkg_macro_limit_entry.delete(0, tk.END)
        self.pkg_infinite_loop_var.set(False)

        self.pkg_id_entry.focus()

    def _save_package(self):
        """Save package to server"""
        pkg_id = self.pkg_id_entry.get().strip().lower()
        if not pkg_id:
            messagebox.showerror("Lỗi", "Package ID không được để trống")
            return

        # Collect features
        features = [fid for fid, var in self.feature_vars.items() if var.get()]

        # Collect limits
        limits = {"midi_file_limit": 999}
        try:
            macro_limit = int(self.pkg_macro_limit_entry.get() or 0)
            if macro_limit > 0:
                limits["macro_save_limit"] = macro_limit
        except:
            pass
        limits["macro_infinite_loop"] = self.pkg_infinite_loop_var.get()

        # Collect feature display (parse lines)
        feature_display_text = self.pkg_feature_display.get("1.0", tk.END).strip()
        feature_display = [
            line.strip() for line in feature_display_text.split("\n") if line.strip()
        ]

        # Get order from existing package or calculate from listbox position
        if pkg_id in self.packages_data:
            order = self.packages_data[pkg_id].get("order", 99)
        else:
            # New package - add at end
            order = (
                max([p.get("order", 0) for p in self.packages_data.values()], default=0)
                + 1
            )

        # Parse duration - check if it's minutes or days
        duration_text = self.pkg_duration_entry.get().strip().lower()
        duration_days = self._parse_duration(duration_text)
        duration_minutes = None

        # Check if input was in minutes (ends with min)
        if "min" in duration_text:
            match = re.match(r"^(\d+)\s*min", duration_text)
            if match:
                duration_minutes = int(match.group(1))
                duration_days = 0  # Mark as minutes-based

        data = {
            "name": self.pkg_name_entry.get().strip(),
            "description": self.pkg_desc_entry.get().strip(),
            "price": int(self.pkg_price_entry.get() or 0),
            "duration_days": duration_days,
            "order": order,
            "features": features,
            "feature_display": feature_display,
            "limits": limits,
            "color": self.pkg_color_entry.get().strip() or "#95a5a6",
            "recommended": self.pkg_recommended_var.get(),
        }

        # Add duration_minutes if minutes-based
        if duration_minutes is not None:
            data["duration_minutes"] = duration_minutes

        # Try to save to server (admin uses localhost directly)
        admin_api_url = "http://localhost:8000"
        try:
            import requests

            url = f"{admin_api_url}/features/admin/packages/{pkg_id}"
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Thành công", f"Đã lưu gói {pkg_id}")
                self._load_packages()
            else:
                # Check if HTML response (server error page)
                if response.text.startswith("<!DOCTYPE") or response.text.startswith(
                    "<html"
                ):
                    raise Exception("Server offline hoặc endpoint không tồn tại")
                raise Exception(f"Server error: {response.status_code}")
        except Exception as e:
            if "requests" in str(type(e).__module__):
                messagebox.showwarning(
                    "Lưu Local",
                    f"Server không khả dụng.\nDữ liệu chỉ lưu local (cần restart server).",
                )
            else:
                messagebox.showwarning(
                    "Lưu Local", f"{e}\n\nDữ liệu chỉ lưu local (cần restart server)."
                )
            # Update local data
            self.packages_data[pkg_id] = data
            self._load_packages()

    def _delete_package(self):
        """Delete selected package"""
        selection = self.packages_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Chọn gói cần xóa")
            return

        item = self.packages_listbox.get(selection[0])
        pkg_id = item.split(":")[0]

        if pkg_id in ["free", "basic", "plus", "pro", "premium"]:
            messagebox.showerror("Lỗi", "Không thể xóa gói mặc định")
            return

        if not messagebox.askyesno("Xác nhận", f"Xóa gói {pkg_id}?"):
            return

        try:
            import requests

            admin_api_url = "http://localhost:8000"
            url = f"{admin_api_url}/features/admin/packages/{pkg_id}"
            response = requests.delete(url, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Thành công", f"Đã xóa gói {pkg_id}")
        except:
            pass

        if pkg_id in self.packages_data:
            del self.packages_data[pkg_id]
        self._load_packages()

    def _move_package_up(self):
        """Move selected package up in the list"""
        selection = self.packages_listbox.curselection()
        if not selection or selection[0] == 0:
            return

        idx = selection[0]
        # Get package IDs in current order
        pkg_ids = [
            self.packages_listbox.get(i).split(":")[0]
            for i in range(self.packages_listbox.size())
        ]

        # Swap orders
        pkg1_id, pkg2_id = pkg_ids[idx], pkg_ids[idx - 1]
        if pkg1_id in self.packages_data and pkg2_id in self.packages_data:
            order1 = self.packages_data[pkg1_id].get("order", idx)
            order2 = self.packages_data[pkg2_id].get("order", idx - 1)
            self.packages_data[pkg1_id]["order"] = order2
            self.packages_data[pkg2_id]["order"] = order1
            self._save_order_to_server(pkg1_id)
            self._save_order_to_server(pkg2_id)

        self._load_packages()
        self.packages_listbox.selection_set(idx - 1)

    def _move_package_down(self):
        """Move selected package down in the list"""
        selection = self.packages_listbox.curselection()
        if not selection or selection[0] >= self.packages_listbox.size() - 1:
            return

        idx = selection[0]
        pkg_ids = [
            self.packages_listbox.get(i).split(":")[0]
            for i in range(self.packages_listbox.size())
        ]

        pkg1_id, pkg2_id = pkg_ids[idx], pkg_ids[idx + 1]
        if pkg1_id in self.packages_data and pkg2_id in self.packages_data:
            order1 = self.packages_data[pkg1_id].get("order", idx)
            order2 = self.packages_data[pkg2_id].get("order", idx + 1)
            self.packages_data[pkg1_id]["order"] = order2
            self.packages_data[pkg2_id]["order"] = order1
            self._save_order_to_server(pkg1_id)
            self._save_order_to_server(pkg2_id)

        self._load_packages()
        self.packages_listbox.selection_set(idx + 1)

    def _save_order_to_server(self, pkg_id):
        """Save package order to server"""
        if pkg_id not in self.packages_data:
            return
        pkg = self.packages_data[pkg_id]
        try:
            import requests

            admin_api_url = "http://localhost:8000"
            data = {
                "name": pkg.get("name", ""),
                "description": pkg.get("description", ""),
                "price": pkg.get("price", 0),
                "duration_days": pkg.get("duration_days", 30),
                "order": pkg.get("order", 99),
                "features": pkg.get("features", []),
                "feature_display": pkg.get("feature_display", []),
                "limits": pkg.get("limits", {}),
                "color": pkg.get("color", "#95a5a6"),
                "recommended": pkg.get("recommended", False),
            }
            requests.post(
                f"{admin_api_url}/features/admin/packages/{pkg_id}",
                json=data,
                timeout=5,
            )
        except:
            pass

    def _on_pkg_drag_start(self, event):
        """Start drag operation"""
        self.pkg_drag_data["index"] = self.packages_listbox.nearest(event.y)

    def _on_pkg_drag_motion(self, event):
        """Handle drag motion - visual feedback"""
        pass  # Could add visual indicator here

    def _on_pkg_drag_end(self, event):
        """End drag - reorder if needed"""
        if self.pkg_drag_data["index"] is None:
            return

        target_idx = self.packages_listbox.nearest(event.y)
        source_idx = self.pkg_drag_data["index"]

        if target_idx != source_idx:
            # Move package from source to target
            self.packages_listbox.selection_set(source_idx)
            while source_idx < target_idx:
                self._move_package_down()
                source_idx += 1
            while source_idx > target_idx:
                self._move_package_up()
                source_idx -= 1

        self.pkg_drag_data["index"] = None
