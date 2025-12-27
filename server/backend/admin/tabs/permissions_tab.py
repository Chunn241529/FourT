"""
User Permissions Tab for Admin UI
"""

import tkinter as tk
from tkinter import ttk, messagebox

from backend.admin.tabs.base_tab import BaseTab


class PermissionsTab(BaseTab):
    """User Permissions tab - manage licenses"""

    def setup(self):
        """Setup User Permissions tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        # Header with refresh button
        header = tk.Frame(self.parent, bg=COLORS["card"])
        header.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(
            header,
            text="User Licenses",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=10, pady=10)

        refresh_btn = ModernButton(
            header,
            text="🔄 Refresh",
            command=self._refresh_permissions,
            kind="primary",
            width=12,
        )
        refresh_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # Custom style cho Treeview - modern dark theme
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview styling
        style.configure(
            "Modern.Treeview",
            background=COLORS["input_bg"],
            foreground=COLORS["fg"],
            fieldbackground=COLORS["input_bg"],
            borderwidth=0,
            rowheight=32,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=COLORS["header"],
            foreground=COLORS["fg"],
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=(8, 6),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#ffffff")],
        )
        style.map("Modern.Treeview.Heading", background=[("active", COLORS["accent"])])

        # Ẩn scrollbar styling
        style.configure("Hidden.Vertical.TScrollbar", width=0)
        style.layout("Hidden.Vertical.TScrollbar", [])

        # Treeview frame với border đẹp
        tree_container = tk.Frame(self.parent, bg=COLORS["border"], padx=1, pady=1)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 10))

        tree_frame = tk.Frame(tree_container, bg=COLORS["input_bg"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Hidden scrollbar (vẫn hoạt động, chỉ ẩn visual)
        vsb = ttk.Scrollbar(
            tree_frame, orient="vertical", style="Hidden.Vertical.TScrollbar"
        )

        # Treeview với style modern
        self.permissions_tree = ttk.Treeview(
            tree_frame,
            columns=("license_key", "package", "expires_at", "device_id", "public_ip"),
            show="headings",
            style="Modern.Treeview",
            yscrollcommand=vsb.set,
        )

        vsb.config(command=self.permissions_tree.yview)

        # Configure columns
        self.permissions_tree.heading("license_key", text="🔑 License Key")
        self.permissions_tree.heading("package", text="📦 Package")
        self.permissions_tree.heading("expires_at", text="⏰ Expires At")
        self.permissions_tree.heading("device_id", text="💻 Device ID")
        self.permissions_tree.heading("public_ip", text="🌐 IP")

        self.permissions_tree.column("license_key", width=200, minwidth=150)
        self.permissions_tree.column("package", width=90, minwidth=80, anchor="center")
        self.permissions_tree.column("expires_at", width=140, minwidth=120)
        self.permissions_tree.column("device_id", width=130, minwidth=100)
        self.permissions_tree.column("public_ip", width=110, minwidth=90)

        # Pack tree (không pack scrollbar visual nhưng vẫn hoạt động)
        self.permissions_tree.pack(fill=tk.BOTH, expand=True)

        # Bind mouse wheel để scroll
        def _on_mousewheel(event):
            self.permissions_tree.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.permissions_tree.bind("<MouseWheel>", _on_mousewheel)
        tree_frame.bind("<MouseWheel>", _on_mousewheel)

        # Action buttons - modern layout
        action_frame = tk.Frame(self.parent, bg=COLORS["bg"])
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ModernButton(
            action_frame,
            text="➕ Add",
            command=self._add_license,
            kind="success",
            width=10,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            action_frame,
            text="📋 Copy",
            command=self._copy_license,
            kind="secondary",
            width=10,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            action_frame,
            text="✏️ Edit",
            command=self._edit_permission,
            kind="primary",
            width=10,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(0, 8))

        ModernButton(
            action_frame,
            text="🗑️ Delete",
            command=self._delete_permission,
            kind="danger",
            width=10,
            anchor="center",
        ).pack(side=tk.LEFT)

    def _copy_license(self):
        """Copy license key của item được chọn vào clipboard"""
        selection = self.permissions_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Vui lòng chọn một license để copy.")
            return

        item = self.permissions_tree.item(selection[0])
        license_key = item["values"][0]

        # Copy vào clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(license_key)
        self.root.update()  # Cần thiết để clipboard hoạt động

        messagebox.showinfo("Copied!", f"Đã copy license:\n{license_key}")

    def load_initial_data(self):
        """Load initial permissions data"""
        self._refresh_permissions()

    def _refresh_permissions(self):
        """Refresh permissions table using LicenseService"""
        # Clear existing items
        for item in self.permissions_tree.get_children():
            self.permissions_tree.delete(item)

        # Load licenses
        try:
            licenses = self.admin.license_service.load_licenses()

            for license_key, data in licenses.items():
                self.permissions_tree.insert(
                    "",
                    "end",
                    values=(
                        license_key,
                        data.get("package", "N/A"),
                        data.get("expires_at", "N/A"),
                        data.get("device_id", "N/A"),
                        data.get("ipv4", data.get("public_ip", "N/A")),
                    ),
                )
        except Exception as e:
            print(f"Error loading licenses: {e}")

    def _get_packages_from_server(self):
        """Lấy danh sách packages từ server"""
        try:
            import requests

            admin_api_url = "http://localhost:8000"
            url = f"{admin_api_url}/features/admin/packages"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                packages_data = response.json().get("packages", {})
                # Sắp xếp theo order, loại bỏ free và trial
                sorted_packages = sorted(
                    [
                        (k, v)
                        for k, v in packages_data.items()
                        if k not in ["free", "trial"]
                    ],
                    key=lambda x: x[1].get("order", 99),
                )
                return [pkg_id for pkg_id, _ in sorted_packages]
        except Exception as e:
            print(f"Error loading packages from server: {e}")

        # Fallback
        return ["basic", "plus", "pro", "premium"]

    def _edit_permission(self):
        """Edit selected user's package"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        selection = self.permissions_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a license to edit.")
            return

        item = self.permissions_tree.item(selection[0])
        values = item["values"]
        license_key = values[0]
        current_package = values[1]
        current_expires = values[2]  # Lấy thời hạn hiện tại

        # Load packages từ server
        packages = self._get_packages_from_server()

        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit License")
        dialog.geometry("420x280")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = tk.Frame(dialog, bg=COLORS["header"], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Edit License",
            font=FONTS["h2"],
            bg=COLORS["header"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=15, pady=12)

        # Content
        content = tk.Frame(dialog, bg=COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)

        # License Key (read-only)
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="License Key:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        tk.Label(
            row,
            text=license_key,
            font=FONTS["body"],
            bg=COLORS["bg"],
            fg=COLORS["accent"],
        ).pack(side=tk.LEFT, padx=5)

        # Package selection
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="Package:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        package_var = tk.StringVar(value=current_package)
        package_combo = ttk.Combobox(
            row, textvariable=package_var, state="readonly", width=22, values=packages
        )
        package_combo.pack(side=tk.LEFT, padx=5)

        # Duration (số ngày)
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="Thời hạn:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        duration_var = tk.StringVar(value="30")
        duration_entry = tk.Entry(
            row,
            textvariable=duration_var,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=10,
        )
        duration_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(
            row, text="ngày", font=FONTS["body"], bg=COLORS["bg"], fg=COLORS["fg_dim"]
        ).pack(side=tk.LEFT)

        tk.Label(
            content,
            text=f"Hết hạn hiện tại: {current_expires}",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w", pady=(0, 5))

        def save_changes():
            new_package = package_var.get()
            try:
                days = int(duration_var.get())
                if days <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("Lỗi", "Vui lòng nhập số ngày hợp lệ (> 0)")
                return

            if self._update_license_package(license_key, new_package, days):
                messagebox.showinfo("Success", f"License đã được cập nhật")
                self._refresh_permissions()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update license")

        # Buttons
        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, padx=25, pady=15)

        ModernButton(
            btn_frame, text="Save", command=save_changes, kind="primary", width=12
        ).pack(side=tk.RIGHT, padx=5)
        ModernButton(
            btn_frame, text="Cancel", command=dialog.destroy, kind="secondary", width=12
        ).pack(side=tk.RIGHT)

    def _delete_permission(self):
        """Delete selected license"""
        selection = self.permissions_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a license to delete.")
            return

        item = self.permissions_tree.item(selection[0])
        license_key = item["values"][0]

        if messagebox.askyesno("Confirm Delete", f"Delete license {license_key}?"):
            if self._remove_license(license_key):
                messagebox.showinfo("Success", "License deleted")
                self._refresh_permissions()
            else:
                messagebox.showerror("Error", "Failed to delete license")

    def _add_license(self):
        """Add a new license"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        dialog = tk.Toplevel(self.root)
        dialog.title("➕ Add New License")
        dialog.geometry("450x400")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = tk.Frame(dialog, bg=COLORS["header"], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="➕ Create New License",
            font=FONTS["h2"],
            bg=COLORS["header"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=15, pady=12)

        # Content
        content = tk.Frame(dialog, bg=COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)

        # License Key
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="License Key:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        key_var = tk.StringVar()
        key_entry = tk.Entry(
            row,
            textvariable=key_var,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=25,
        )
        key_entry.pack(side=tk.LEFT, padx=5)

        # Package (load từ server)
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="Package:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        packages = self._get_packages_from_server()
        package_var = tk.StringVar(
            value=(
                "premium" if "premium" in packages else packages[-1] if packages else ""
            )
        )
        package_combo = ttk.Combobox(
            row, textvariable=package_var, state="readonly", width=22, values=packages
        )
        package_combo.pack(side=tk.LEFT, padx=5)

        def generate_key():
            pkg = package_var.get()
            key_var.set(self.admin.license_service.generate_license_key(pkg))

        # Add generate button after key entry
        row_key = content.winfo_children()[0]
        ModernButton(
            row_key, text="🔄", command=generate_key, kind="secondary", width=3
        ).pack(side=tk.LEFT, padx=2)

        package_combo.bind("<<ComboboxSelected>>", lambda e: generate_key())

        # Duration (nhập số ngày)
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="Thời hạn:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        duration_var = tk.StringVar(value="30")
        duration_entry = tk.Entry(
            row,
            textvariable=duration_var,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=10,
        )
        duration_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(
            row, text="ngày", font=FONTS["body"], bg=COLORS["bg"], fg=COLORS["fg_dim"]
        ).pack(side=tk.LEFT)

        # Notes
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="Notes:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        notes_var = tk.StringVar()
        notes_entry = tk.Entry(
            row,
            textvariable=notes_var,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=28,
        )
        notes_entry.pack(side=tk.LEFT, padx=5)

        # Auto-generate initial key
        generate_key()

        # Buttons
        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, padx=25, pady=20)

        def create_license():
            key = key_var.get().strip()
            if not key:
                messagebox.showwarning(
                    "Missing Key", "Please enter or generate a license key."
                )
                return

            package = package_var.get()
            try:
                days = int(duration_var.get())
                if days <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("Lỗi", "Vui lòng nhập số ngày hợp lệ (> 0)")
                return
            notes = notes_var.get().strip()

            if self.admin.license_service.add_license(key, package, days, notes):
                messagebox.showinfo("Success", f"License created: {key}")
                self._refresh_permissions()
                dialog.destroy()
            else:
                messagebox.showerror(
                    "Error", "Failed to create license. Key may already exist."
                )

        ModernButton(
            btn_frame, text="Create", command=create_license, kind="success", width=12
        ).pack(side=tk.RIGHT, padx=5)
        ModernButton(
            btn_frame, text="Cancel", command=dialog.destroy, kind="secondary", width=12
        ).pack(side=tk.RIGHT)

    def _update_license_package(self, license_key, new_package, days=None):
        """Update license package và thời hạn"""
        try:
            return self.admin.license_service.update_license(
                license_key, package=new_package, days=days
            )
        except Exception as e:
            print(f"Error updating license: {e}")
            return False

    def _remove_license(self, license_key):
        """Remove license using LicenseService"""
        try:
            return self.admin.license_service.delete_license(license_key)
        except Exception as e:
            print(f"Error removing license: {e}")
            return False
