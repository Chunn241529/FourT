"""
Screen Translator Window
Main UI for screen translation feature with 2 modes:
1. Capture Once - Take screenshot, OCR, translate once
2. Real-time - Continuously OCR + translate selected region
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import json
from typing import Optional, Tuple
from pathlib import Path
from .components import FramelessWindow
from .region_selector import RegionSelector
from services.ocr_addon_manager import OCRAddonManager
from services.translation_service import get_translation_service, TranslationService
from .theme import colors, FONTS, ModernButton
from .i18n import t
from .story_log_window import StoryLogWindow


class TranslationOverlay(tk.Toplevel):
    """Floating overlay to display translated text - soft, minimal design"""

    def __init__(self, parent, on_stop=None, on_show_log=None):
        super().__init__(parent)

        self.on_stop = on_stop  # Callback for stop button
        self.on_show_log = on_show_log  # Callback for log button

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        # Soft dark background - no harsh borders
        self.bg_color = "#1a1d21"
        self.accent_color = "#7eb8da"
        self.text_color = "#f0f3f6"
        self.muted_color = "#8b949e"
        self.configure(bg=self.bg_color)

        # Main frame - no border, just padding for soft edges
        self.main_frame = tk.Frame(
            self,
            bg=self.bg_color,
            highlightthickness=0,  # No outline
        )
        self.main_frame.pack(fill="both", expand=True)

        # Content with generous padding for soft look
        self.content = tk.Frame(self.main_frame, bg=self.bg_color, padx=16, pady=12)
        self.content.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self.content, bg=self.bg_color)
        header.pack(fill="x", pady=(0, 8))

        self.title_label = tk.Label(
            header,
            text=f"🌐 {t('st_translate')}",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.muted_color,
        )
        self.title_label.pack(side="left")

        # Buttons frame (right side) - subtle
        btn_frame = tk.Frame(header, bg=self.bg_color)
        btn_frame.pack(side="right")

        # Log button - scroll icon
        self.log_btn = tk.Label(
            btn_frame,
            text="📜",
            font=("Segoe UI", 11),
            bg=self.bg_color,
            fg="#a8b8d0",  # Light blue-ish
            cursor="hand2",
        )
        self.log_btn.pack(side="left", padx=(0, 12))
        self.log_btn.bind("<Button-1>", lambda e: self._on_log_click())
        self.log_btn.bind("<Enter>", lambda e: self.log_btn.configure(fg="#ffffff"))
        self.log_btn.bind("<Leave>", lambda e: self.log_btn.configure(fg="#a8b8d0"))

        # Stop button - subtle
        self.stop_btn = tk.Label(
            btn_frame,
            text="⏹",
            font=("Segoe UI", 11),
            bg=self.bg_color,
            fg="#e09956",
            cursor="hand2",
        )
        self.stop_btn.pack(side="left", padx=(0, 12))
        self.stop_btn.bind("<Button-1>", self._on_stop_click)
        self.stop_btn.bind("<Enter>", lambda e: self.stop_btn.configure(fg="#ffa657"))
        self.stop_btn.bind("<Leave>", lambda e: self.stop_btn.configure(fg="#e09956"))

        # Close button - subtle X
        self.close_btn = tk.Label(
            btn_frame,
            text="×",
            font=("Segoe UI", 14),
            bg=self.bg_color,
            fg=self.muted_color,
            cursor="hand2",
        )
        self.close_btn.pack(side="left")
        self.close_btn.bind("<Button-1>", lambda e: self.hide())
        self.close_btn.bind(
            "<Enter>", lambda e: self.close_btn.configure(fg=self.text_color)
        )
        self.close_btn.bind(
            "<Leave>", lambda e: self.close_btn.configure(fg=self.muted_color)
        )

        # Text display
        self.text_label = tk.Label(
            self.content,
            text="",
            font=("Segoe UI", 11),
            bg=self.bg_color,
            fg=self.text_color,
            wraplength=350,
            justify="left",
            anchor="nw",
        )
        self.text_label.pack(fill="both", expand=True)
        self.text_label.bind("<ButtonPress-1>", self._start_drag)
        self.text_label.bind("<B1-Motion>", self._do_drag)

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        # Initially hidden
        self.withdraw()

    def _on_stop_click(self, event):
        """Handle stop button click"""
        # Show feedback
        self.text_label.configure(text=t("st_stopped"), fg="#f0883e")
        self.title_label.configure(text="🌐 Stopped")

        if self.on_stop:
            self.on_stop()

        # Hide after short delay
        self.after(1500, self.hide)

    def _on_log_click(self):
        """Handle log button click"""
        if self.on_show_log:
            self.on_show_log()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    def show_text(self, original: str, translated: str, source_lang: str = ""):
        """Show translated text in overlay"""
        # Reset colors to default
        self.text_label.configure(text=translated, fg=self.text_color)
        self.title_label.configure(text="🌐 Dịch", fg=self.muted_color)

        if source_lang:
            lang_name = TranslationService.get_language_name(source_lang)
            self.title_label.configure(text=f"🌐 {lang_name} → Vietnamese")

        self.deiconify()
        self.lift()

    def hide(self):
        """Hide overlay"""
        self.withdraw()

    def position_near_region(self, x: int, y: int, w: int, h: int):
        """Position overlay near the selected region"""
        # Position below the region
        overlay_x = x
        overlay_y = y + h + 10

        # Keep on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        self.update_idletasks()
        overlay_w = max(300, self.winfo_reqwidth())
        overlay_h = self.winfo_reqheight()

        if overlay_x + overlay_w > screen_w:
            overlay_x = screen_w - overlay_w - 10
        if overlay_y + overlay_h > screen_h:
            overlay_y = y - overlay_h - 10  # Above the region

        self.geometry(f"+{overlay_x}+{overlay_y}")


class ScreenTranslatorWindow:
    """Main screen translator window"""

    SETTINGS_FILE = "screen_translator_settings.json"

    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.ocr_manager = OCRAddonManager()
        self.translation_service = get_translation_service()

        # State
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.is_realtime_running = False
        self._realtime_thread: Optional[threading.Thread] = None
        self._stop_realtime = False
        self._last_text = ""

        # Settings (defaults)
        self.realtime_interval = 1500  # ms
        self.source_lang = "auto"
        self.target_lang = "vi"

        # Load saved settings
        self._settings = self._load_settings()

        # UI
        self.root: Optional[FramelessWindow] = None
        self.overlay: Optional[TranslationOverlay] = None
        self.story_log: Optional[StoryLogWindow] = None

        self._create_window()

    def _get_settings_path(self):
        """Get settings file path"""
        import os

        settings_dir = Path(os.path.expanduser("~")) / ".fourt"
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / self.SETTINGS_FILE

    def _load_settings(self) -> dict:
        """Load settings from file"""

        try:
            path = self._get_settings_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    print(f"[ScreenTranslator] Loaded settings: {settings}")
                    return settings
        except Exception as e:
            print(f"[ScreenTranslator] Failed to load settings: {e}")

        # Defaults
        return {
            "source_lang": "auto",
            "target_lang": "vi",
            "ocr_engine": "windows",
            "skip_first_line": True,
            "ocr_engine": "windows",
            "skip_first_line": True,
            "interval": "800",
            "smart_mode": False,
            "groq_api_key": "",
        }

    def _save_settings(self):
        """Save current settings to file"""
        try:
            settings = {
                "source_lang": self.source_var.get(),
                "target_lang": self.target_var.get(),
                "ocr_engine": self.engine_var.get(),
                "skip_first_line": self.skip_first_line.get(),
                "ocr_engine": self.engine_var.get(),
                "skip_first_line": self.skip_first_line.get(),
                "interval": self.interval_var.get(),
                "smart_mode": self.smart_mode_var.get(),
                "groq_api_key": (
                    self.groq_api_key_var.get()
                    if self.groq_api_key_var.get() != "Enter Groq API Key..."
                    else ""
                ),
            }
            path = self._get_settings_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            print(f"[ScreenTranslator] Settings saved")
        except Exception as e:
            print(f"[ScreenTranslator] Failed to save settings: {e}")

    def _create_window(self):
        """Create main window with modern design"""
        import os

        icon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
        if not os.path.exists(icon_path):
            icon_path = None

        self.root = FramelessWindow(
            self.parent, title="Screen Translator", icon_path=icon_path
        )
        self.root.geometry("400x550")
        self.root.minsize(380, 480)

        # Main container with padding
        main = tk.Frame(self.root.content_frame, bg=colors["bg"])
        main.pack(fill="both", expand=True, padx=20, pady=15)

        # === HEADER ===
        header = tk.Frame(main, bg=colors["bg"])
        header.pack(fill="x", pady=(0, 15))

        tk.Label(
            header,
            text=f"🌐 {t('st_title')}",
            font=("Segoe UI", 15, "bold"),
            bg=colors["bg"],
            fg=colors["fg"],
        ).pack(anchor="w")

        tk.Label(
            header,
            text=t("st_subtitle"),
            font=("Segoe UI", 9),
            bg=colors["bg"],
            fg=colors["fg_dim"],
        ).pack(anchor="w", pady=(2, 0))

        # === LANGUAGE CARD ===
        lang_card = tk.Frame(main, bg=colors["card"], padx=14, pady=12)
        lang_card.pack(fill="x", pady=(0, 12))

        lang_row = tk.Frame(lang_card, bg=colors["card"])
        lang_row.pack(fill="x")

        tk.Label(
            lang_row,
            text=f"🔤 {t('st_language')}",
            font=("Segoe UI", 10, "bold"),
            bg=colors["card"],
            fg=colors["fg"],
        ).pack(side="left")

        # Languages - get available languages
        try:
            lang_dict = TranslationService.get_available_languages()
            languages = [
                (code, name) for code, name in lang_dict.items() if code != "auto"
            ]
        except Exception as e:
            print(f"[ScreenTranslator] Failed to get languages: {e}")
            languages = [("en", "English"), ("vi", "Vietnamese"), ("zh-cn", "Chinese")]

        # Target frame on right side
        lang_right = tk.Frame(lang_row, bg=colors["card"])
        lang_right.pack(side="right")

        self.source_var = tk.StringVar(value=self._settings.get("source_lang", "auto"))
        self.target_var = tk.StringVar(value=self._settings.get("target_lang", "vi"))

        source_cb = ttk.Combobox(
            lang_right,
            textvariable=self.source_var,
            values=["auto"] + [l[0] for l in languages],
            width=7,
            state="readonly",
        )
        source_cb.pack(side="left", padx=(0, 6))
        source_cb.bind("<<ComboboxSelected>>", self._on_lang_change)

        tk.Label(
            lang_right,
            text="→",
            font=("Segoe UI", 11),
            bg=colors["card"],
            fg=colors["accent"],
        ).pack(side="left", padx=4)

        target_cb = ttk.Combobox(
            lang_right,
            textvariable=self.target_var,
            values=[l[0] for l in languages],
            width=7,
            state="readonly",
        )
        target_cb.pack(side="left")
        target_cb.bind("<<ComboboxSelected>>", self._on_lang_change)

        # === ACTION BUTTONS ===
        action_frame = tk.Frame(main, bg=colors["bg"])
        action_frame.pack(fill="x", pady=(0, 12))

        capture_btn = ModernButton(
            action_frame,
            text=t("st_capture_once"),
            command=self._start_capture_once,
            kind="primary",
        )
        capture_btn.pack(fill="x", pady=(0, 8), ipady=3)

        self.realtime_btn = ModernButton(
            action_frame,
            text=t("st_realtime"),
            command=self._toggle_realtime,
            kind="secondary",
        )
        self.realtime_btn.pack(fill="x", ipady=3)

        self.realtime_status = tk.Label(
            action_frame,
            text=t("st_realtime_desc"),
            font=("Segoe UI", 9),
            bg=colors["bg"],
            fg=colors["fg_dim"],
        )
        self.realtime_status.pack(pady=(5, 0))

        # === AI MODE TOGGLE ===
        ai_frame = tk.Frame(main, bg=colors["bg"])
        ai_frame.pack(fill="x", pady=(5, 0))

        self.smart_mode_var = tk.BooleanVar(
            value=self._settings.get("smart_mode", False)
        )
        self.groq_api_key_var = tk.StringVar(
            value=self._settings.get("groq_api_key", "")
        )

        # Container for API Key (Hidden by default)
        self.api_key_container = tk.Frame(ai_frame, bg=colors["bg"])

        # Input Frame - Darker card background for contrast
        self.api_key_frame = tk.Frame(
            self.api_key_container, bg=colors["card"], padx=8, pady=4
        )
        self.api_key_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.api_key_entry = tk.Entry(
            self.api_key_frame,
            textvariable=self.groq_api_key_var,
            font=("Segoe UI", 9),
            bg=colors["card"],
            fg=colors["fg"],
            insertbackground=colors["fg"],
            bd=0,
            width=18,
            show="*",
        )
        self.api_key_entry.pack(side="left", fill="x", expand=True)

        # Link to get key
        def open_groq_console(e):
            import webbrowser

            webbrowser.open("https://console.groq.com/keys")

        link_lbl = tk.Label(
            self.api_key_frame,
            text="Get key free",
            font=("Segoe UI", 8, "underline"),
            bg=colors["card"],
            fg=colors["accent"],
            cursor="hand2",
        )
        link_lbl.pack(side="right", padx=(5, 0))
        link_lbl.bind("<Button-1>", open_groq_console)
        # Placeholder Logic
        PLACEHOLDER = "Enter Groq API Key..."

        def on_entry_focus_in(event):
            if self.groq_api_key_var.get() == PLACEHOLDER:
                self.groq_api_key_var.set("")
                self.api_key_entry.configure(show="*", fg=colors["fg"])

        def on_entry_focus_out(event):
            if not self.groq_api_key_var.get():
                self.groq_api_key_var.set(PLACEHOLDER)
                self.api_key_entry.configure(show="", fg=colors["fg_dim"])
            self._save_settings()

        self.api_key_entry.bind("<FocusIn>", on_entry_focus_in)
        self.api_key_entry.bind("<FocusOut>", on_entry_focus_out)

        # Initialize State
        current_key = self.groq_api_key_var.get()
        if not current_key:
            self.groq_api_key_var.set(PLACEHOLDER)
            self.api_key_entry.configure(show="", fg=colors["fg_dim"])
        else:
            self.api_key_entry.configure(show="*", fg=colors["fg"])

        def toggle_smart():
            is_smart = self.smart_mode_var.get()
            if is_smart:
                self.smart_btn.configure(text="⚡ Smart AI: ON", fg=colors["accent"])
                self.api_key_container.pack(side="left", fill="x", expand=True)
                # Auto focus if using placeholder
                if self.groq_api_key_var.get() == PLACEHOLDER:
                    # self.api_key_entry.focus() # Removed auto-focus
                    pass
            else:
                self.smart_btn.configure(text="⚡ Smart AI: OFF", fg=colors["fg_dim"])
                self.api_key_container.pack_forget()
            self._save_settings()

        self.smart_btn = tk.Checkbutton(
            ai_frame,
            text="⚡ Smart AI" + ("" if not self.smart_mode_var.get() else ": ON"),
            variable=self.smart_mode_var,
            font=("Segoe UI", 10, "bold"),
            bg=colors["bg"],
            fg=colors["fg_dim"],
            activebackground=colors["bg"],
            activeforeground=colors["accent"],
            selectcolor=colors["bg"],
            command=toggle_smart,
            indicatoron=False,  # Make it look like a button or label
            bd=0,
        )
        # Custom styling to make it look nicer
        self.smart_btn.pack(side="left")

        # Initial state
        if self.smart_mode_var.get():
            self.smart_btn.configure(text="⚡ Smart AI: ON", fg=colors["accent"])
            self.api_key_container.pack(side="left", fill="x", expand=True)
        else:
            self.smart_btn.configure(text="⚡ Smart AI: OFF", fg=colors["fg_dim"])
            self.api_key_container.pack_forget()

        # === SETTINGS CARD ===
        settings_card = tk.Frame(main, bg=colors["card"], padx=14, pady=12)
        settings_card.pack(fill="x", pady=(8, 0))

        # Settings header with toggle
        settings_header = tk.Frame(settings_card, bg=colors["card"])
        settings_header.pack(fill="x")

        self.settings_expanded = True  # Start expanded
        self.settings_toggle = tk.Label(
            settings_header,
            text=f"⚙️ {t('st_settings')}",
            font=("Segoe UI", 10, "bold"),
            bg=colors["card"],
            fg=colors["fg"],
            cursor="hand2",
        )
        self.settings_toggle.pack(side="left")

        self.toggle_arrow = tk.Label(
            settings_header,
            text="▲",
            font=("Segoe UI", 8),
            bg=colors["card"],
            fg=colors["fg_dim"],
            cursor="hand2",
        )
        self.toggle_arrow.pack(side="left", padx=(5, 0))

        # Story Log Button
        self.log_btn = tk.Label(
            settings_header,
            text="📜 Log",
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["accent"],
            cursor="hand2",
        )
        self.log_btn.pack(side="right", padx=5)
        self.log_btn.bind("<Button-1>", lambda e: self._toggle_story_log())

        # Settings content frame
        self.settings_content = tk.Frame(settings_card, bg=colors["card"])
        self.settings_content.pack(fill="x", pady=(10, 0))

        def toggle_settings(e=None):
            if self.settings_expanded:
                self.settings_content.pack_forget()
                self.toggle_arrow.configure(text="▼")
            else:
                self.settings_content.pack(fill="x", pady=(10, 0))
                self.toggle_arrow.configure(text="▲")
            self.settings_expanded = not self.settings_expanded

        self.settings_toggle.bind("<Button-1>", toggle_settings)
        self.toggle_arrow.bind("<Button-1>", toggle_settings)

        # --- OCR Engine Row ---
        ocr_row = tk.Frame(self.settings_content, bg=colors["card"])
        ocr_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            ocr_row,
            text=t("st_ocr_engine"),
            font=FONTS["body"],
            bg=colors["card"],
            fg=colors["fg"],
        ).pack(side="left")

        self.engine_var = tk.StringVar(
            value=self._settings.get("ocr_engine", "windows")
        )
        engine_cb = ttk.Combobox(
            ocr_row,
            textvariable=self.engine_var,
            values=["windows", "tesseract"],
            width=12,
        )
        engine_cb.pack(side="left", padx=(10, 5))
        engine_cb.bind("<<ComboboxSelected>>", self._on_engine_change)

        # Setup button
        setup_btn = tk.Label(
            ocr_row,
            text="⚙ Setup",
            font=("Segoe UI", 9),
            bg=colors["accent"],
            fg="#ffffff",
            cursor="hand2",
            padx=8,
            pady=2,
        )
        setup_btn.pack(side="right")
        setup_btn.bind("<Button-1>", lambda e: self._open_ocr_setup())

        # OCR Status indicator
        status_row = tk.Frame(self.settings_content, bg=colors["card"])
        status_row.pack(fill="x", pady=(0, 10))

        self.ocr_status_indicator = tk.Label(
            status_row,
            text="●",
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["success"],
        )
        self.ocr_status_indicator.pack(side="left")

        self.ocr_status_label = tk.Label(
            status_row,
            text=t("st_ocr_ready", engine="OCR"),
            font=("Segoe UI", 9),
            bg=colors["card"],
            fg=colors["fg_dim"],
        )
        self.ocr_status_label.pack(side="left", padx=(5, 0))

        # Skip first line toggle
        skip_row = tk.Frame(self.settings_content, bg=colors["card"])
        skip_row.pack(fill="x", pady=(0, 10))

        self.skip_first_line = tk.BooleanVar(
            value=self._settings.get("skip_first_line", True)
        )
        skip_cb = tk.Checkbutton(
            skip_row,
            text=t("st_skip_character"),
            variable=self.skip_first_line,
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["fg"],
            activebackground=colors["card"],
            selectcolor=colors["bg"],
            command=self._save_settings,
        )
        skip_cb.pack(side="left")

        # Realtime interval
        interval_row = tk.Frame(self.settings_content, bg=colors["card"])
        interval_row.pack(fill="x")

        tk.Label(
            interval_row,
            text=t("st_interval"),
            font=FONTS["body"],
            bg=colors["card"],
            fg=colors["fg"],
        ).pack(side="left")

        self.interval_var = tk.StringVar(value=self._settings.get("interval", "800"))
        interval_entry = tk.Entry(
            interval_row,
            textvariable=self.interval_var,
            width=6,
            font=FONTS["body"],
        )
        interval_entry.pack(side="left", padx=(10, 5))
        interval_entry.bind("<FocusOut>", lambda e: self._save_settings())

        tk.Label(
            interval_row,
            text="ms",
            font=FONTS["small"],
            bg=colors["card"],
            fg=colors["fg_dim"],
        ).pack(side="left")

        # Update OCR status
        self._update_ocr_status()

        # Create overlay with stop callback
        self.overlay = TranslationOverlay(
            self.parent,
            on_stop=self._stop_realtime_mode,
            on_show_log=self._toggle_story_log,
        )

        # Close handler
        if self.story_log and self.story_log.winfo_exists():
            self.story_log.destroy()
        self.root.set_on_close(self._on_close)

    def _on_lang_change(self, event=None):
        """Handle language selection change"""
        self.source_lang = self.source_var.get()
        self.target_lang = self.target_var.get()
        self._save_settings()

    def _on_engine_change(self, event=None):
        """Handle OCR engine selection change"""
        engine = self.engine_var.get()
        self.ocr_manager.set_engine(engine)
        self._update_ocr_status()
        self._save_settings()

    def _update_ocr_status(self):
        """Update OCR status indicator"""
        try:
            engine = self.engine_var.get()
            is_ready = self.ocr_manager.is_engine_ready(engine)

            if is_ready:
                self.ocr_status_indicator.configure(fg=colors["success"])
                engine_name = "Windows OCR" if engine == "windows" else "Tesseract"
                self.ocr_status_label.configure(
                    text=t("st_ocr_ready", engine=engine_name)
                )
            else:
                self.ocr_status_indicator.configure(fg=colors["warning"])
                self.ocr_status_label.configure(text=t("st_ocr_need_setup"))
        except Exception as e:
            self.ocr_status_indicator.configure(fg=colors["error"])
            self.ocr_status_label.configure(text=f"Error: {e}")

    def _ensure_story_log(self):
        """Ensure story log window exists"""
        if self.story_log is None or not self.story_log.winfo_exists():
            self.story_log = StoryLogWindow(self.parent)
            self.story_log.withdraw()

    def _toggle_story_log(self):
        """Show/Hide story log"""
        self._ensure_story_log()
        if self.story_log.winfo_viewable():
            self.story_log.hide()
        else:
            self.story_log.show()

    def _add_to_log(self, original: str, translated: str):
        """Add text to story log"""
        self._ensure_story_log()
        self.story_log.add_entry(original, translated)

    def _open_ocr_setup(self):
        """Open OCR setup window"""
        from .ocr_setup_window import OCRSetupWindow

        def on_ready():
            self._update_ocr_status()

        selected_engine = self.engine_var.get()
        OCRSetupWindow(self.root, on_ready=on_ready, selected_engine=selected_engine)

    def _start_capture_once(self):
        """Start capture once mode"""
        self.root.withdraw()

        def on_select(x, y, w, h):
            self.region = (x, y, w, h)
            self.root.deiconify()
            self._do_capture_once(x, y, w, h)

        def on_cancel():
            self.root.deiconify()

        RegionSelector(
            self.parent,
            on_select=on_select,
            on_cancel=on_cancel,
            instruction_text="Tô vùng chứa text cần dịch",
        ).show()

    def _do_capture_once(self, x: int, y: int, w: int, h: int):
        """Capture, OCR and translate once"""

        def process():
            try:
                from PIL import ImageGrab
                from services.ocr_addon_manager import is_valid_text

                screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))

                text = self.ocr_manager.extract_text(screenshot)

                # Validate OCR text
                if not text or not text.strip():
                    self.root.after(
                        0, lambda: self._show_error("Không nhận diện được text")
                    )
                    return

                # Check if text is valid/meaningful
                if not is_valid_text(text):
                    self.root.after(
                        0,
                        lambda: self._show_error(
                            "Text không rõ ràng, vui lòng chọn vùng khác"
                        ),
                    )
                    return

                if self.smart_mode_var.get():
                    translated, detected_lang = (
                        self.translation_service.translate_smart(
                            text,
                            dest=self.target_lang,
                            style="volam",
                            api_key=self.groq_api_key_var.get(),
                        )
                    )
                else:
                    translated, detected_lang = self.translation_service.translate(
                        text, dest=self.target_lang, src=self.source_lang
                    )

                def show_result():
                    self.overlay.position_near_region(x, y, w, h)
                    self.overlay.show_text(text, translated, detected_lang)
                    self._add_to_log(text, translated)

                self.root.after(0, show_result)

            except Exception as e:
                self.root.after(0, lambda: self._show_error(str(e)))

        threading.Thread(target=process, daemon=True).start()

    def _toggle_realtime(self):
        """Toggle realtime translation mode"""
        if self.is_realtime_running:
            self._stop_realtime_mode()
        else:
            self._start_realtime_mode()

    def _start_realtime_mode(self):
        """Start realtime translation"""
        self.root.withdraw()

        def on_select(x, y, w, h):
            self.region = (x, y, w, h)
            self._run_realtime(x, y, w, h)

        def on_cancel():
            self.root.deiconify()

        RegionSelector(
            self.parent,
            on_select=on_select,
            on_cancel=on_cancel,
            instruction_text="Tô vùng để dịch liên tục",
        ).show()

    def _run_realtime(self, x: int, y: int, w: int, h: int):
        """Run realtime translation loop"""
        self.is_realtime_running = True
        self._stop_realtime = False
        self._last_text = ""

        self.realtime_btn.configure(text="⏹ Dừng Real-time")
        self.realtime_status.configure(text="🔴 Đang dịch...", fg=colors["success"])

        self.overlay.position_near_region(x, y, w, h)
        self._last_translated = ""

        def loop():
            from PIL import ImageGrab
            from services.ocr_addon_manager import is_valid_text

            skip_first = self.skip_first_line.get()
            try:
                interval_ms = int(self.interval_var.get())
            except ValueError:
                interval_ms = 800

            while not self._stop_realtime:
                try:
                    screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                    text = self.ocr_manager.extract_text(screenshot)

                    # Validate text before processing - skip garbage OCR results
                    if text and text.strip() and is_valid_text(text):
                        text_clean = text.strip()

                        # Format: First line is character name, rest is dialogue
                        if skip_first:
                            lines = text_clean.split("\n")
                            if len(lines) > 1:
                                dialogue = " ".join(lines[1:]).strip()
                                if dialogue and is_valid_text(dialogue):
                                    text_clean = dialogue
                                elif not dialogue:
                                    # No dialogue after removing first line, skip
                                    continue

                        # Double-check cleaned text is still valid
                        if not text_clean or not is_valid_text(text_clean):
                            continue

                        if self._text_significantly_different(
                            text_clean, self._last_text
                        ):
                            self._last_text = text_clean

                            self._last_text = text_clean

                            # Use Smart Mode if enabled
                            if self.smart_mode_var.get():
                                # Get context from log (last 2 entries)
                                context = ""
                                if self.story_log and self.story_log.log_entries:
                                    last_entries = self.story_log.log_entries[-2:]
                                    context = "\n".join(
                                        [e["translated"] for e in last_entries]
                                    )

                                translated, detected = (
                                    self.translation_service.translate_smart(
                                        text_clean,
                                        context=context,
                                        dest=self.target_lang,
                                        style="volam",
                                        api_key=self.groq_api_key_var.get(),
                                    )
                                )
                            else:
                                translated, detected = (
                                    self.translation_service.translate(
                                        text_clean,
                                        dest=self.target_lang,
                                        src=self.source_lang,
                                    )
                                )

                            # Validate translation result too

                            # Validate translation result too
                            if translated and len(translated.strip()) >= 2:
                                if self._text_significantly_different(
                                    translated, self._last_translated
                                ):
                                    self._last_translated = translated
                                    self.root.after(
                                        0,
                                        lambda t=translated, d=detected: self.overlay.show_text(
                                            text_clean, t, d
                                        ),
                                    )
                                    self._add_to_log(text_clean, translated)

                except Exception as e:
                    print(f"[ScreenTranslator] Realtime error: {e}")

                sleep_steps = max(1, interval_ms // 100)
                for _ in range(sleep_steps):
                    if self._stop_realtime:
                        break
                    time.sleep(0.1)

            self.root.after(0, self._on_realtime_stopped)

        self._realtime_thread = threading.Thread(target=loop, daemon=True)
        self._realtime_thread.start()

    def _text_significantly_different(self, new_text: str, old_text: str) -> bool:
        """Check if text is significantly different using fuzzy comparison"""
        if not old_text:
            return True
        if not new_text:
            return False

        old_normalized = old_text.strip().lower()
        new_normalized = new_text.strip().lower()

        if old_normalized == new_normalized:
            return False

        old_chars = set(old_normalized)
        new_chars = set(new_normalized)
        common = len(old_chars & new_chars)
        total = max(len(old_chars), len(new_chars))

        if total > 0:
            char_similarity = common / total
            if char_similarity > 0.85:
                len_ratio = min(len(old_normalized), len(new_normalized)) / max(
                    len(old_normalized), len(new_normalized)
                )
                if len_ratio > 0.9:
                    return False

        old_words = set(old_normalized.split())
        new_words = set(new_normalized.split())

        if old_words and new_words:
            intersection = len(old_words & new_words)
            smaller_set = min(len(old_words), len(new_words))

            if smaller_set > 0 and intersection / smaller_set >= 0.85:
                return False

        return True

    def _stop_realtime_mode(self):
        """Stop realtime mode"""
        self._stop_realtime = True
        self._on_realtime_stopped()

    def _on_realtime_stopped(self):
        """Called when realtime mode stops"""
        if not self.is_realtime_running:
            return

        self.is_realtime_running = False
        self.realtime_btn.configure(text="🔄 Dịch Real-time")
        self.realtime_status.configure(
            text="Liên tục dịch vùng đã chọn", fg=colors["fg_dim"]
        )
        self.root.deiconify()

    def _show_error(self, message: str):
        """Show error in overlay"""
        self.overlay.show_text("", f"⚠ Lỗi: {message}", "")

    def _on_close(self):
        """Handle window close"""
        self._stop_realtime = True
        if self.overlay:
            self.overlay.destroy()
        self.root.destroy()

    def show(self):
        """Show the window"""
        self.root.deiconify()
        self.root.lift()
