"""
Quest Video Helper Window
Main window with settings UI and controls for Quest Video Helper
"""

import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
from typing import Optional
from services.quest_helper_settings import QuestHelperSettings
from services.ocr_addon_manager import OCRAddonManager
from services.video_popup_service import get_video_popup_service
from .theme import colors, FONTS, ModernButton
from .region_selector import RegionSelector
from .video_overlay_window import VideoOverlayWindow
from .ocr_setup_window import OCRSetupWindow
from .components import FramelessWindow
from .i18n import t


class QuestVideoHelperWindow:
    """
    Main Quest Video Helper window with settings and controls

    Layout:
    - Settings section (hotkey, search prefix/suffix, language, video size)
    - OCR Addon status section
    - Quick actions section
    """

    LANGUAGES = [
        ("English", "en"),
        ("Tiếng Việt", "vi"),
    ]

    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.settings = QuestHelperSettings()
        self.ocr_manager = OCRAddonManager()

        # Build engine maps dynamically
        self.engine_map_name_to_id = {}
        self.engine_map_id_to_name = {}
        for eid, info in self.ocr_manager.ENGINES.items():
            # Use simple name for dropdown if possible, or just the name field
            name = info.get("name", eid)
            # Strip extra info like size or stars for the dropdown?
            # The 'name' field in ENGINES has "EasyOCR ⭐", let's keep it or clean it?
            # Let's keep it as is for consistency with Setup window
            self.engine_map_name_to_id[name] = eid
            self.engine_map_id_to_name[eid] = name

        self.root: Optional[tk.Toplevel] = None
        self.video_overlay: Optional[VideoOverlayWindow] = None
        self.video_popup_service = get_video_popup_service()
        self._hotkey_registered = False
        self._is_selecting = False

        self._create_window()
        self._register_hotkey()

    def _create_window(self) -> None:
        """Create the main window using FramelessWindow"""
        import os

        # Get icon path
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "favicon.ico"
        )
        if not os.path.exists(icon_path):
            icon_path = None

        self.root = FramelessWindow(
            self.parent, title="Quest Video Helper", icon_path=icon_path
        )
        self.root.geometry("480x350")

        self._setup_ui()
        self._load_settings()

        # Override close to unregister hotkey
        self.root._original_close = self.root.close
        self.root.close = self._on_close

    def _setup_ui(self) -> None:
        """Setup UI elements inside FramelessWindow content_frame"""
        container = self.root.content_frame

        # Main content frame (no scroll needed for simple view)
        content = tk.Frame(container, bg=colors["bg"])
        content.pack(fill="both", expand=True, padx=15, pady=10)

        # === FLOW GUIDE QUOTE ===
        flow_quote = tk.Frame(
            content,
            bg=colors["card"],
            highlightthickness=2,
            highlightbackground=colors["accent"],
        )
        flow_quote.pack(fill="x", pady=(0, 15))

        # Left accent bar
        accent_bar = tk.Frame(flow_quote, bg=colors["accent"], width=4)
        accent_bar.pack(side="left", fill="y")

        quote_content = tk.Frame(flow_quote, bg=colors["card"])
        quote_content.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        tk.Label(
            quote_content,
            text=t("quest_quick_guide"),
            font=("Segoe UI", 11, "bold"),
            bg=colors["card"],
            fg=colors["accent"],
        ).pack(anchor="w")

        flow_text = (
            t("quest_step_1") + "\n" + t("quest_step_2") + "\n" + t("quest_step_3")
        )
        tk.Label(
            quote_content,
            text=flow_text,
            font=FONTS["body"],
            bg=colors["card"],
            fg=colors["fg"],
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # === MAIN ACTION BUTTON ===
        self.start_btn = self._create_big_button(
            content, t("start_select_region"), self.start_selection, colors["success"]
        )
        self.start_btn.pack(fill="x", pady=(0, 15))

        # Hotkey hint
        hotkey = self.settings.get("hotkey", "ctrl+shift+q")
        hotkey_hint = tk.Label(
            content,
            text=t("hotkey_label", hotkey=hotkey.upper()),
            font=FONTS["small"],
            bg=colors["bg"],
            fg=colors["fg_dim"],
        )
        hotkey_hint.pack(pady=(0, 15))
        self._hotkey_hint = hotkey_hint

        # === SETTINGS TOGGLE BUTTON ===
        settings_toggle_frame = tk.Frame(content, bg=colors["bg"])
        settings_toggle_frame.pack(fill="x", pady=(0, 5))

        self._settings_visible = False

        settings_toggle = tk.Label(
            settings_toggle_frame,
            text=t("settings"),
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["fg"],
            cursor="hand2",
            padx=12,
            pady=6,
        )
        settings_toggle.pack(side="left")

        self._settings_arrow = tk.Label(
            settings_toggle_frame,
            text="▼",
            font=("Segoe UI", 8),
            bg=colors["bg"],
            fg=colors["fg_dim"],
        )
        self._settings_arrow.pack(side="left", padx=(5, 0))

        def toggle_settings(e=None):
            self._settings_visible = not self._settings_visible
            if self._settings_visible:
                self._settings_panel.pack(fill="x", pady=(5, 10))
                self._settings_arrow.config(text="▲")
                # Expand window height
                self.root.geometry("480x580")
            else:
                self._settings_panel.pack_forget()
                self._settings_arrow.config(text="▼")
                # Shrink window height
                self.root.geometry("480x350")

        settings_toggle.bind("<Button-1>", toggle_settings)
        settings_toggle.bind(
            "<Enter>", lambda e: settings_toggle.config(bg=colors["card_hover"])
        )
        settings_toggle.bind(
            "<Leave>", lambda e: settings_toggle.config(bg=colors["card"])
        )

        # === COLLAPSIBLE SETTINGS PANEL (hidden scroll) ===
        self._settings_panel = tk.Frame(
            content,
            bg=colors["card"],
            highlightthickness=1,
            highlightbackground=colors["border"],
        )
        # Don't pack yet - hidden by default

        # Scrollable container (hidden scrollbar)
        settings_canvas = tk.Canvas(
            self._settings_panel, bg=colors["card"], highlightthickness=0, height=280
        )
        settings_inner = tk.Frame(settings_canvas, bg=colors["card"])

        settings_inner.bind(
            "<Configure>",
            lambda e: settings_canvas.configure(
                scrollregion=settings_canvas.bbox("all")
            ),
        )

        # Create window and store ID for resizing
        settings_window_id = settings_canvas.create_window(
            (0, 0), window=settings_inner, anchor="nw"
        )
        settings_canvas.pack(fill="both", expand=True, padx=5, pady=10)

        # Auto-resize inner window when canvas resizes
        def on_canvas_resize(event):
            settings_canvas.itemconfig(settings_window_id, width=event.width - 10)

        settings_canvas.bind("<Configure>", on_canvas_resize)

        # Mouse wheel scroll (hidden scrollbar)
        def _on_settings_scroll(event):
            settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        settings_canvas.bind(
            "<Enter>",
            lambda e: settings_canvas.bind_all("<MouseWheel>", _on_settings_scroll),
        )
        settings_canvas.bind(
            "<Leave>", lambda e: settings_canvas.unbind_all("<MouseWheel>")
        )

        # Hotkey row
        self._create_settings_row(settings_inner, t("hotkey"))
        hotkey_row = tk.Frame(settings_inner, bg=colors["card"])
        hotkey_row.pack(fill="x", pady=(0, 8))

        self.hotkey_entry = self._create_entry(hotkey_row, width=15)
        self.hotkey_entry.pack(side="left")

        record_btn = self._create_icon_button(
            hotkey_row, "⏺", self._record_hotkey, colors["warning"]
        )
        record_btn.pack(side="left", padx=(8, 0))

        # Search prefix/suffix
        self._create_settings_row(settings_inner, t("search_prefix"))
        self.prefix_entry = self._create_entry(settings_inner, width=28)
        self.prefix_entry.pack(fill="x", pady=(0, 8))

        self._create_settings_row(settings_inner, t("search_suffix"))
        self.suffix_entry = self._create_entry(settings_inner, width=28)
        self.suffix_entry.pack(fill="x", pady=(0, 8))

        # Language
        self._create_settings_row(settings_inner, t("language"))
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(
            settings_inner,
            textvariable=self.lang_var,
            values=[lang[0] for lang in self.LANGUAGES],
            state="readonly",
            width=20,
        )
        self.lang_combo.pack(anchor="w", pady=(0, 8))

        # Video size
        self._create_settings_row(settings_inner, t("video_size"))
        size_row = tk.Frame(settings_inner, bg=colors["card"])
        size_row.pack(fill="x", pady=(0, 8))

        self.width_entry = self._create_entry(size_row, width=6)
        self.width_entry.pack(side="left")
        tk.Label(
            size_row,
            text=" × ",
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["fg_dim"],
        ).pack(side="left")
        self.height_entry = self._create_entry(size_row, width=6)
        self.height_entry.pack(side="left")
        tk.Label(
            size_row,
            text=" px",
            font=FONTS["small"],
            bg=colors["card"],
            fg=colors["fg_dim"],
        ).pack(side="left")

        # Auto play toggle
        self.autoplay_var = tk.BooleanVar(value=True)
        autoplay_row = tk.Frame(settings_inner, bg=colors["card"])
        autoplay_row.pack(fill="x", pady=(0, 8))
        self._create_toggle(autoplay_row, t("auto_play_video"), self.autoplay_var)

        # OCR Engine section - separator
        tk.Frame(settings_inner, bg=colors["border"], height=1).pack(
            fill="x", pady=(5, 10)
        )

        # OCR row with engine and setup button
        ocr_header = tk.Frame(settings_inner, bg=colors["card"])
        ocr_header.pack(fill="x", pady=(0, 8))

        tk.Label(
            ocr_header,
            text="OCR Engine:",
            font=FONTS["body"],
            bg=colors["card"],
            fg=colors["fg"],
        ).pack(side="left")

        self.engine_var = tk.StringVar()

        # Use keys from map (the Names) for values
        engine_values = list(self.engine_map_name_to_id.keys())

        self.engine_combo = ttk.Combobox(
            ocr_header,
            textvariable=self.engine_var,
            values=engine_values,
            state="readonly",
            width=20,
        )
        self.engine_combo.pack(side="left", padx=(10, 0))
        self.engine_combo.bind("<<ComboboxSelected>>", self._on_engine_changed)

        # Setup button on same row
        self.ocr_btn = tk.Label(
            ocr_header,
            text="⚙",
            font=("Segoe UI", 12),
            bg=colors["card"],
            fg=colors["accent"],
            cursor="hand2",
        )
        self.ocr_btn.pack(side="right")
        self.ocr_btn.bind("<Button-1>", lambda e: self._open_ocr_setup())
        self.ocr_btn.bind(
            "<Enter>", lambda e: self.ocr_btn.config(fg=colors["warning"])
        )
        self.ocr_btn.bind("<Leave>", lambda e: self.ocr_btn.config(fg=colors["accent"]))

        # OCR Status - simple display
        ocr_status_row = tk.Frame(settings_inner, bg=colors["card"])
        ocr_status_row.pack(fill="x", pady=(0, 10))

        self.ocr_status_indicator = tk.Label(
            ocr_status_row,
            text="●",
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["success"],
        )
        self.ocr_status_indicator.pack(side="left")

        self.ocr_status_label = tk.Label(
            ocr_status_row,
            text=t("ocr_ready"),
            font=FONTS["small"],
            bg=colors["card"],
            fg=colors["fg"],
        )
        self.ocr_status_label.pack(side="left", padx=(3, 0))

        # Save button - full width at bottom
        save_btn = tk.Label(
            settings_inner,
            text=t("save_settings"),
            font=("Segoe UI", 11, "bold"),
            bg=colors["accent"],
            fg="white",
            cursor="hand2",
            pady=10,
        )
        save_btn.pack(fill="x", pady=(5, 0))

        def save_enter(e):
            save_btn.config(bg="#5a9cf8")

        def save_leave(e):
            save_btn.config(bg=colors["accent"])

        def save_click(e):
            save_btn.config(bg=colors["success"])
            save_btn.after(100, lambda: save_btn.config(bg=colors["accent"]))
            self._save_settings()

        save_btn.bind("<Enter>", save_enter)
        save_btn.bind("<Leave>", save_leave)
        save_btn.bind("<Button-1>", save_click)

        self._update_ocr_status()

    def _create_settings_row(self, parent, label: str) -> None:
        """Create a compact label for settings"""
        tk.Label(
            parent,
            text=label,
            font=FONTS["small"],
            bg=colors["card"],
            fg=colors["fg_dim"],
        ).pack(anchor="w", pady=(0, 2))

    def _create_card(self, parent, title: str, accent: bool = False) -> tk.Frame:
        """Create a modern card container with title"""
        card = tk.Frame(
            parent,
            bg=colors["card"],
            highlightthickness=1,
            highlightbackground=colors["accent"] if accent else colors["border"],
        )
        card.pack(fill="x", padx=15, pady=8)

        # Card header
        header = tk.Frame(card, bg=colors["card"])
        header.pack(fill="x", padx=15, pady=(12, 8))

        tk.Label(
            header,
            text=title,
            font=FONTS["h2"],
            bg=colors["card"],
            fg=colors["accent"] if accent else colors["fg"],
        ).pack(side="left")

        return card

    def _create_row(self, parent, label: str) -> None:
        """Create a labeled row"""
        row = tk.Frame(parent, bg=colors["card"])
        row.pack(fill="x", padx=15, pady=(0, 4))
        tk.Label(
            row, text=label, font=FONTS["small"], bg=colors["card"], fg=colors["fg_dim"]
        ).pack(side="left")

    def _create_entry(self, parent, width: int = 20) -> tk.Entry:
        """Create a styled entry field"""
        entry = tk.Entry(
            parent,
            font=FONTS["body"],
            bg=colors["input_bg"],
            fg=colors["fg"],
            insertbackground=colors["fg"],
            width=width,
            relief="flat",
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=colors["accent"],
        )
        return entry

    def _create_icon_button(self, parent, icon: str, command, color: str) -> tk.Label:
        """Create an icon button with hover effect"""
        btn = tk.Label(
            parent,
            text=icon,
            font=("Segoe UI Emoji", 14),
            bg=colors["card"],
            fg=color,
            cursor="hand2",
            padx=8,
            pady=2,
        )
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg=colors["card_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=colors["card"]))
        return btn

    def _create_toggle(self, parent, text: str, var: tk.BooleanVar) -> None:
        """Create a modern toggle checkbox"""
        cb = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            font=FONTS["body"],
            bg=colors["card"],
            fg=colors["fg"],
            selectcolor=colors["input_bg"],
            activebackground=colors["card"],
            activeforeground=colors["fg"],
            cursor="hand2",
        )
        cb.pack(side="left")

    def _create_big_button(self, parent, text: str, command, color: str) -> tk.Label:
        """Create a big action button with hover animation"""
        btn = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 13, "bold"),
            bg=color,
            fg="white",
            cursor="hand2",
            pady=12,
        )
        btn.bind("<Button-1>", lambda e: command())

        # Hover effect - brighten
        def on_enter(e):
            btn.config(bg=colors.get("success_hover", "#27ae60"))

        def on_leave(e):
            btn.config(bg=color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _load_settings(self) -> None:
        """Load settings into UI"""
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.insert(0, self.settings.get("hotkey"))

        self.prefix_entry.delete(0, tk.END)
        self.prefix_entry.insert(0, self.settings.get("search_prefix"))

        self.suffix_entry.delete(0, tk.END)
        self.suffix_entry.insert(0, self.settings.get("search_suffix"))

        # Language
        lang_code = self.settings.get("language")
        for name, code in self.LANGUAGES:
            if code == lang_code:
                self.lang_var.set(name)
                break

        # OCR Engine
        engine_code = self.settings.get("ocr_engine", "windows")
        # Default to Windows OCR if unknown
        default_name = self.engine_map_id_to_name.get("windows", "Windows OCR")
        self.engine_var.set(self.engine_map_id_to_name.get(engine_code, default_name))

        self.width_entry.delete(0, tk.END)
        self.width_entry.insert(0, str(self.settings.get("video_width")))

        self.height_entry.delete(0, tk.END)
        self.height_entry.insert(0, str(self.settings.get("video_height")))

        self.autoplay_var.set(self.settings.get("auto_play"))

    def _save_settings(self) -> None:
        """Save settings from UI"""
        # Get language code
        lang_name = self.lang_var.get()
        lang_code = "en"
        for name, code in self.LANGUAGES:
            if name == lang_name:
                lang_code = code
                break

        # Validate video size
        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
        except ValueError:
            messagebox.showerror(t("error"), t("video_size_number"))
            return

        # Update settings
        old_hotkey = self.settings.get("hotkey")
        new_hotkey = self.hotkey_entry.get().strip().lower()

        # Get OCR engine code
        engine_name = self.engine_var.get()
        engine_code = self.engine_map_name_to_id.get(engine_name, "windows")

        self.settings.set("hotkey", new_hotkey)
        self.settings.set("search_prefix", self.prefix_entry.get())
        self.settings.set("search_suffix", self.suffix_entry.get())
        self.settings.set("language", lang_code)
        self.settings.set("video_width", width)
        self.settings.set("video_height", height)
        self.settings.set("auto_play", self.autoplay_var.get())
        self.settings.set("ocr_engine", engine_code)

        if self.settings.save():
            # Re-register hotkey if changed
            if old_hotkey != new_hotkey:
                self._unregister_hotkey()
                self._register_hotkey()

            messagebox.showinfo(t("success"), t("settings_saved"))
        else:
            messagebox.showerror(t("error"), t("cannot_save_settings"))

    def _record_hotkey(self) -> None:
        """Record a new hotkey"""
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.insert(0, t("press_key"))
        self.hotkey_entry.focus_set()

        def on_key(event):
            # Build hotkey string
            parts = []
            if event.state & 0x4:  # Control
                parts.append("ctrl")
            if event.state & 0x1:  # Shift
                parts.append("shift")
            if event.state & 0x8:  # Alt
                parts.append("alt")

            key = event.keysym.lower()
            if key not in (
                "control_l",
                "control_r",
                "shift_l",
                "shift_r",
                "alt_l",
                "alt_r",
            ):
                parts.append(key)

            if parts:
                hotkey = "+".join(parts)
                self.hotkey_entry.delete(0, tk.END)
                self.hotkey_entry.insert(0, hotkey)

            self.root.unbind("<KeyPress>")
            return "break"

        self.root.bind("<KeyPress>", on_key)

    def _get_selected_engine_id(self) -> str:
        """Get currently selected engine ID"""
        engine_name = self.engine_var.get()
        return self.engine_map_name_to_id.get(engine_name, "windows")

    def _on_engine_changed(self, event=None) -> None:
        """Handle engine selection change"""
        self._update_ocr_status()

    def _update_ocr_status(self) -> None:
        """Update OCR engine status display"""
        engine_id = self._get_selected_engine_id()
        is_ready, status = self.ocr_manager.get_status(engine_id)

        self.ocr_status_label.config(text=f"Trạng thái: {status}")

        if is_ready:
            self.ocr_status_label.config(fg=colors["success"])
            self.ocr_btn.config(text="Sẵn sàng", state="disabled")
        else:
            self.ocr_status_label.config(fg=colors["warning"])
            self.ocr_btn.config(text="Cài đặt", state="normal")

    def _open_ocr_setup(self) -> None:
        """Open OCR setup window"""
        engine_id = self._get_selected_engine_id()

        def on_ready():
            self._update_ocr_status()

        OCRSetupWindow(self.root, on_ready=on_ready, selected_engine=engine_id)

    def _register_hotkey(self) -> None:
        """Register global hotkey"""
        if self._hotkey_registered:
            return

        hotkey = self.settings.get("hotkey")
        if not hotkey:
            return

        try:
            keyboard.add_hotkey(hotkey, self._on_hotkey_pressed, suppress=True)
            self._hotkey_registered = True
            print(f"[QuestVideoHelper] Registered hotkey: {hotkey}")
        except Exception as e:
            print(f"[QuestVideoHelper] Failed to register hotkey: {e}")

    def _unregister_hotkey(self) -> None:
        """Unregister global hotkey"""
        if not self._hotkey_registered:
            return

        try:
            keyboard.unhook_all_hotkeys()
            self._hotkey_registered = False
        except Exception as e:
            print(f"[QuestVideoHelper] Failed to unregister hotkey: {e}")

    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press"""
        # Safety check: ensure window is still valid
        if not self._is_window_valid():
            return
        # Use after() to run in main thread
        self.root.after(0, self.start_selection)

    def start_selection(self) -> None:
        """Start region selection"""
        if self._is_selecting:
            return

        # Check OCR addon
        if not self.ocr_manager.is_installed():

            def on_ready():
                self._update_ocr_status()
                self._start_region_selector()

            OCRSetupWindow(self.root, on_ready=on_ready)
            return

        self._start_region_selector()

    def _is_window_valid(self) -> bool:
        """Check if the root window still exists and is valid"""
        try:
            if not self.root:
                return False
            # Try to access the window - will raise TclError if destroyed
            self.root.winfo_exists()
            return True
        except Exception:
            return False

    def _start_region_selector(self) -> None:
        """Show region selector overlay"""
        # Safety check: ensure window is still valid
        if not self._is_window_valid():
            print(
                "[QuestVideoHelper] Window no longer valid, aborting region selection"
            )
            return

        self._is_selecting = True

        # Minimize our window
        self.root.withdraw()

        def on_select(x, y, w, h):
            self._is_selecting = False
            if self._is_window_valid():
                self.root.deiconify()
            self._process_region(x, y, w, h)

        def on_cancel():
            self._is_selecting = False
            if self._is_window_valid():
                self.root.deiconify()

        selector = RegionSelector(
            self.parent,
            on_select=on_select,
            on_cancel=on_cancel,
            instruction_text="Kéo chuột để chọn vùng chứa tên quest",
        )
        selector.show()

    def _process_region(self, x: int, y: int, w: int, h: int) -> None:
        """Process selected region: OCR -> Open YouTube and auto-play first video"""
        # OCR with selected engine
        engine_id = self._get_selected_engine_id()
        quest_name = self.ocr_manager.extract_text_from_region(x, y, w, h, engine_id)

        if not quest_name:
            messagebox.showwarning(
                "Không tìm thấy text",
                "Không thể đọc text từ vùng đã chọn.\nHãy thử chọn lại vùng khác.",
            )
            return

        print(f"[QuestVideoHelper] Raw OCR result: {quest_name}")

        # Clean OCR text: remove special chars, numbers, keep meaningful text
        import re

        clean_name = quest_name
        # Remove special characters but keep basic punctuation and Chinese chars
        clean_name = re.sub(r'[/\\|<>:"\[\]{}()!@#$%^&*+=~`]', " ", clean_name)
        # Remove standalone numbers and short garbage
        clean_name = re.sub(r"\b\d+\b", "", clean_name)
        # Remove extra whitespace
        clean_name = " ".join(clean_name.split())
        # Limit to reasonable length (first 50 chars for search)
        if len(clean_name) > 50:
            clean_name = clean_name[:50].rsplit(" ", 1)[0]  # Cut at word boundary

        if not clean_name or len(clean_name) < 3:
            messagebox.showwarning(
                "Text không hợp lệ",
                f"OCR đọc được: '{quest_name}'\nNhưng không đủ text để search.\nHãy thử chọn vùng khác.",
            )
            return

        print(f"[QuestVideoHelper] Cleaned quest name: {clean_name}")

        # Save selection position for video popup
        self._last_selection = (x, y, w, h)

        # Build search query using settings
        search_query = self.settings.get_search_query(clean_name)
        print(f"[QuestVideoHelper] Search query: {search_query}")

        # Open YouTube search in browser popup
        popup_width = self.settings.get("video_width", 480)
        popup_height = self.settings.get("video_height", 360)

        if hasattr(self, "_last_selection") and self._last_selection:
            popup_x, popup_y = self.video_popup_service.calculate_popup_position(
                self._last_selection,
                popup_width,
                popup_height,
                self.root.winfo_screenwidth(),
                self.root.winfo_screenheight(),
            )
        else:
            popup_x, popup_y = 100, 100

        # Open loading page which will search and redirect to video
        self._open_video_loading_page(
            search_query, popup_x, popup_y, popup_width, popup_height
        )

    def _open_video_loading_page(
        self, search_query: str, x: int, y: int, width: int, height: int
    ) -> None:
        """Open the video loading page that shows animation while searching"""
        import urllib.parse
        from core.config import refresh_server_url

        # Get server URL
        server_url = refresh_server_url()
        if not server_url:
            # Fallback: open YouTube search directly
            encoded_query = urllib.parse.quote_plus(search_query)
            fallback_url = (
                f"https://www.youtube.com/results?search_query={encoded_query}"
            )
            self.video_popup_service.open_video_popup(
                url=fallback_url,
                title=f"Search: {search_query[:30]}",
                x=x,
                y=y,
                width=width + 200,
                height=height + 100,
            )
            return

        # Open loading page URL
        encoded_query = urllib.parse.quote_plus(search_query)
        loading_url = f"{server_url}/api/youtube/player?q={encoded_query}"

        print(f"[QuestVideoHelper] Opening loading page: {loading_url}")

        self.video_popup_service.open_video_popup(
            url=loading_url,
            title=f"Quest: {search_query[:30]}",
            x=x,
            y=y,
            width=width,
            height=height,
        )

    def _open_first_video_async(
        self, search_query: str, x: int, y: int, width: int, height: int
    ) -> None:
        """Search and open first video asynchronously with loading indicator"""
        import threading

        # Show loading indicator
        loading_popup = None
        try:
            loading_popup = self._show_loading_popup(
                "🔍 Đang tìm video...", search_query[:50]
            )
        except Exception as e:
            print(f"[QuestVideoHelper] Could not show loading: {e}")

        def search_and_open():
            try:
                # Use server API to get first video URL
                first_video_url = self._search_first_video(search_query)

                # Close loading popup
                if loading_popup:
                    try:
                        self.root.after(0, loading_popup.destroy)
                    except:
                        pass

                if first_video_url:
                    # Open in popup with autoplay
                    self.root.after(
                        0,
                        lambda: self.video_popup_service.open_video_popup(
                            url=first_video_url,
                            title=f"Quest: {search_query[:30]}",
                            x=x,
                            y=y,
                            width=width,
                            height=height,
                        ),
                    )
                else:
                    # Fallback: open search page
                    import urllib.parse

                    encoded_query = urllib.parse.quote_plus(search_query)
                    fallback_url = (
                        f"https://www.youtube.com/results?search_query={encoded_query}"
                    )
                    self.root.after(
                        0,
                        lambda: self.video_popup_service.open_video_popup(
                            url=fallback_url,
                            title=f"Search: {search_query[:30]}",
                            x=x,
                            y=y,
                            width=width + 200,
                            height=height + 100,
                        ),
                    )
            except Exception as e:
                print(f"[QuestVideoHelper] Error searching video: {e}")
                # Close loading on error
                if loading_popup:
                    try:
                        self.root.after(0, loading_popup.destroy)
                    except:
                        pass

        thread = threading.Thread(target=search_and_open, daemon=True)
        thread.start()

    def _show_loading_popup(self, title: str, subtitle: str) -> tk.Toplevel:
        """Show a small loading popup near cursor"""
        popup = tk.Toplevel(self.parent)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=colors["card"])

        # Position near center of screen
        screen_w = self.parent.winfo_screenwidth()
        screen_h = self.parent.winfo_screenheight()
        popup_w, popup_h = 250, 80
        x = (screen_w - popup_w) // 2
        y = (screen_h - popup_h) // 2
        popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")

        # Border effect
        popup.configure(highlightthickness=2, highlightbackground=colors["accent"])

        # Content
        tk.Label(
            popup,
            text=title,
            font=("Segoe UI", 12, "bold"),
            bg=colors["card"],
            fg=colors["accent"],
        ).pack(pady=(15, 5))

        tk.Label(
            popup,
            text=subtitle,
            font=("Segoe UI", 9),
            bg=colors["card"],
            fg=colors["fg_dim"],
        ).pack()

        popup.update()
        return popup

    def _search_first_video(self, query: str) -> str:
        """Search YouTube via server API and return first video URL"""
        try:
            import requests
            import urllib.parse
            from core.config import refresh_server_url

            # Get current server URL
            server_url = refresh_server_url()
            if not server_url:
                print("[QuestVideoHelper] No server URL available")
                return ""

            # Call server API
            encoded_query = urllib.parse.quote_plus(query)
            api_url = f"{server_url}/api/youtube/search?q={encoded_query}&limit=1"

            print(f"[QuestVideoHelper] Calling API: {api_url}")

            response = requests.get(api_url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                first_video_url = data.get("first_video_url", "")
                if first_video_url:
                    print(f"[QuestVideoHelper] Got video URL: {first_video_url}")
                    return first_video_url

            print(f"[QuestVideoHelper] API returned status: {response.status_code}")
            return ""
        except Exception as e:
            print(f"[QuestVideoHelper] API search error: {e}")
            return ""

    def _show_video(self, video: dict) -> None:
        """Open video in browser popup near selection region"""
        video_url = video.get("url", "")
        title = video.get("title", "Video")

        # Get settings
        popup_width = self.settings.get("video_width", 480)
        popup_height = self.settings.get("video_height", 360)

        # Calculate position near selection
        if hasattr(self, "_last_selection") and self._last_selection:
            popup_x, popup_y = self.video_popup_service.calculate_popup_position(
                self._last_selection,
                popup_width,
                popup_height,
                self.root.winfo_screenwidth(),
                self.root.winfo_screenheight(),
            )
        else:
            popup_x, popup_y = 100, 100

        # Open popup using service
        self.video_popup_service.open_video_popup(
            url=video_url,
            title=title,
            x=popup_x,
            y=popup_y,
            width=popup_width,
            height=popup_height,
        )

    def _download_and_play(self, video: dict, width: int, height: int) -> None:
        """Download video and play locally"""
        # Show loading popup
        loading_window = self._show_loading(
            "🔄 Đang chuẩn bị video...", "Vui lòng đợi..."
        )

        def on_progress(status: str, percent: int):
            try:
                loading_window.children.get("!label2", loading_window).config(
                    text=f"{status} ({percent}%)"
                )
            except:
                pass

        def on_download_complete(video_path: Optional[str]):
            try:
                loading_window.destroy()
            except:
                pass

            if video_path:
                self.root.after(
                    0,
                    lambda: self._show_local_video(
                        video_path, video.get("title", "Video Guide"), width, height
                    ),
                )
            else:
                # Fallback: open in browser
                print(f"[QuestVideoHelper] Download failed, opening in browser")
                import webbrowser

                webbrowser.open(video["url"])

        self.youtube_service.download_video_async(
            video["url"],
            progress_callback=on_progress,
            on_complete=on_download_complete,
        )

    def _show_loading(self, title: str, message: str) -> tk.Toplevel:
        """Show a loading popup window"""
        loading = tk.Toplevel(self.root)
        loading.title(title)
        loading.geometry("300x100")
        loading.configure(bg=colors["bg"])
        loading.resizable(False, False)
        loading.attributes("-topmost", True)

        # Set icon
        from .theme import set_window_icon

        set_window_icon(loading)

        # Center
        loading.update_idletasks()
        x = (loading.winfo_screenwidth() - 300) // 2
        y = (loading.winfo_screenheight() - 100) // 2
        loading.geometry(f"+{x}+{y}")

        tk.Label(
            loading, text=title, font=FONTS["h2"], bg=colors["bg"], fg=colors["accent"]
        ).pack(pady=(20, 5))

        tk.Label(
            loading,
            text=message,
            font=FONTS["body"],
            bg=colors["bg"],
            fg=colors["fg"],
            name="loading_status",
        ).pack(pady=5)

        return loading

    def _show_local_video(
        self, video_path: str, title: str, width: int, height: int
    ) -> None:
        """Show local video file in overlay"""
        self.video_overlay = VideoOverlayWindow(
            video_url=video_path,  # Local path
            title=title,
            width=width,
            height=height,
            autoplay=True,
            embed_html=None,
            is_local=True,  # Flag for local video
        )
        self.video_overlay.show()

    def _show_help(self) -> None:
        """Show help dialog"""
        help_text = """
🎯 Quest Video Helper

Cách sử dụng:
1. Nhấn phím tắt (mặc định: Ctrl+Shift+Q)
2. Kéo chuột để chọn vùng chứa tên quest
3. Hệ thống sẽ tự động:
   - Đọc tên quest từ màn hình
   - Tìm video hướng dẫn trên YouTube
   - Hiển thị video trong overlay

Cài đặt:
- Phím tắt: Tùy chỉnh phím để kích hoạt
- Tiền tố/Hậu tố: Thêm vào câu tìm kiếm
- Kích thước video: Thay đổi kích thước overlay

Lưu ý:
- Cần cài OCR Addon trước khi sử dụng
- Cần kết nối internet để tìm video
        """

        messagebox.showinfo("Hướng dẫn", help_text.strip())

    def _on_close(self) -> None:
        """Handle window close"""
        self._unregister_hotkey()

        if self.video_overlay and self.video_overlay.is_open:
            self.video_overlay.close()

        if self.root:
            self.root.destroy()
            self.root = None

    def show(self) -> None:
        """Show the window"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
