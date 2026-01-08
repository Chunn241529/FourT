"""
Admin UI for FourT Helper
Provides server control, terminal logs, and user permissions management
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import os
import json
import sys
from pathlib import Path
from datetime import datetime

from ui.theme import COLORS, FONTS, ModernButton
from services.skills_service import SkillsService
from services.license_service import LicenseService
from services.server_service import ServerService


class AdminWindow:
    """Main Admin UI Window"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FourT Helper - Admin Panel")
        self.root.geometry("900x800")
        self.root.minsize(900, 800)  # Minimum size for responsive layout
        self.root.configure(bg=COLORS["bg"])

        # Server process reference
        self.server_process = None
        self.server_running = False

        # Paths - handle both script and exe modes
        if getattr(sys, "frozen", False):
            # Running as exe - get the directory where exe is located
            self.backend_dir = Path(sys.executable).parent
        else:
            # Running as script - get project root
            self.backend_dir = Path(__file__).parent.parent

        self.data_dir = self.backend_dir / "data"
        self.licenses_file = self.data_dir / "licenses.json"
        self.devices_file = self.data_dir / "devices.json"
        self.orders_file = self.data_dir / "orders.json"

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

        # Initialize services
        self.skills_service = SkillsService(self.backend_dir / "data" / "skills.json")
        self.license_service = LicenseService(self.licenses_file)
        self.server_service = ServerService(self.backend_dir)

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        """Setup the main UI layout with modern styling"""
        # Header with gradient-like background
        header = tk.Frame(self.root, bg=COLORS["header"], height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Header content
        header_inner = tk.Frame(header, bg=COLORS["header"])
        header_inner.pack(fill=tk.BOTH, expand=True, padx=25, pady=15)

        title_label = tk.Label(
            header_inner,
            text="🛠️ FourT Helper Admin",
            font=("Segoe UI", 18, "bold"),
            bg=COLORS["header"],
            fg="white",
        )
        title_label.pack(side=tk.LEFT)

        # Subtitle
        subtitle = tk.Label(
            header_inner,
            text="Control Panel",
            font=("Segoe UI", 11),
            bg=COLORS["header"],
            fg=COLORS["fg_dim"],
        )
        subtitle.pack(side=tk.LEFT, padx=(10, 0), pady=(5, 0))

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        # Create tabs with better styling
        self.server_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.permissions_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.packages_tab = tk.Frame(self.notebook, bg=COLORS["bg"])  # NEW
        self.skills_tab = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.build_tab = tk.Frame(self.notebook, bg=COLORS["bg"])

        self.notebook.add(self.server_tab, text="  🖥️ Server  ")
        self.notebook.add(self.permissions_tab, text="  👥 Permissions  ")
        self.notebook.add(self.packages_tab, text="  📦 Packages  ")  # NEW
        self.notebook.add(self.skills_tab, text="  🎮 Skills  ")
        self.notebook.add(self.build_tab, text="  🔨 Build  ")

        # Setup each tab
        self._setup_server_tab()
        self._setup_permissions_tab()
        self._setup_packages_tab()  # NEW
        self._setup_skills_tab()
        self._setup_build_tab()

    def _setup_server_tab(self):
        """Setup Server Control tab"""
        # Status Section
        status_frame = tk.Frame(
            self.server_tab, bg=COLORS["card"], relief=tk.FLAT, bd=2
        )
        status_frame.pack(fill=tk.X, padx=20, pady=20)

        tk.Label(
            status_frame,
            text="Server Status",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 5))

        # Status indicator
        status_inner = tk.Frame(status_frame, bg=COLORS["card"])
        status_inner.pack(fill=tk.X, padx=15, pady=(5, 15))

        self.status_indicator = tk.Label(
            status_inner,
            text="●",
            font=("Segoe UI", 20),
            bg=COLORS["card"],
            fg=COLORS["error"],
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))

        self.status_label = tk.Label(
            status_inner,
            text="Server Stopped",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.status_label.pack(side=tk.LEFT)

        # Server info
        info_frame = tk.Frame(self.server_tab, bg=COLORS["card"])
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        tk.Label(
            info_frame,
            text="Server Configuration",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 10))

        # Host and Port
        config_inner = tk.Frame(info_frame, bg=COLORS["card"])
        config_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        tk.Label(
            config_inner,
            text="Host:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"] if hasattr(COLORS, "text_dim") else COLORS["fg"],
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        tk.Label(
            config_inner,
            text="0.0.0.0",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        ).grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        tk.Label(
            config_inner,
            text="Port:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"] if hasattr(COLORS, "text_dim") else COLORS["fg"],
        ).grid(row=1, column=0, sticky=tk.W, pady=5)

        tk.Label(
            config_inner,
            text="8000",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        ).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        tk.Label(
            config_inner,
            text="Local URL:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"] if hasattr(COLORS, "text_dim") else COLORS["fg"],
        ).grid(row=2, column=0, sticky=tk.W, pady=5)

        self.local_url_label = tk.Label(
            config_inner,
            text="http://localhost:8000",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["accent"],
        )
        self.local_url_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Control buttons
        button_frame = tk.Frame(self.server_tab, bg=COLORS["bg"])
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        self.start_button = ModernButton(
            button_frame,
            text="▶ Start Server",
            command=self._start_server,
            kind="success",
            font=FONTS["h2"],
            width=20,
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ModernButton(
            button_frame,
            text="⏹ Stop Server",
            command=self._stop_server,
            kind="danger",
            font=FONTS["h2"],
            width=20,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT)

        # Terminal section (integrated into server tab)
        terminal_header = tk.Frame(self.server_tab, bg=COLORS["card"])
        terminal_header.pack(fill=tk.X, padx=20, pady=(20, 0))

        tk.Label(
            terminal_header,
            text="Server Output",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=10, pady=10)

        clear_btn = ModernButton(
            terminal_header,
            text="Clear",
            command=self._clear_terminal,
            kind="secondary",
            width=10,
        )
        clear_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # Terminal output
        terminal_frame = tk.Frame(self.server_tab, bg=COLORS["input_bg"])
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.terminal_output = scrolledtext.ScrolledText(
            terminal_frame,
            font=FONTS["code"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            height=15,
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.terminal_output.config(state=tk.DISABLED)

    def _setup_permissions_tab(self):
        """Setup User Permissions tab"""
        # Header with refresh button
        header = tk.Frame(self.permissions_tab, bg=COLORS["card"])
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

        # Treeview for licenses
        tree_frame = tk.Frame(self.permissions_tab, bg=COLORS["bg"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        self.permissions_tree = ttk.Treeview(
            tree_frame,
            columns=("license_key", "package", "expires_at", "device_id", "public_ip"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )

        vsb.config(command=self.permissions_tree.yview)
        hsb.config(command=self.permissions_tree.xview)

        # Configure columns
        self.permissions_tree.heading("license_key", text="License Key")
        self.permissions_tree.heading("package", text="Package")
        self.permissions_tree.heading("expires_at", text="Expires At")
        self.permissions_tree.heading("device_id", text="Device ID")
        self.permissions_tree.heading("public_ip", text="Public IP")

        self.permissions_tree.column("license_key", width=150)
        self.permissions_tree.column("package", width=100)
        self.permissions_tree.column("expires_at", width=150)
        self.permissions_tree.column("device_id", width=150)
        self.permissions_tree.column("public_ip", width=120)

        # Grid layout
        self.permissions_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Action buttons
        action_frame = tk.Frame(self.permissions_tab, bg=COLORS["bg"])
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ModernButton(
            action_frame,
            text="➕ Add License",
            command=self._add_license,
            kind="success",
            width=14,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(0, 10))

        ModernButton(
            action_frame,
            text="Edit",
            command=self._edit_permission,
            kind="primary",
            width=10,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(0, 10))

        ModernButton(
            action_frame,
            text="Delete",
            command=self._delete_permission,
            kind="danger",
            width=10,
            anchor="center",
        ).pack(side=tk.LEFT)

    def _parse_duration(self, text: str) -> int:
        """
        Smart parse duration text to days.
        Supports: 30, 1d, 7d, 1m, 1y, 30min, 1h, 1s, etc.
        Returns duration in days (minimum 0).
        """
        import re

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
            "s": 1 / 86400,  # second
            "sec": 1 / 86400,
            "second": 1 / 86400,
            "seconds": 1 / 86400,
            "min": 1 / 1440,  # minute
            "minute": 1 / 1440,
            "minutes": 1 / 1440,
            "h": 1 / 24,  # hour
            "hr": 1 / 24,
            "hour": 1 / 24,
            "hours": 1 / 24,
            "d": 1,  # day
            "day": 1,
            "days": 1,
            "w": 7,  # week
            "week": 7,
            "weeks": 7,
            "m": 30,  # month
            "mo": 30,
            "month": 30,
            "months": 30,
            "y": 365,  # year
            "yr": 365,
            "year": 365,
            "years": 365,
        }

        multiplier = unit_map.get(unit, 1)  # Default to days
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

    def _setup_packages_tab(self):
        """Setup Package Management tab with CRUD operations"""
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

        # Main container - split left (list) and right (edit form)
        main_container = tk.PanedWindow(
            self.packages_tab,
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
            font=FONTS["small"] if "small" in FONTS else ("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"] if "fg_dim" in COLORS else COLORS["fg"],
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
            font=FONTS["small"] if "small" in FONTS else ("Segoe UI", 9),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"] if "fg_dim" in COLORS else COLORS["fg"],
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
            import re

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
        except requests.exceptions.RequestException as e:
            messagebox.showwarning(
                "Lưu Local",
                f"Server không khả dụng.\nDữ liệu chỉ lưu local (cần restart server).",
            )
            # Update local data
            self.packages_data[pkg_id] = data
            self._load_packages()
        except Exception as e:
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

    def _setup_skills_tab(self):
        """Setup Skill Config tab"""
        # Skills file path
        self.skills_file = self.backend_dir / "data" / "skills.json"
        self.selected_skill = None
        self.selected_weapon = None

        # Main container - split into left (list) and right (preview/edit) using PanedWindow for responsive resize
        main_container = tk.PanedWindow(
            self.skills_tab,
            orient=tk.HORIZONTAL,
            bg=COLORS["bg"],
            sashwidth=6,
            sashrelief=tk.RAISED,
        )
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Skill list (resizable with PanedWindow)
        left_panel = tk.Frame(main_container, bg=COLORS["card"])
        main_container.add(left_panel, minsize=280, width=350)

        # === WEAPONS Section ===
        weapons_section = tk.Frame(left_panel, bg=COLORS["card"])
        weapons_section.pack(fill=tk.X, padx=10, pady=(10, 5))

        weapons_header = tk.Frame(weapons_section, bg=COLORS["card"])
        weapons_header.pack(fill=tk.X)

        tk.Label(
            weapons_header,
            text="🗡️ Vũ khí",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        ModernButton(
            weapons_header, text="➕", command=self._add_weapon, kind="success", width=3
        ).pack(side=tk.RIGHT, padx=2)
        ModernButton(
            weapons_header, text="✏️", command=self._edit_weapon, kind="primary", width=3
        ).pack(side=tk.RIGHT, padx=2)
        ModernButton(
            weapons_header,
            text="❌",
            command=self._delete_weapon,
            kind="danger",
            width=3,
        ).pack(side=tk.RIGHT, padx=2)

        # Weapons Canvas (draggable list with hover effects)
        weapons_list_frame = tk.Frame(weapons_section, bg=COLORS["input_bg"])
        weapons_list_frame.pack(fill=tk.X, pady=5)

        self.weapons_canvas = tk.Canvas(
            weapons_list_frame, height=120, bg=COLORS["input_bg"], highlightthickness=0
        )
        self.weapons_canvas.pack(fill=tk.X)

        # Drag state for weapons
        self.weapon_drag_data = {"idx": None, "start_y": 0, "dragging": False}
        self.weapon_hovered_idx = -1

        # Bind weapon canvas events
        self.weapons_canvas.bind("<Button-1>", self._on_weapon_click)
        self.weapons_canvas.bind("<B1-Motion>", self._on_weapon_drag)
        self.weapons_canvas.bind("<ButtonRelease-1>", self._on_weapon_release)
        self.weapons_canvas.bind("<Motion>", self._on_weapon_hover)
        self.weapons_canvas.bind("<Leave>", self._on_weapon_leave)

        # Hidden scroll - scroll with mouse wheel
        def _on_weapon_scroll(event):
            # Check if content is taller than visible area
            bbox = self.weapons_canvas.bbox("all")
            if not bbox:
                return
            content_height = bbox[3] - bbox[1]
            visible_height = self.weapons_canvas.winfo_height()
            if content_height > visible_height:
                self.weapons_canvas.yview_scroll(-1 * (event.delta // 120), "units")

        self.weapons_canvas.bind("<MouseWheel>", _on_weapon_scroll)

        # === SKILLS Section ===
        skills_section = tk.Frame(left_panel, bg=COLORS["card"])
        skills_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Weapon filter
        filter_frame = tk.Frame(skills_section, bg=COLORS["card"])
        filter_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            filter_frame,
            text="Lọc:",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.weapon_var = tk.StringVar(value="all")
        self.weapon_combo = ttk.Combobox(
            filter_frame, textvariable=self.weapon_var, state="readonly", width=15
        )
        self.weapon_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.weapon_combo.bind("<<ComboboxSelected>>", self._on_weapon_filter_change)

        # Skills treeview
        tree_frame = tk.Frame(skills_section, bg=COLORS["bg"])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        self.skills_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "key", "weapon"),
            show="headings",
            yscrollcommand=vsb.set,
        )
        vsb.config(command=self.skills_tree.yview)

        self.skills_tree.heading("name", text="Tên Skill")
        self.skills_tree.heading("key", text="Phím")
        self.skills_tree.heading("weapon", text="Vũ khí")

        self.skills_tree.column("name", width=130)
        self.skills_tree.column("key", width=60)
        self.skills_tree.column("weapon", width=70)

        self.skills_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.skills_tree.bind("<<TreeviewSelect>>", self._on_skill_select)

        # Skill Buttons
        btn_frame = tk.Frame(left_panel, bg=COLORS["card"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ModernButton(
            btn_frame, text="➕", command=self._add_skill, kind="success", width=3
        ).pack(side=tk.LEFT, padx=(0, 5))
        ModernButton(
            btn_frame, text="❌", command=self._delete_skill, kind="danger", width=3
        ).pack(side=tk.LEFT, padx=(0, 5))
        ModernButton(
            btn_frame,
            text="🔄",
            command=self._load_skills_data,
            kind="secondary",
            width=3,
        ).pack(side=tk.RIGHT)

        # Right panel - Edit/Preview (added to PanedWindow)
        right_panel = tk.Frame(main_container, bg=COLORS["card"])
        main_container.add(right_panel, minsize=400)

        tk.Label(
            right_panel,
            text="📝 Chi tiết Skill",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 10))

        # Scrollable container for form (hidden scrollbar)
        scroll_container = tk.Frame(right_panel, bg=COLORS["card"])
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Canvas for scrolling
        self.skill_detail_canvas = tk.Canvas(
            scroll_container, bg=COLORS["card"], highlightthickness=0, bd=0
        )
        self.skill_detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Inner frame to hold all form content
        self.skill_detail_inner = tk.Frame(self.skill_detail_canvas, bg=COLORS["card"])
        self.skill_detail_window = self.skill_detail_canvas.create_window(
            (0, 0), window=self.skill_detail_inner, anchor="nw"
        )

        # Mouse wheel scroll (hidden scrollbar)
        def _on_skill_detail_scroll(event):
            # Only scroll if content is larger than visible area
            if (
                self.skill_detail_inner.winfo_reqheight()
                > self.skill_detail_canvas.winfo_height()
            ):
                self.skill_detail_canvas.yview_scroll(
                    -1 * (event.delta // 120), "units"
                )

        # Store scroll handler for binding to children
        self._skill_detail_scroll_handler = _on_skill_detail_scroll

        self.skill_detail_canvas.bind("<MouseWheel>", _on_skill_detail_scroll)
        self.skill_detail_inner.bind("<MouseWheel>", _on_skill_detail_scroll)

        # Update scroll region when inner frame changes size
        def _on_inner_configure(event):
            self.skill_detail_canvas.configure(
                scrollregion=self.skill_detail_canvas.bbox("all")
            )
            # Bind scroll to all children recursively
            self._bind_scroll_to_children(self.skill_detail_inner)

        def _on_canvas_configure(event):
            # Update inner frame width to match canvas width
            self.skill_detail_canvas.itemconfig(
                self.skill_detail_window, width=event.width
            )

        self.skill_detail_inner.bind("<Configure>", _on_inner_configure)
        self.skill_detail_canvas.bind("<Configure>", _on_canvas_configure)

        # Form fields (now inside scrollable inner frame)
        form_frame = tk.Frame(self.skill_detail_inner, bg=COLORS["card"])
        form_frame.pack(fill=tk.X, padx=15, pady=5)

        # ID
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="ID:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_id_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.skill_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Name
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Tên:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_name_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.skill_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Key
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Phím:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_key_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.skill_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            row,
            text="(lmb/rmb/mouse4/scroll_down...)",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"] if "text_dim" in COLORS else COLORS["fg"],
        ).pack(side=tk.LEFT, padx=5)

        # Modifiers (Alt, Ctrl, Shift)
        mod_row = tk.Frame(form_frame, bg=COLORS["card"])
        mod_row.pack(fill=tk.X, pady=5)
        tk.Label(
            mod_row,
            text="Modifiers:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        self.mod_alt_var = tk.BooleanVar(value=False)
        self.mod_ctrl_var = tk.BooleanVar(value=False)
        self.mod_shift_var = tk.BooleanVar(value=False)

        tk.Checkbutton(
            mod_row,
            text="Alt",
            variable=self.mod_alt_var,
            bg=COLORS["card"],
            fg=COLORS["fg"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["fg"],
            font=FONTS["body"],
        ).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(
            mod_row,
            text="Ctrl",
            variable=self.mod_ctrl_var,
            bg=COLORS["card"],
            fg=COLORS["fg"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["fg"],
            font=FONTS["body"],
        ).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(
            mod_row,
            text="Shift",
            variable=self.mod_shift_var,
            bg=COLORS["card"],
            fg=COLORS["fg"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["fg"],
            font=FONTS["body"],
        ).pack(side=tk.LEFT, padx=5)

        # Hold time
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Hold (s):",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_hold_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=10,
        )
        self.skill_hold_entry.pack(side=tk.LEFT)

        tk.Label(
            row, text="Count:", font=FONTS["body"], bg=COLORS["card"], fg=COLORS["fg"]
        ).pack(side=tk.LEFT, padx=(20, 5))
        self.skill_count_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=5,
        )
        self.skill_count_entry.pack(side=tk.LEFT)

        # Weapon
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Vũ khí:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_weapon_var = tk.StringVar()
        self.skill_weapon_combo = ttk.Combobox(
            row, textvariable=self.skill_weapon_var, state="readonly", width=15
        )
        self.skill_weapon_combo.pack(side=tk.LEFT)

        # Color
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Màu:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_color_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=10,
        )
        self.skill_color_entry.pack(side=tk.LEFT)
        self.color_preview = tk.Label(row, text="  ██  ", bg=COLORS["accent"], width=5)
        self.color_preview.pack(side=tk.LEFT, padx=10)
        self.skill_color_entry.bind("<KeyRelease>", self._update_color_preview)

        # Image
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=5)
        tk.Label(
            row,
            text="Image:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)
        self.skill_image_entry = tk.Entry(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
        )
        self.skill_image_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ModernButton(
            row, text="📁", command=self._browse_image, kind="secondary", width=3
        ).pack(side=tk.LEFT, padx=5)

        # Description
        row = tk.Frame(form_frame, bg=COLORS["card"])
        row.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Label(
            row,
            text="Mô tả:",
            width=10,
            anchor="w",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(
            row,
            text="Dùng [image: file.gif] chèn ảnh. *In đậm*, [#ff0000:Màu đỏ], [khaki:Màu Khaki]",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"] if "text_dim" in COLORS else COLORS["fg"],
        ).pack(side=tk.TOP, anchor="w", pady=(0, 5))

        self.skill_desc_entry = tk.Text(
            row,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            height=4,
            undo=True,
        )
        self.skill_desc_entry.pack(fill=tk.BOTH, expand=True)

        # Undo/Redo bindings
        def safe_undo(event):
            try:
                self.skill_desc_entry.edit_undo()
            except tk.TclError:
                pass  # Stack empty
            return "break"  # Prevent default handling if any

        def safe_redo(event):
            try:
                self.skill_desc_entry.edit_redo()
            except tk.TclError:
                pass
            return "break"

        self.skill_desc_entry.bind("<Control-z>", safe_undo)
        self.skill_desc_entry.bind("<Control-y>", safe_redo)

        # Preview section - Two previews side by side
        preview_frame = tk.Frame(
            self.skill_detail_inner, bg=COLORS["input_bg"], relief=tk.FLAT, bd=1
        )
        preview_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(
            preview_frame,
            text="Preview",
            font=FONTS["bold"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))

        previews_container = tk.Frame(preview_frame, bg=COLORS["input_bg"], height=100)
        previews_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        previews_container.pack_propagate(False)

        # === MENU Preview (left) ===
        menu_preview_frame = tk.Frame(
            previews_container, bg=COLORS["card"], relief=tk.RIDGE, bd=1
        )
        menu_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(
            menu_preview_frame,
            text="📋 Menu Skill",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["fg_dim"] if "fg_dim" in COLORS else COLORS["fg"],
        ).pack(anchor=tk.W, padx=5, pady=5)

        menu_inner = tk.Frame(menu_preview_frame, bg=COLORS["bg"])
        menu_inner.pack(fill=tk.X, padx=5, pady=(0, 10))

        # Menu style: image + name + key
        self.menu_preview_image = tk.Label(
            menu_inner, text="", bg=COLORS["bg"], width=5, height=2
        )
        self.menu_preview_image.pack(side=tk.LEFT, padx=(5, 10))

        self.menu_preview_dot = tk.Label(
            menu_inner,
            text="●",
            font=("Arial", 12),
            bg=COLORS["bg"],
            fg=COLORS["accent"],
        )
        self.menu_preview_dot.pack(side=tk.LEFT, padx=(0, 5))

        self.menu_preview_name = tk.Label(
            menu_inner,
            text="Skill Name",
            font=FONTS["body"],
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        )
        self.menu_preview_name.pack(side=tk.LEFT)

        self.menu_preview_key = tk.Label(
            menu_inner,
            text="[KEY]",
            font=FONTS["small"],
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"] if "fg_dim" in COLORS else COLORS["fg"],
        )
        self.menu_preview_key.pack(side=tk.RIGHT, padx=5)

        # === TIMELINE Preview (right) ===
        timeline_preview_frame = tk.Frame(
            previews_container, bg=COLORS["card"], relief=tk.RIDGE, bd=1
        )
        timeline_preview_frame.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0)
        )

        tk.Label(
            timeline_preview_frame,
            text="� Timeline",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["fg_dim"] if "fg_dim" in COLORS else COLORS["fg"],
        ).pack(anchor=tk.W, padx=5, pady=5)

        timeline_inner = tk.Frame(timeline_preview_frame, bg=COLORS["bg"])
        timeline_inner.pack(fill=tk.X, padx=5, pady=(0, 10))

        # Timeline style: colored box with icon only
        self.timeline_preview_box = tk.Frame(
            timeline_inner, bg=COLORS["accent"], width=50, height=50
        )
        self.timeline_preview_box.pack(side=tk.LEFT, padx=10, pady=5)
        self.timeline_preview_box.pack_propagate(False)

        self.timeline_preview_image = tk.Label(
            self.timeline_preview_box, text="", bg=COLORS["accent"]
        )
        self.timeline_preview_image.place(relx=0.5, rely=0.5, anchor="center")

        self.timeline_preview_key_fallback = tk.Label(
            self.timeline_preview_box,
            text="K",
            font=FONTS["h2"],
            bg=COLORS["accent"],
            fg="white",
        )
        self.timeline_preview_key_fallback.place(relx=0.5, rely=0.5, anchor="center")

        # Keep photo references
        self.preview_photo_menu = None
        self.preview_photo_timeline = None

        # Save button
        save_frame = tk.Frame(self.skill_detail_inner, bg=COLORS["card"])
        save_frame.pack(fill=tk.X, padx=15, pady=10)

        ModernButton(
            save_frame,
            text="💾 Lưu Skill",
            command=self._save_skill,
            kind="primary",
            width=15,
        ).pack(side=tk.LEFT)

        # Load initial data
        self._load_skills_data()

    def _bind_scroll_to_children(self, widget):
        """Recursively bind mouse wheel scroll to all children widgets"""
        try:
            for child in widget.winfo_children():
                # Bind scroll event (skip Text widgets to allow their own scrolling)
                if not isinstance(child, tk.Text):
                    child.bind(
                        "<MouseWheel>", self._skill_detail_scroll_handler, add="+"
                    )
                # Recursively bind to children
                self._bind_scroll_to_children(child)
        except:
            pass

    def _load_skills_data(self):
        """Load skills and weapons from JSON using SkillsService"""
        try:
            self.skills_data = self.skills_service.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.skills_data = {"weapons": [], "skills": []}

        # Populate weapon filter
        weapons = ["all"] + self.skills_service.get_weapon_ids()
        self.weapon_combo["values"] = weapons
        self.skill_weapon_combo["values"] = self.skills_service.get_weapon_ids()

        # Refresh weapons listbox
        self._refresh_weapons_list()
        self._refresh_skills()

    def _refresh_weapons_list(self):
        """Refresh weapons canvas with draggable items"""
        self.weapons_canvas.delete("all")
        self.weapon_item_rects = []

        # Load weapon images cache
        if not hasattr(self, "weapon_image_cache"):
            self.weapon_image_cache = {}

        weapons = self.skills_data.get("weapons", [])
        row_height = 28
        y = 4

        for idx, weapon in enumerate(weapons):
            icon = weapon.get("icon", "")
            name = weapon.get("name", weapon["id"])
            color = weapon.get("color", "#95a5a6")
            image_path = weapon.get("image", "")

            # Determine if selected or hovered
            is_selected = (
                hasattr(self, "selected_weapon_idx") and self.selected_weapon_idx == idx
            )
            is_hovered = self.weapon_hovered_idx == idx

            # Background
            if is_selected:
                bg_color = COLORS["accent"]
            elif is_hovered:
                bg_color = COLORS["sidebar_hover"]
            else:
                bg_color = COLORS["input_bg"]

            x1, y1 = 4, y
            x2, y2 = self.weapons_canvas.winfo_width() - 4 or 320, y + row_height - 2

            # Draw rounded background
            self.weapons_canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=bg_color,
                outline=COLORS["border"] if is_hovered else "",
                tags=(f"weapon_{idx}", "weapon_item"),
            )

            # Try to load and display weapon image
            img_x = x1 + 14  # Center of image area
            has_image = False

            if image_path:
                # Try to load image
                cache_key = f"{weapon['id']}_{image_path}"
                if cache_key not in self.weapon_image_cache:
                    try:
                        from PIL import Image, ImageTk

                        wwm_resources = self.backend_dir / "wwm_resources"
                        paths_to_try = [
                            wwm_resources / image_path,
                            wwm_resources / Path(image_path).name,
                            Path(image_path),
                        ]
                        for path in paths_to_try:
                            if path.exists():
                                img = Image.open(path)
                                img = img.resize(
                                    (18, 18),
                                    (
                                        Image.Resampling.LANCZOS
                                        if hasattr(Image, "Resampling")
                                        else Image.LANCZOS
                                    ),
                                )
                                self.weapon_image_cache[cache_key] = ImageTk.PhotoImage(
                                    img
                                )
                                break
                    except:
                        pass

                if cache_key in self.weapon_image_cache:
                    self.weapons_canvas.create_image(
                        img_x,
                        (y1 + y2) / 2,
                        image=self.weapon_image_cache[cache_key],
                        tags=(f"weapon_{idx}", "weapon_item"),
                    )
                    has_image = True

            if not has_image:
                # Fallback: Color box
                self.weapons_canvas.create_rectangle(
                    x1 + 6,
                    y1 + 5,
                    x1 + 22,
                    y2 - 5,
                    fill=color,
                    outline="",
                    tags=(f"weapon_{idx}", "weapon_item"),
                )

            # Icon + Name
            display_text = f"{icon} {name}" if icon else name
            text_color = "white" if is_selected else COLORS["fg"]
            self.weapons_canvas.create_text(
                x1 + 30,
                (y1 + y2) / 2,
                text=display_text,
                anchor="w",
                fill=text_color,
                font=FONTS["small"],
                tags=(f"weapon_{idx}", "weapon_item"),
            )

            # Drag handle indicator
            self.weapons_canvas.create_text(
                x2 - 15,
                (y1 + y2) / 2,
                text="⋮⋮",
                fill=COLORS["fg_dim"],
                font=("Arial", 9),
                tags=(f"weapon_{idx}", "weapon_item"),
            )

            # Store rect for hit detection
            self.weapon_item_rects.append((x1, y1, x2, y2, idx))

            y += row_height

        # Update canvas scroll region
        self.weapons_canvas.configure(scrollregion=(0, 0, 320, y + 4))

    def _get_weapon_at_y(self, y):
        """Get weapon index at y position"""
        # Convert to canvas coordinates (account for scrolling)
        canvas_y = self.weapons_canvas.canvasy(y)
        for x1, y1, x2, y2, idx in getattr(self, "weapon_item_rects", []):
            if y1 <= canvas_y <= y2:
                return idx
        return None

    def _on_weapon_click(self, event):
        """Handle weapon canvas click"""
        idx = self._get_weapon_at_y(event.y)
        if idx is not None:
            self.selected_weapon_idx = idx
            self.weapon_drag_data["idx"] = idx
            self.weapon_drag_data["start_y"] = event.y
            self.weapon_drag_data["dragging"] = False
            self._refresh_weapons_list()

    def _on_weapon_drag(self, event):
        """Handle weapon drag for reordering"""
        if self.weapon_drag_data["idx"] is None:
            return

        # Check if we've moved enough to start dragging
        if abs(event.y - self.weapon_drag_data["start_y"]) > 10:
            self.weapon_drag_data["dragging"] = True
            self.weapons_canvas.config(cursor="fleur")

            # Find target position
            target_idx = self._get_weapon_at_y(event.y)
            if target_idx is not None and target_idx != self.weapon_drag_data["idx"]:
                # Swap positions
                weapons = self.skills_data.get("weapons", [])
                src_idx = self.weapon_drag_data["idx"]

                if 0 <= src_idx < len(weapons) and 0 <= target_idx < len(weapons):
                    # Move weapon
                    weapon = weapons.pop(src_idx)
                    weapons.insert(target_idx, weapon)

                    # Update indices
                    self.weapon_drag_data["idx"] = target_idx
                    self.selected_weapon_idx = target_idx
                    self.weapon_drag_data["start_y"] = (
                        event.y
                    )  # Reset start_y to avoid repeated swaps

                    # Refresh display
                    self._refresh_weapons_list()

    def _on_weapon_release(self, event):
        """Handle weapon drag release"""
        was_dragging = self.weapon_drag_data.get("dragging", False)

        self.weapon_drag_data = {"idx": None, "start_y": 0, "dragging": False}
        self.weapons_canvas.config(cursor="")

        if was_dragging:
            # Save the new order
            self._save_skills_data()
            # Reload to update filter combos etc
            weapons = ["all"] + [w["id"] for w in self.skills_data.get("weapons", [])]
            self.weapon_combo["values"] = weapons
            self.skill_weapon_combo["values"] = [
                w["id"] for w in self.skills_data.get("weapons", [])
            ]

    def _on_weapon_hover(self, event):
        """Handle weapon hover effect"""
        idx = self._get_weapon_at_y(event.y)
        if idx != self.weapon_hovered_idx:
            self.weapon_hovered_idx = idx
            if idx is not None:
                self.weapons_canvas.config(cursor="hand2")
            self._refresh_weapons_list()

    def _on_weapon_leave(self, event):
        """Handle mouse leave weapons canvas"""
        self.weapon_hovered_idx = -1
        self.weapons_canvas.config(cursor="")
        self._refresh_weapons_list()

    def _add_weapon(self):
        """Add new weapon"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Thêm Vũ Khí")
        dialog.geometry("400x300")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        # Form
        form = tk.Frame(dialog, bg=COLORS["bg"])
        form.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(form, text="ID:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=0, column=0, sticky="w", pady=5
        )
        id_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        id_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Tên:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=1, column=0, sticky="w", pady=5
        )
        name_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        name_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Icon:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=2, column=0, sticky="w", pady=5
        )
        icon_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        icon_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Màu (#hex):", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=3, column=0, sticky="w", pady=5
        )
        color_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        color_entry.insert(0, "#95a5a6")
        color_entry.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Image:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=4, column=0, sticky="w", pady=5
        )
        image_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        image_entry.grid(row=4, column=1, sticky="ew", pady=5)

        def browse_image():
            from tkinter import filedialog

            filepath = filedialog.askopenfilename(
                initialdir=self.backend_dir / "wwm_resources",
                filetypes=[("Images", "*.png *.jpg *.webp")],
            )
            if filepath:
                image_entry.delete(0, tk.END)
                image_entry.insert(0, Path(filepath).name)

        ModernButton(
            form, text="📁", command=browse_image, kind="secondary", width=3
        ).grid(row=4, column=2, padx=2)

        form.columnconfigure(1, weight=1)

        def save():
            weapon_id = id_entry.get().strip()
            name = name_entry.get().strip()
            if not weapon_id:
                messagebox.showwarning("Lỗi", "ID không được để trống")
                return

            new_weapon = {
                "id": weapon_id,
                "name": name or weapon_id,
                "icon": icon_entry.get().strip(),
                "color": color_entry.get().strip() or "#95a5a6",
                "image": image_entry.get().strip(),
            }

            self.skills_data.setdefault("weapons", []).append(new_weapon)
            self._save_skills_data()
            self._load_skills_data()
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        ModernButton(
            btn_frame, text="Lưu", command=save, kind="primary", width=10
        ).pack(side=tk.LEFT, padx=5)
        ModernButton(
            btn_frame, text="Hủy", command=dialog.destroy, kind="secondary", width=10
        ).pack(side=tk.LEFT)

    def _edit_weapon(self):
        """Edit selected weapon"""
        if not hasattr(self, "selected_weapon_idx") or self.selected_weapon_idx is None:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn vũ khí để sửa")
            return

        idx = self.selected_weapon_idx
        weapon = self.skills_data.get("weapons", [])[idx]

        dialog = tk.Toplevel(self.root)
        dialog.title("Sửa Vũ Khí")
        dialog.geometry("400x300")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        form = tk.Frame(dialog, bg=COLORS["bg"])
        form.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(form, text="ID:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=0, column=0, sticky="w", pady=5
        )
        id_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        id_entry.insert(0, weapon.get("id", ""))
        id_entry.config(state="disabled")
        id_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Tên:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=1, column=0, sticky="w", pady=5
        )
        name_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        name_entry.insert(0, weapon.get("name", ""))
        name_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Icon:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=2, column=0, sticky="w", pady=5
        )
        icon_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        icon_entry.insert(0, weapon.get("icon", ""))
        icon_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Màu (#hex):", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=3, column=0, sticky="w", pady=5
        )
        color_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        color_entry.insert(0, weapon.get("color", "#95a5a6"))
        color_entry.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)

        tk.Label(form, text="Image:", bg=COLORS["bg"], fg=COLORS["fg"]).grid(
            row=4, column=0, sticky="w", pady=5
        )
        image_entry = tk.Entry(form, bg=COLORS["input_bg"], fg=COLORS["fg"])
        image_entry.insert(0, weapon.get("image", ""))
        image_entry.grid(row=4, column=1, sticky="ew", pady=5)

        def browse_image():
            from tkinter import filedialog

            filepath = filedialog.askopenfilename(
                initialdir=self.backend_dir / "wwm_resources",
                filetypes=[("Images", "*.png *.jpg *.webp")],
            )
            if filepath:
                image_entry.delete(0, tk.END)
                image_entry.insert(0, Path(filepath).name)

        ModernButton(
            form, text="📁", command=browse_image, kind="secondary", width=3
        ).grid(row=4, column=2, padx=2)

        form.columnconfigure(1, weight=1)

        def save():
            self.skills_data["weapons"][idx] = {
                "id": weapon["id"],
                "name": name_entry.get().strip() or weapon["id"],
                "icon": icon_entry.get().strip(),
                "color": color_entry.get().strip() or "#95a5a6",
                "image": image_entry.get().strip(),
            }
            # Clear image cache for this weapon
            if hasattr(self, "weapon_image_cache"):
                keys_to_delete = [
                    k for k in self.weapon_image_cache if k.startswith(weapon["id"])
                ]
                for k in keys_to_delete:
                    del self.weapon_image_cache[k]

            self._save_skills_data()
            self._load_skills_data()
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        ModernButton(
            btn_frame, text="Lưu", command=save, kind="primary", width=10
        ).pack(side=tk.LEFT, padx=5)
        ModernButton(
            btn_frame, text="Hủy", command=dialog.destroy, kind="secondary", width=10
        ).pack(side=tk.LEFT)

    def _delete_weapon(self):
        """Delete selected weapon"""
        if not hasattr(self, "selected_weapon_idx") or self.selected_weapon_idx is None:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn vũ khí để xóa")
            return

        idx = self.selected_weapon_idx
        weapon = self.skills_data.get("weapons", [])[idx]

        # Check if any skills use this weapon
        skills_using = [
            s
            for s in self.skills_data.get("skills", [])
            if s.get("weapon") == weapon["id"]
        ]

        msg = f"Xóa vũ khí '{weapon['name']}'?"
        if skills_using:
            msg += f"\n⚠️ Có {len(skills_using)} skill đang dùng vũ khí này!"

        if messagebox.askyesno("Xác nhận", msg):
            del self.skills_data["weapons"][idx]
            self._save_skills_data()
            self._load_skills_data()

    def _save_skills_data(self):
        """Save skills data to JSON using SkillsService"""
        try:
            self.skills_service.save_data()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def _refresh_skills(self):
        """Refresh skills list"""
        # Clear tree
        for item in self.skills_tree.get_children():
            self.skills_tree.delete(item)

        # Filter skills
        weapon_filter = self.weapon_var.get()
        skills = self.skills_data.get("skills", [])

        for skill in skills:
            if weapon_filter == "all" or skill.get("weapon") == weapon_filter:
                self.skills_tree.insert(
                    "",
                    "end",
                    iid=skill["id"],
                    values=(
                        skill.get("name", ""),
                        skill.get("key", ""),
                        skill.get("weapon", ""),
                    ),
                )

    def _on_weapon_filter_change(self, event=None):
        """Handle weapon filter change"""
        self._refresh_skills()

    def _on_skill_select(self, event=None):
        """Handle skill selection"""
        selection = self.skills_tree.selection()
        if not selection:
            return

        skill_id = selection[0]
        skill = next(
            (s for s in self.skills_data.get("skills", []) if s["id"] == skill_id), None
        )

        if skill:
            self.selected_skill = skill
            self._populate_skill_form(skill)

    def _populate_skill_form(self, skill):
        """Fill form with skill data"""
        self.skill_id_entry.delete(0, tk.END)
        self.skill_id_entry.insert(0, skill.get("id", ""))

        self.skill_name_entry.delete(0, tk.END)
        self.skill_name_entry.insert(0, skill.get("name", ""))

        self.skill_key_entry.delete(0, tk.END)
        self.skill_key_entry.insert(0, skill.get("key", ""))

        self.skill_hold_entry.delete(0, tk.END)
        self.skill_hold_entry.insert(0, str(skill.get("hold", 0.05)))

        self.skill_count_entry.delete(0, tk.END)
        self.skill_count_entry.insert(0, str(skill.get("click_count", 1)))

        self.skill_weapon_var.set(skill.get("weapon", "common"))

        self.skill_color_entry.delete(0, tk.END)
        self.skill_color_entry.insert(0, skill.get("color", ""))

        self.skill_image_entry.delete(0, tk.END)
        self.skill_image_entry.insert(0, skill.get("image", ""))

        self.skill_desc_entry.delete("1.0", tk.END)
        self.skill_desc_entry.insert("1.0", skill.get("description", ""))

        # Load modifiers
        modifiers = skill.get("modifiers", [])
        self.mod_alt_var.set("alt" in modifiers)
        self.mod_ctrl_var.set("ctrl" in modifiers)
        self.mod_shift_var.set("shift" in modifiers)

        self._update_preview()

    def _update_color_preview(self, event=None):
        """Update color preview"""
        color = self.skill_color_entry.get()
        if color and (color.startswith("#") and len(color) in [4, 7]):
            try:
                self.color_preview.config(bg=color)
            except:
                pass
        self._update_preview()

    def _update_preview(self):
        """Update both Menu and Timeline skill previews"""
        name = self.skill_name_entry.get() or "Skill Name"
        key = self.skill_key_entry.get() or "key"
        color = self.skill_color_entry.get()
        image_path = self.skill_image_entry.get()

        # Get weapon color if no skill color
        if not color:
            weapon_id = self.skill_weapon_var.get()
            weapon = next(
                (
                    w
                    for w in self.skills_data.get("weapons", [])
                    if w["id"] == weapon_id
                ),
                None,
            )
            if weapon:
                color = weapon.get("color", "#95a5a6")
            else:
                color = "#95a5a6"

        try:
            self.color_preview.config(bg=color)
        except:
            pass

        # Update Menu Preview
        self.menu_preview_name.config(text=name)
        self.menu_preview_key.config(text=f"[{key.upper()}]")
        self.menu_preview_dot.config(fg=color)

        # Update Timeline Preview
        try:
            self.timeline_preview_box.config(bg=color)
            self.timeline_preview_image.config(bg=color)
            self.timeline_preview_key_fallback.config(bg=color)
        except:
            pass

        # Build key display with modifiers for timeline
        modifiers = []
        if self.mod_alt_var.get():
            modifiers.append("alt")
        if self.mod_ctrl_var.get():
            modifiers.append("ctrl")
        if self.mod_shift_var.get():
            modifiers.append("shift")

        if modifiers:
            key_display = "+".join(modifiers) + "+" + key
        else:
            key_display = key

        # Load and display images
        self._load_preview_images(image_path, color, key_display)

    def _load_preview_images(self, image_path, color, key_display):
        """Load and display images in both previews"""
        try:
            from PIL import Image, ImageTk
        except ImportError:
            self._show_preview_fallback(key_display)
            return

        if not image_path:
            self._show_preview_fallback(key_display)
            return

        try:
            # Try different paths
            wwm_resources = self.backend_dir / "wwm_resources"
            paths_to_try = [
                wwm_resources / image_path,
                wwm_resources / Path(image_path).name,
                Path(image_path),
            ]

            img = None
            for path in paths_to_try:
                if path.exists():
                    img = Image.open(path)
                    break

            if img:
                # Menu preview - 40x40
                img_menu = img.copy()
                img_menu = img_menu.resize(
                    (40, 40),
                    (
                        Image.Resampling.LANCZOS
                        if hasattr(Image, "Resampling")
                        else Image.LANCZOS
                    ),
                )
                self.preview_photo_menu = ImageTk.PhotoImage(img_menu)
                self.menu_preview_image.config(
                    image=self.preview_photo_menu, text="", width=40, height=40
                )
                # Hide dot by making it empty
                self.menu_preview_dot.config(text="")

                # Timeline preview - 40x40
                img_timeline = img.copy()
                img_timeline = img_timeline.resize(
                    (40, 40),
                    (
                        Image.Resampling.LANCZOS
                        if hasattr(Image, "Resampling")
                        else Image.LANCZOS
                    ),
                )
                self.preview_photo_timeline = ImageTk.PhotoImage(img_timeline)
                self.timeline_preview_image.config(
                    image=self.preview_photo_timeline, text=""
                )
                # Hide key fallback
                self.timeline_preview_key_fallback.config(text="")
            else:
                self._show_preview_fallback(key_display or "?")

        except Exception as e:
            self._show_preview_fallback("!")

    def _show_preview_fallback(self, key_text):
        """Show fallback preview when no image available"""
        try:
            # Clear menu image, show dot
            self.menu_preview_image.config(image="", text="")
            self.preview_photo_menu = None
            self.menu_preview_dot.config(text="●")

            # Clear timeline image, show key text
            self.timeline_preview_image.config(image="", text="")
            self.preview_photo_timeline = None
            self.timeline_preview_key_fallback.config(
                text=key_text.upper() if key_text else "K"
            )
        except:
            pass

    def _add_skill(self):
        """Add new skill"""
        self.selected_skill = None

        # Get current weapon filter for auto ID generation
        current_weapon = self.weapon_var.get()
        if current_weapon == "all":
            current_weapon = "common"

        # Count existing skills for this weapon to generate next ID
        skills = self.skills_data.get("skills", [])
        weapon_skills = [s for s in skills if s.get("weapon") == current_weapon]
        next_num = len(weapon_skills) + 1

        # Generate ID: weapon_skill_N
        auto_id = f"{current_weapon}_skill_{next_num}"

        # Clear form and set auto-generated values
        self.skill_id_entry.delete(0, tk.END)
        self.skill_id_entry.insert(0, auto_id)
        self.skill_name_entry.delete(0, tk.END)
        self.skill_key_entry.delete(0, tk.END)
        self.skill_hold_entry.delete(0, tk.END)
        self.skill_hold_entry.insert(0, "0.05")
        self.skill_count_entry.delete(0, tk.END)
        self.skill_count_entry.insert(0, "1")
        self.skill_weapon_var.set(current_weapon)  # Set to current filter
        self.skill_color_entry.delete(0, tk.END)
        self.skill_image_entry.delete(0, tk.END)
        self.skill_desc_entry.delete("1.0", tk.END)

        # Reset modifiers
        self.mod_alt_var.set(False)
        self.mod_ctrl_var.set(False)
        self.mod_shift_var.set(False)

        self._update_preview()

    def _save_skill(self):
        """Save skill to JSON"""
        skill_id = self.skill_id_entry.get().strip()
        name = self.skill_name_entry.get().strip()
        key = self.skill_key_entry.get().strip()

        if not skill_id or not name:
            messagebox.showwarning("Thiếu thông tin", "ID và Tên là bắt buộc")
            return

        try:
            hold = float(self.skill_hold_entry.get() or 0.05)
        except:
            hold = 0.05

        try:
            click_count = int(self.skill_count_entry.get() or 1)
            if click_count < 1:
                click_count = 1
        except:
            click_count = 1

        # Collect modifiers
        modifiers = []
        if self.mod_alt_var.get():
            modifiers.append("alt")
        if self.mod_ctrl_var.get():
            modifiers.append("ctrl")
        if self.mod_shift_var.get():
            modifiers.append("shift")

        new_skill = {
            "id": skill_id,
            "name": name,
            "key": key,
            "color": self.skill_color_entry.get().strip(),
            "hold": hold,
            "click_count": click_count,
            "weapon": self.skill_weapon_var.get(),
            "image": self.skill_image_entry.get().strip(),
            "description": self.skill_desc_entry.get("1.0", tk.END).strip(),
        }

        # Only add modifiers if not empty
        if modifiers:
            new_skill["modifiers"] = modifiers

        # Update or add
        skills = self.skills_data.get("skills", [])
        existing_idx = next(
            (i for i, s in enumerate(skills) if s["id"] == skill_id), None
        )

        if existing_idx is not None:
            skills[existing_idx] = new_skill
        else:
            skills.append(new_skill)

        self.skills_data["skills"] = skills

        # Save to file
        try:
            with open(self.skills_file, "w", encoding="utf-8") as f:
                json.dump(self.skills_data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Thành công", f"Đã lưu skill: {name}")
            self._refresh_skills()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu: {e}")

    def _delete_skill(self):
        """Delete selected skill"""
        selection = self.skills_tree.selection()
        if not selection:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn skill để xóa")
            return

        skill_id = selection[0]

        if messagebox.askyesno("Xác nhận", f"Xóa skill '{skill_id}'?"):
            skills = self.skills_data.get("skills", [])
            self.skills_data["skills"] = [s for s in skills if s["id"] != skill_id]

            try:
                with open(self.skills_file, "w", encoding="utf-8") as f:
                    json.dump(self.skills_data, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Thành công", "Đã xóa skill")
                self._refresh_skills()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa: {e}")

    def _browse_image(self):
        """Browse for image file"""
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Chọn ảnh skill",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            # Get just the filename
            import os

            basename = os.path.basename(filename)
            self.skill_image_entry.delete(0, tk.END)
            self.skill_image_entry.insert(0, basename)

    def _load_initial_data(self):
        """Load initial permissions data"""
        self._refresh_permissions()

    def _refresh_permissions(self):
        """Refresh permissions table using LicenseService"""
        # Clear existing items
        for item in self.permissions_tree.get_children():
            self.permissions_tree.delete(item)

        # Load licenses
        try:
            licenses = self.license_service.load_licenses()

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
            self._log_to_terminal(f"Error loading licenses: {e}\n")

    def _edit_permission(self):
        """Edit selected user's package"""
        selection = self.permissions_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a license to edit.")
            return

        item = self.permissions_tree.item(selection[0])
        values = item["values"]
        license_key = values[0]
        current_package = values[1]

        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Package")
        dialog.geometry("400x350")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=f"License: {license_key}",
            font=FONTS["h2"],
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(pady=(20, 10))

        tk.Label(
            dialog,
            text="Select New Package:",
            font=FONTS["body"],
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(pady=(10, 5))

        package_var = tk.StringVar(value=current_package)
        packages = ["free", "basic", "pro", "premium"]

        for pkg in packages:
            tk.Radiobutton(
                dialog,
                text=pkg.capitalize(),
                variable=package_var,
                value=pkg,
                font=FONTS["body"],
                bg=COLORS["bg"],
                fg=COLORS["fg"],
                selectcolor=COLORS["input_bg"],
                activebackground=COLORS["bg"],
                activeforeground=COLORS["accent"],
            ).pack(anchor=tk.W, padx=50, pady=2)

        def save_changes():
            new_package = package_var.get()
            if self._update_license_package(license_key, new_package):
                messagebox.showinfo("Success", f"Package updated to {new_package}")
                self._refresh_permissions()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update package")

        button_frame = tk.Frame(dialog, bg=COLORS["bg"])
        button_frame.pack(pady=20)

        ModernButton(
            button_frame, text="Save", command=save_changes, kind="primary", width=12
        ).pack(side=tk.LEFT, padx=5)

        ModernButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            kind="secondary",
            width=12,
        ).pack(side=tk.LEFT, padx=5)

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

        def generate_key():
            pkg = package_var.get()
            key_var.set(self.license_service.generate_license_key(pkg))

        ModernButton(
            row, text="🔄", command=generate_key, kind="secondary", width=3
        ).pack(side=tk.LEFT, padx=2)

        # Package
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

        package_var = tk.StringVar(value="premium")
        package_combo = ttk.Combobox(
            row,
            textvariable=package_var,
            state="readonly",
            width=22,
            values=["basic", "pro", "premium"],
        )
        package_combo.pack(side=tk.LEFT, padx=5)
        package_combo.bind("<<ComboboxSelected>>", lambda e: generate_key())

        # Duration
        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(fill=tk.X, pady=8)
        tk.Label(
            row,
            text="Duration:",
            font=FONTS["body"],
            width=12,
            anchor="w",
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        duration_options = [
            ("7 days", 7),
            ("30 days", 30),
            ("90 days", 90),
            ("365 days", 365),
        ]
        duration_var = tk.StringVar(value="30 days")
        duration_combo = ttk.Combobox(
            row,
            textvariable=duration_var,
            state="readonly",
            width=22,
            values=[d[0] for d in duration_options],
        )
        duration_combo.pack(side=tk.LEFT, padx=5)

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
            duration_text = duration_var.get()
            days = dict(duration_options).get(duration_text, 30)
            notes = notes_var.get().strip()

            if self.license_service.add_license(key, package, days, notes):
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

    def _update_license_package(self, license_key, new_package):
        """Update license package using LicenseService"""
        try:
            return self.license_service.update_package(license_key, new_package)
        except Exception as e:
            self._log_to_terminal(f"Error updating license: {e}\n")
            return False

    def _remove_license(self, license_key):
        """Remove license using LicenseService"""
        try:
            return self.license_service.delete_license(license_key)
        except Exception as e:
            self._log_to_terminal(f"Error removing license: {e}\n")
            return False

    def _kill_existing_processes(self):
        """Kill existing server and ngrok processes using ServerService"""
        killed_processes = self.server_service.kill_existing_processes(
            self._log_to_terminal
        )

        for msg in killed_processes:
            self._log_to_terminal(f"{msg}\n")

        return len(killed_processes)

    def _start_server(self):
        """Start the FastAPI server using ServerService"""
        if self.server_service.is_running():
            return

        try:
            # Kill any existing server/ngrok processes first
            self._log_to_terminal("=== Checking for existing processes ===\n")
            killed_count = self._kill_existing_processes()

            if killed_count > 0:
                self._log_to_terminal(
                    f"Cleaned up {killed_count} existing process(es)\n\n"
                )
            else:
                self._log_to_terminal("No existing processes found\n\n")

            # Start server using service
            self.server_process = self.server_service.start_server(
                self._log_to_terminal
            )
            self.server_running = self.server_service.is_running()
            self._update_server_status(True)

            # Start thread to read output
            threading.Thread(target=self._read_server_output, daemon=True).start()

            self._log_to_terminal("=== Starting FourT Helper Backend Server ===\n")

        except Exception as e:
            self._log_to_terminal(f"Error starting server: {e}\n")
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def _stop_server(self):
        """Stop the FastAPI server using ServerService"""
        if not self.server_service.is_running():
            return

        try:
            self.server_service.stop_server()
            self.server_running = False
            self.server_process = None
            self._update_server_status(False)
            self._log_to_terminal("Server stopped\n")
        except Exception as e:
            self._log_to_terminal(f"Error stopping server: {e}\n")
            messagebox.showerror("Error", f"Failed to stop server: {e}")

    def _read_server_output(self):
        """Read server output and display in terminal"""
        try:
            while self.server_running and self.server_process:
                line = self.server_process.stdout.readline()
                if line:
                    self._log_to_terminal(line)
                elif self.server_process.poll() is not None:
                    # Process has terminated
                    self._log_to_terminal("\n=== Server process terminated ===\n")
                    break
        except Exception as e:
            self._log_to_terminal(f"Error reading server output: {e}\n")

    def _update_server_status(self, running):
        """Update server status UI"""
        if running:
            self.status_indicator.config(fg=COLORS["success"])
            self.status_label.config(text="Server Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.status_indicator.config(fg=COLORS["error"])
            self.status_label.config(text="Server Stopped")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _log_to_terminal(self, message):
        """Log message to terminal widget"""

        def append():
            self.terminal_output.config(state=tk.NORMAL)
            self.terminal_output.insert(tk.END, message)
            self.terminal_output.see(tk.END)
            self.terminal_output.config(state=tk.DISABLED)

        # Schedule on main thread
        self.root.after(0, append)

    def _clear_terminal(self):
        """Clear terminal output"""
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.delete(1.0, tk.END)
        self.terminal_output.config(state=tk.DISABLED)

    def _setup_build_tab(self):
        """Setup Build & Release tab"""
        # Header
        header = tk.Frame(self.build_tab, bg=COLORS["card"])
        header.pack(fill=tk.X, padx=20, pady=(20, 10))

        tk.Label(
            header,
            text="📦 Build & Release",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=15, pady=15)

        # Version Section
        version_frame = tk.Frame(self.build_tab, bg=COLORS["card"])
        version_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(
            version_frame,
            text="Version",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 5))

        version_inner = tk.Frame(version_frame, bg=COLORS["card"])
        version_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Current version display
        tk.Label(
            version_inner,
            text="Current:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg_dim"] if "fg_dim" in COLORS else COLORS["fg"],
        ).pack(side=tk.LEFT)

        self.current_version_label = tk.Label(
            version_inner,
            text=self._get_current_version(),
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        )
        self.current_version_label.pack(side=tk.LEFT, padx=(10, 30))

        # New version input
        tk.Label(
            version_inner,
            text="New Version:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        self.new_version_entry = tk.Entry(
            version_inner,
            font=FONTS["code"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=15,
        )
        self.new_version_entry.pack(side=tk.LEFT, padx=10)
        self.new_version_entry.insert(0, self._get_next_version())

        # Download link section (hidden by default)
        self.download_frame = tk.Frame(self.build_tab, bg=COLORS["card"])

        dl_inner = tk.Frame(self.download_frame, bg=COLORS["card"])
        dl_inner.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(
            dl_inner,
            text="📥 Download:",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.download_url_label = tk.Label(
            dl_inner,
            text="",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["accent"],
            cursor="hand2",
        )
        self.download_url_label.pack(side=tk.LEFT)
        self.download_url_label.bind("<Button-1>", lambda e: self._copy_download_url())

        ModernButton(
            dl_inner,
            text="📋 Copy",
            command=self._copy_download_url,
            kind="secondary",
            width=8,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Build Buttons
        buttons_frame = tk.Frame(self.build_tab, bg=COLORS["bg"])
        buttons_frame.pack(fill=tk.X, padx=20, pady=15)

        # Build App Button (Nuitka)
        self.build_app_btn = ModernButton(
            buttons_frame,
            text="🔨 Build App (Nuitka)",
            command=self._build_nuitka,
            kind="primary",
            font=FONTS["h2"],
            width=22,
        )
        self.build_app_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Build Installer Button
        self.build_installer_btn = ModernButton(
            buttons_frame,
            text="📦 Build Installer",
            command=self._build_installer,
            kind="success",
            font=FONTS["h2"],
            width=18,
        )
        self.build_installer_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Open Dist Folder Button
        ModernButton(
            buttons_frame,
            text="📂 Open Dist",
            command=self._open_dist_folder,
            kind="secondary",
            width=12,
        ).pack(side=tk.LEFT)

        # Progress Section
        progress_frame = tk.Frame(self.build_tab, bg=COLORS["card"])
        progress_frame.pack(fill=tk.X, padx=20, pady=10)

        progress_inner = tk.Frame(progress_frame, bg=COLORS["card"])
        progress_inner.pack(fill=tk.X, padx=15, pady=15)

        # Status label
        self.build_status_label = tk.Label(
            progress_inner,
            text="Ready to build",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.build_status_label.pack(anchor=tk.W)

        # Progress bar
        self.build_progress = ttk.Progressbar(
            progress_inner, mode="indeterminate", length=400
        )
        self.build_progress.pack(fill=tk.X, pady=(10, 0))

        # Build Output Log
        log_header = tk.Frame(self.build_tab, bg=COLORS["card"])
        log_header.pack(fill=tk.X, padx=20, pady=(10, 0))

        tk.Label(
            log_header,
            text="Build Output",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=10, pady=10)

        ModernButton(
            log_header,
            text="Clear",
            command=self._clear_build_log,
            kind="secondary",
            width=8,
        ).pack(side=tk.RIGHT, padx=10, pady=10)

        # Output text
        log_frame = tk.Frame(self.build_tab, bg=COLORS["input_bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.build_output = scrolledtext.ScrolledText(
            log_frame,
            font=FONTS["code"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            height=12,
        )
        self.build_output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.build_output.config(state=tk.DISABLED)

        # Build state
        self.build_running = False

    def _get_current_version(self):
        """Get current version from version.ini"""
        try:
            version_file = self.backend_dir / "version.ini"
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except:
            pass
        return "1.0.0"

    def _get_next_version(self):
        """Suggest next version (increment patch)"""
        current = self._get_current_version()
        try:
            parts = current.split(".")
            if len(parts) >= 3:
                parts[-1] = str(int(parts[-1]) + 1)
                return ".".join(parts)
        except:
            pass
        return current

    def _log_build(self, message, color=None):
        """Log message to build output"""

        def append():
            self.build_output.config(state=tk.NORMAL)
            self.build_output.insert(tk.END, message + "\n")
            self.build_output.see(tk.END)
            self.build_output.config(state=tk.DISABLED)

        self.root.after(0, append)

    def _clear_build_log(self):
        """Clear build output"""
        self.build_output.config(state=tk.NORMAL)
        self.build_output.delete(1.0, tk.END)
        self.build_output.config(state=tk.DISABLED)

    def _update_build_status(self, status, is_running=None):
        """Update build status label"""

        def update():
            self.build_status_label.config(text=status)
            if is_running is not None:
                self.build_running = is_running
                if is_running:
                    self.build_progress.start(10)
                    self.build_app_btn.config(state=tk.DISABLED)
                    self.build_installer_btn.config(state=tk.DISABLED)
                else:
                    self.build_progress.stop()
                    self.build_app_btn.config(state=tk.NORMAL)
                    self.build_installer_btn.config(state=tk.NORMAL)

        self.root.after(0, update)

    def _build_nuitka(self):
        """Run Nuitka build"""
        if self.build_running:
            return

        new_version = self.new_version_entry.get().strip()
        if not new_version:
            messagebox.showwarning("Warning", "Please enter a version number")
            return

        self._clear_build_log()
        self._update_build_status(f"Building app v{new_version}...", True)
        self._log_build(f"=== Building FourT v{new_version} with Nuitka ===\n")

        def run_build():
            try:
                # Clean dist folder before building
                dist_path = self.backend_dir / "dist"
                if dist_path.exists():
                    self._log_build(f"🗑️ Cleaning dist folder: {dist_path}")
                    try:
                        import shutil

                        shutil.rmtree(dist_path)
                        self._log_build("✅ dist folder deleted successfully\n")
                    except Exception as e:
                        self._log_build(
                            f"⚠️ Warning: Could not delete dist folder: {e}\n"
                        )

                script_path = self.backend_dir / "build_nuitka.ps1"
                if not script_path.exists():
                    self._log_build(
                        f"ERROR: build_nuitka.ps1 not found at {script_path}"
                    )
                    self._update_build_status("Build failed!", False)
                    return

                # Run PowerShell script with UTF-8 encoding
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                process = subprocess.Popen(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script_path),
                        "-NewVersion",
                        new_version,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.backend_dir),
                    env=env,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

                # Read output in binary and decode immediately for faster streaming
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        try:
                            text = line.decode("utf-8", errors="replace").rstrip()
                        except:
                            text = line.decode("cp1252", errors="replace").rstrip()
                        self._log_build(text)

                process.wait()

                if process.returncode == 0:
                    self._log_build("\n✅ Build completed successfully!")
                    self._update_build_status("Build completed!", False)
                    # Update current version display
                    self.root.after(
                        0, lambda: self.current_version_label.config(text=new_version)
                    )
                    self.root.after(0, lambda: self.new_version_entry.delete(0, tk.END))
                    self.root.after(
                        0,
                        lambda: self.new_version_entry.insert(
                            0, self._get_next_version()
                        ),
                    )
                else:
                    self._log_build(f"\n❌ Build failed with code {process.returncode}")
                    self._update_build_status("Build failed!", False)

            except Exception as e:
                self._log_build(f"\n❌ Error: {str(e)}")
                self._update_build_status("Build error!", False)

        threading.Thread(target=run_build, daemon=True).start()

    def _build_installer(self):
        """Run Inno Setup installer build"""
        if self.build_running:
            return

        self._clear_build_log()
        self._update_build_status("Building installer...", True)
        self._log_build("=== Building FourT Installer ===\n")

        def run_build():
            try:
                script_path = self.backend_dir / "build_installer.ps1"
                if not script_path.exists():
                    self._log_build(
                        f"ERROR: build_installer.ps1 not found at {script_path}"
                    )
                    self._update_build_status("Build failed!", False)
                    return

                # Run PowerShell script with UTF-8 encoding
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                process = subprocess.Popen(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script_path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.backend_dir),
                    env=env,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

                # Read output in binary and decode immediately for faster streaming
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        try:
                            text = line.decode("utf-8", errors="replace").rstrip()
                        except:
                            text = line.decode("cp1252", errors="replace").rstrip()
                        self._log_build(text)

                process.wait()

                if process.returncode == 0:
                    self._log_build("\n✅ Installer created successfully!")
                    self._update_build_status("Installer ready!", False)

                    # Show download link
                    public_url = os.getenv("PUBLIC_URL", "http://localhost:8000")
                    download_url = f"{public_url}/download/installer"
                    self.root.after(0, lambda: self._show_download_link(download_url))
                else:
                    self._log_build(f"\n❌ Build failed with code {process.returncode}")
                    self._update_build_status("Build failed!", False)

            except Exception as e:
                self._log_build(f"\n❌ Error: {str(e)}")
                self._update_build_status("Build error!", False)

        threading.Thread(target=run_build, daemon=True).start()

    def _show_download_link(self, download_url: str):
        """Show the download link in the UI"""
        self.download_url_label.config(text=download_url)
        self.download_url = download_url  # Store for copying
        self.download_frame.pack(
            fill=tk.X, padx=20, pady=(0, 10), after=self.new_version_entry.master.master
        )
        self._log_build(f"\n📥 Download URL: {download_url}")

    def _copy_download_url(self):
        """Copy download URL to clipboard"""
        if hasattr(self, "download_url") and self.download_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.download_url)
            self.root.update()  # Required for clipboard to work
            messagebox.showinfo(
                "Copied", f"Download URL copied to clipboard!\n\n{self.download_url}"
            )

    def _open_dist_folder(self):
        """Open dist folder in file explorer"""
        dist_path = self.backend_dir / "dist"
        if dist_path.exists():
            os.startfile(str(dist_path))
        else:
            messagebox.showinfo("Info", "dist folder doesn't exist yet. Build first!")

    def run(self):
        """Run the admin UI"""
        self.root.mainloop()

        # Cleanup on exit
        if self.server_running:
            self._stop_server()


def main():
    """Main entry point"""
    app = AdminWindow()
    app.run()


if __name__ == "__main__":
    main()
