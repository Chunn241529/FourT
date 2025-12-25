"""
WWM Combo Studio - Frame Version
A tk.Frame that can be embedded in any parent window.
This is the embeddable version used by menu_launcher.py
"""

import tkinter as tk
import os
import sys
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path

# Import components from this package
from .tooltip import RichTooltip
from .settings_dialog import SettingsDialog

# Import theme
try:
    from ..theme import colors, FONTS, ModernButton, apply_theme
except ImportError:
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from ui.theme import colors, FONTS, ModernButton, apply_theme

# Import i18n
try:
    from ..i18n import t
except ImportError:
    from ui.i18n import t

# Import services
from services.wwm_combo_service import (
    SkillLoader,
    ComboPlayer,
    ComboManager,
    TriggerManager,
    TemplateManager,
    get_resources_dir,
    get_combos_dir,
)
from services.wwm_combo_runtime import get_wwm_combo_runtime
from services.user_settings_service import get_user_settings_service


# Action items for weapon switching (scroll actions)
ACTION_ITEMS = [
    {
        "id": "scroll_down",
        "name": "⬇ Switch Weapon",
        "key": "scroll_down",
        "color": "#9b59b6",  # Purple
        "hold": 0.05,
        "description": "Switch weapon (toggle melee 1↔2)",
        "is_action": True,
    },
    {
        "id": "scroll_up",
        "name": "⬆ Switch Bow",
        "key": "scroll_up",
        "color": "#1abc9c",  # Teal
        "hold": 0.05,
        "description": "Switch to ranged weapon (bow)",
        "is_action": True,
    },
]


class WWMComboFrame(tk.Frame):
    """WWM Combo Studio Frame - Embeddable in any parent window"""

    def __init__(self, parent):
        super().__init__(parent, bg=colors["bg"])
        self.parent_window = parent

        # Initialize services (loads skills data, NOT images yet)
        self._init_services()

        # UI State - initialize with defaults
        self.drag_data = {"skill_data": None, "ghost": None}
        self.timeline_drag = {"index": None, "ghost": None}
        self.item_rects = []

        # Restore session state from runtime (if available)
        session = self._runtime.get_session_state()

        # Combo items from session (or empty list)
        self.combo_items = list(session.get("combo_items", []))

        # Trigger settings from session (or defaults)
        self.trigger_key_var = tk.StringVar(
            value=session.get("trigger_key", "Button.x1")
        )
        self.playback_mode_var = tk.StringVar(
            value=session.get("playback_mode", "once")
        )
        self.status_var = tk.StringVar(value="Ready")

        # Store restored weapon for palette setup
        self._restored_weapon = session.get("current_weapon", "")

        # Setup UI first (creates palette_canvas)
        self.setup_ui()

        # Apply restored trigger key to trigger manager
        trigger_key = session.get("trigger_key", "Button.x1")
        self.trigger_manager.trigger_key_code = TriggerManager.parse_trigger_string(
            trigger_key
        )
        self.btn_trigger.configure(text=trigger_key)

        # NOW start async image loading (after UI exists)
        self._start_async_image_load()

        # Start trigger listeners (will be kept running even when UI closes)
        self._setup_trigger_callbacks()
        self._runtime.start_listeners()

        # Handle window close - find the FramelessWindow from parent chain
        self._toplevel_window = self._find_toplevel_window(parent)
        if self._toplevel_window:
            # FramelessWindow has set_on_close method
            if hasattr(self._toplevel_window, "set_on_close"):
                self._toplevel_window.set_on_close(self._save_session_state)
            # Standard Toplevel uses protocol
            elif isinstance(self._toplevel_window, tk.Toplevel):
                self._toplevel_window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Auto-reload skills on focus (in case Admin updated them)
        self.bind("<FocusIn>", self._on_focus_in)

    def _on_focus_in(self, event):
        """Handle window focus - reload skills"""
        if event.widget == self:
            self.reload_skills()

    def _find_toplevel_window(self, widget):
        """Find the Toplevel window from widget's parent chain"""
        current = widget
        while current:
            if isinstance(current, tk.Toplevel):
                return current
            current = getattr(current, "master", None)
        return None

    def _save_session_state(self):
        """Save current UI state to runtime (called before window closes)"""
        current_weapon = (
            self.current_weapon_var.get() if hasattr(self, "current_weapon_var") else ""
        )
        self._runtime.save_session_state(
            combo_items=self.combo_items,
            trigger_key=self.trigger_key_var.get(),
            playback_mode=self.playback_mode_var.get(),
            current_weapon=current_weapon,
        )
        # Also clear UI callbacks
        self._runtime.ui_on_trigger_press = None
        self._runtime.ui_on_trigger_release = None
        self._runtime.ui_on_trigger_set = None

    def reload_skills(self):
        """Reload skills from disk (smart - skips if unchanged)"""
        try:
            old_skills = (
                self.skill_loader.skills.copy() if self.skill_loader.skills else []
            )
            self.skill_loader.load_skills()

            if self.skill_loader.skills != old_skills:
                self._start_async_image_load()
        except Exception as e:
            print(f"Error reloading skills: {e}")

    def _start_async_image_load(self):
        """Start async image loading with UI callback"""

        def on_images_loaded():
            self.after(0, self._on_images_ready)

        self.skill_loader.load_images(on_complete=on_images_loaded)
        self.render_palette()
        self.refresh_timeline()

    def _on_images_ready(self):
        """Called when async image loading completes"""
        try:
            self.skill_loader.finalize_images()
            self.render_palette()
            self.refresh_timeline()
        except Exception as e:
            print(f"Error finalizing images: {e}")

    def _init_services(self):
        """Initialize all service objects"""
        self.resources_dir = Path(get_resources_dir())
        self.skill_loader = SkillLoader(self.resources_dir)
        self.skill_loader.load_skills(force=True)

        # Use shared runtime for background execution
        self._runtime = get_wwm_combo_runtime()
        self.player = self._runtime.player
        self.combo_manager = self._runtime.combo_manager
        self.trigger_manager = self._runtime.trigger_manager
        self.template_manager = TemplateManager(get_combos_dir())

    def _setup_trigger_callbacks(self):
        """Setup callbacks for trigger manager via runtime"""
        # Register UI callbacks with the runtime
        # These will be called when the UI is visible
        self._runtime.ui_on_trigger_press = self._on_trigger_press
        self._runtime.ui_on_trigger_release = self._on_trigger_release
        self._runtime.ui_on_trigger_set = self._on_trigger_set

    # === Properties ===

    @property
    def skills(self):
        return self.skill_loader.skills

    @property
    def weapons(self):
        return self.skill_loader.weapons

    @property
    def image_cache(self):
        return self.skill_loader.image_cache

    @property
    def active_combos(self):
        return self.combo_manager.active_combos

    # === UI Setup ===

    def setup_ui(self):
        """Setup main UI layout"""
        self._setup_header()

        content = tk.Frame(self, bg=colors["bg"])
        content.pack(fill="both", expand=True, padx=10, pady=10)

        self._setup_palette(content)
        self._setup_editor(content)
        self._setup_activity(content)

    def _setup_header(self):
        """Setup header bar (simplified - title is now in window title bar)"""
        header = tk.Frame(self, bg=colors["bg"], height=36)
        header.pack(fill="x", padx=10, pady=(5, 0))
        header.pack_propagate(False)

        # Settings button (left)
        ModernButton(
            header,
            text="⚙ Settings",
            command=self._open_settings,
            kind="secondary",
            width=10,
        ).pack(side="left", padx=5)

        # Status (right)
        tk.Label(
            header,
            textvariable=self.status_var,
            font=FONTS["small"],
            bg=colors["bg"],
            fg=colors["fg_dim"],
        ).pack(side="right", padx=5)

        # Warning banner
        warning_frame = tk.Frame(self, bg=colors["bg"])
        warning_frame.pack(fill="x", padx=10, pady=(5, 0))

        border = tk.Frame(warning_frame, bg="#f5a623", width=3)
        border.pack(side="left", fill="y")

        quote_bg = "#2a2520"
        quote_content = tk.Frame(warning_frame, bg=quote_bg)
        quote_content.pack(side="left", fill="x", expand=True)

        warning_text = t("wwm_warning")
        tk.Label(
            quote_content,
            text=warning_text,
            font=("Segoe UI", 9),
            bg=quote_bg,
            fg="#d4a574",
            anchor="w",
            justify="left",
            wraplength=800,
            padx=10,
            pady=6,
        ).pack(fill="x")

    def _setup_palette(self, parent):
        """Setup skill palette panel"""
        palette_frame = tk.Frame(parent, bg=colors["sidebar"], width=260)
        palette_frame.pack(side="left", fill="y", padx=(0, 10))
        palette_frame.pack_propagate(False)

        # Header
        header = tk.Frame(palette_frame, bg=colors["header"])
        header.pack(fill="x")
        tk.Label(
            header,
            text=t("skills"),
            font=FONTS["h2"],
            bg=colors["header"],
            fg=colors["fg"],
        ).pack(side="left", padx=10, pady=8)

        ModernButton(
            header, text="+ Delay", command=self.add_delay_item, kind="secondary"
        ).pack(side="right", padx=5, pady=5)

        # Weapon selector
        weapon_frame = tk.Frame(palette_frame, bg=colors["sidebar"])
        weapon_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(
            weapon_frame,
            text=t("weapon"),
            bg=colors["sidebar"],
            fg=colors["fg"],
            font=FONTS["small"],
        ).pack(side="left", padx=5)

        self.current_weapon_var = tk.StringVar(value="common")
        weapon_names = {
            w["id"]: f"{w.get('icon', '')} {w['name']}"
            for w in self.skill_loader.weapons
        }

        self.weapon_combo = ttk.Combobox(
            weapon_frame,
            textvariable=self.current_weapon_var,
            values=list(weapon_names.values()),
            state="readonly",
            width=15,
        )
        self.weapon_combo.pack(side="left", fill="x", expand=True, padx=5)

        # Restore weapon selection from session, or use first weapon
        restored_weapon = getattr(self, "_restored_weapon", "")
        weapon_set = False
        if restored_weapon and self.skill_loader.weapons:
            # Find weapon by display name
            for weapon in self.skill_loader.weapons:
                weapon_display = f"{weapon.get('icon', '')} {weapon['name']}"
                if weapon_display == restored_weapon:
                    self.current_weapon_var.set(weapon_display)
                    weapon_set = True
                    break

        if not weapon_set and self.skill_loader.weapons:
            first_weapon = self.skill_loader.weapons[0]
            self.current_weapon_var.set(
                f"{first_weapon.get('icon', '')} {first_weapon['name']}"
            )

        self.weapon_combo.bind("<<ComboboxSelected>>", self._on_weapon_changed)
        self._weapon_name_to_id = {
            f"{w.get('icon', '')} {w['name']}": w["id"]
            for w in self.skill_loader.weapons
        }

        # Canvas
        canvas_frame = tk.Frame(palette_frame, bg=colors["sidebar"])
        canvas_frame.pack(fill="both", expand=True)

        self.palette_canvas = tk.Canvas(
            canvas_frame, bg=colors["sidebar"], highlightthickness=0
        )
        self.palette_canvas.pack(fill="both", expand=True)

        # Scroll handling
        def _can_scroll():
            bbox = self.palette_canvas.bbox("all")
            if not bbox:
                return False
            content_height = bbox[3] - bbox[1]
            visible_height = self.palette_canvas.winfo_height()
            return content_height > visible_height

        def _on_palette_scroll(event):
            if not _can_scroll():
                return "break"
            self.palette_canvas.yview_scroll(-1 * (event.delta // 120), "units")
            return "break"

        self.palette_canvas.bind("<MouseWheel>", _on_palette_scroll)
        canvas_frame.bind("<MouseWheel>", _on_palette_scroll)

        def _bind_scroll(event):
            self.palette_canvas.bind_all("<MouseWheel>", _on_palette_scroll)

        def _unbind_scroll(event):
            self.palette_canvas.unbind_all("<MouseWheel>")

        self.palette_canvas.bind("<Enter>", _bind_scroll)
        self.palette_canvas.bind("<Leave>", _unbind_scroll)

        self.render_palette()

        # Template section
        self._setup_templates(palette_frame)

        # Drag bindings
        self.palette_canvas.bind("<Button-1>", self.on_palette_drag_start)
        self.palette_canvas.bind("<B1-Motion>", self.on_palette_drag_motion)
        self.palette_canvas.bind("<ButtonRelease-1>", self.on_palette_drag_stop)

    def _setup_templates(self, parent):
        """Setup template combo section"""
        tk.Frame(parent, bg=colors["border"], height=1).pack(fill="x", pady=5)

        header = tk.Frame(parent, bg=colors["sidebar"])
        header.pack(fill="x", padx=5)

        tk.Label(
            header,
            text=t("templates"),
            font=FONTS["bold"],
            bg=colors["sidebar"],
            fg=colors["fg"],
        ).pack(side="left")

        ModernButton(
            header, text="+ Save", command=self.save_as_template, kind="secondary"
        ).pack(side="right", padx=2)

        template_frame = tk.Frame(parent, bg=colors["sidebar"], height=150)
        template_frame.pack(fill="x", expand=False, padx=5, pady=5)
        template_frame.pack_propagate(False)

        self.template_canvas = tk.Canvas(
            template_frame, bg=colors["sidebar"], highlightthickness=0
        )
        self.template_canvas.pack(fill="both", expand=True)

        self.template_container = tk.Frame(self.template_canvas, bg=colors["sidebar"])
        self.template_canvas.create_window(
            (0, 0), window=self.template_container, anchor="nw"
        )

        def _on_template_scroll(event):
            self.template_canvas.yview_scroll(-1 * (event.delta // 120), "units")
            return "break"

        self.template_canvas.bind("<MouseWheel>", _on_template_scroll)
        self.template_container.bind("<MouseWheel>", _on_template_scroll)

        def _update_scroll_region(event=None):
            self.template_canvas.configure(
                scrollregion=self.template_canvas.bbox("all")
            )

        self.template_container.bind("<Configure>", _update_scroll_region)

        self.refresh_templates()

    def refresh_templates(self):
        """Refresh template list display"""
        for widget in self.template_container.winfo_children():
            widget.destroy()

        # Templates already prefetched in splash screen - no need to fetch again
        all_templates = self.template_manager.get_all_templates()

        if not all_templates:
            tk.Label(
                self.template_container,
                text="No templates yet\nSave combos or use + Save",
                bg=colors["sidebar"],
                fg=colors["fg_dim"],
                font=FONTS["small"],
                justify="center",
            ).pack(pady=10)
            return

        for template in all_templates:
            self._create_template_card(template)

    def _create_template_card(self, template):
        """Create a draggable template card"""
        name = template["name"]
        items = template.get("items", [])
        skill_count = sum(1 for i in items if i.get("type") == "skill")
        delay_count = sum(1 for i in items if i.get("type") == "delay")
        is_server = template.get("is_server", False)

        card_bg = "#2a3f5f" if is_server else colors["card"]
        accent_color = "#3498db" if is_server else colors["accent"]

        card = tk.Frame(self.template_container, bg=card_bg, bd=0)
        card.pack(fill="x", pady=3, padx=2)
        card.template_data = template

        accent_bar = tk.Frame(card, bg=accent_color, width=4)
        accent_bar.pack(side="left", fill="y")

        content = tk.Frame(card, bg=card_bg)
        content.pack(side="left", fill="both", expand=True, padx=8, pady=6)

        top_row = tk.Frame(content, bg=card_bg)
        top_row.pack(fill="x")

        icon = "☁️" if is_server else "📋"
        tk.Label(
            top_row, text=icon, bg=card_bg, fg=colors["fg"], font=("Segoe UI", 10)
        ).pack(side="left", padx=(0, 5))

        display_name = name[:18] + "..." if len(name) > 18 else name
        tk.Label(
            top_row,
            text=display_name,
            bg=card_bg,
            fg=colors["fg"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        del_btn = None
        if not is_server:
            del_btn = tk.Label(
                top_row,
                text="×",
                bg=card_bg,
                fg="#e74c3c",
                font=("Arial", 14, "bold"),
                cursor="hand2",
            )
            del_btn.pack(side="right", padx=2)
            del_btn.bind("<Button-1>", lambda e, n=name: self._delete_template(n))

        stats_row = tk.Frame(content, bg=card_bg)
        stats_row.pack(fill="x", pady=(3, 0))

        skill_badge = tk.Label(
            stats_row,
            text=f"⚔ {skill_count}",
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 8),
            padx=4,
            pady=1,
        )
        skill_badge.pack(side="left", padx=(0, 4))

        delay_badge = tk.Label(
            stats_row,
            text=f"⏱ {delay_count}",
            bg="#f39c12",
            fg="white",
            font=("Segoe UI", 8),
            padx=4,
            pady=1,
        )
        delay_badge.pack(side="left")

        if is_server:
            server_label = tk.Label(
                stats_row,
                text="server",
                bg=card_bg,
                fg="#7fb3d5",
                font=("Segoe UI", 8, "italic"),
            )
            server_label.pack(side="right")

        def bind_drag(widget):
            widget.bind(
                "<Button-1>", lambda e, t=template: self._on_template_drag_start(e, t)
            )
            widget.bind("<B1-Motion>", self._on_template_drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_template_drag_stop)
            for child in widget.winfo_children():
                if del_btn and child == del_btn:
                    continue
                bind_drag(child)

        bind_drag(card)

        def on_enter(e):
            card.configure(bg="#3a4f6f" if is_server else "#3a3f4a")
            for w in [content, top_row, stats_row]:
                w.configure(bg="#3a4f6f" if is_server else "#3a3f4a")

        def on_leave(e):
            card.configure(bg=card_bg)
            for w in [content, top_row, stats_row]:
                w.configure(bg=card_bg)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def save_as_template(self):
        """Save current combo as template"""
        if not self.combo_items:
            messagebox.showwarning("Empty", "Create a combo first!")
            return

        name = simpledialog.askstring(
            "Save Template", "Enter template name:", parent=self
        )
        if not name or not name.strip():
            return

        name = name.strip()

        if self.template_manager.get_template(name):
            if not messagebox.askyesno(
                "Exists", f"Template '{name}' exists. Overwrite?"
            ):
                return
            self.template_manager.delete_template(name)

        if self.template_manager.add_template(name, list(self.combo_items)):
            self.status_var.set(f"Template '{name}' saved!")
            self.refresh_templates()
        else:
            messagebox.showerror("Error", "Failed to save template")

    def _delete_template(self, name):
        """Delete a template"""
        if messagebox.askyesno("Delete", f"Delete template '{name}'?"):
            self.template_manager.delete_template(name)
            self.refresh_templates()
            self.status_var.set(f"Template '{name}' deleted")

    def _on_template_drag_start(self, event, template):
        """Start dragging a template"""
        self.template_drag = {"template": template, "ghost": None}

        self.template_drag["ghost"] = tk.Toplevel(self)
        self.template_drag["ghost"].overrideredirect(True)
        self.template_drag["ghost"].attributes("-alpha", 0.8)
        self.template_drag["ghost"].attributes("-topmost", True)

        f = tk.Frame(
            self.template_drag["ghost"], bg=colors["accent"], bd=2, relief="solid"
        )
        f.pack()
        tk.Label(
            f,
            text=f"📋 {template['name']}",
            fg="white",
            bg=colors["accent"],
            font=FONTS["bold"],
            padx=10,
            pady=5,
        ).pack()

        self.template_drag["ghost"].geometry(f"+{event.x_root+10}+{event.y_root+10}")

    def _on_template_drag_motion(self, event):
        """Update template ghost"""
        if hasattr(self, "template_drag") and self.template_drag.get("ghost"):
            self.template_drag["ghost"].geometry(
                f"+{event.x_root+10}+{event.y_root+10}"
            )

    def _on_template_drag_stop(self, event):
        """Drop template onto timeline"""
        if not hasattr(self, "template_drag"):
            return

        if self.template_drag.get("ghost"):
            self.template_drag["ghost"].destroy()
            self.template_drag["ghost"] = None

            if self._is_over_timeline(event):
                template = self.template_drag.get("template")
                if template:
                    for item in template.get("items", []):
                        self.combo_items.append(dict(item))

                    self.refresh_timeline()
                    self.status_var.set(
                        f"Added template '{template['name']}' to timeline"
                    )

        self.template_drag = {}

    def _setup_editor(self, parent):
        """Setup combo editor panel"""
        editor_frame = tk.Frame(parent, bg=colors["bg"])
        editor_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        controls = tk.Frame(editor_frame, bg=colors["bg"])
        controls.pack(fill="x", pady=(0, 10))

        tk.Label(
            controls,
            text="Combo Timeline:",
            font=FONTS["h2"],
            bg=colors["bg"],
            fg=colors["fg"],
        ).pack(side="left")

        ModernButton(
            controls, text="🗑", command=self.clear_combo, kind="secondary"
        ).pack(side="right", padx=5)

        # Tip
        tip_frame = tk.Frame(editor_frame, bg=colors["bg"])
        tip_frame.pack(fill="x", pady=(0, 5))

        tip_border = tk.Frame(tip_frame, bg="#3498db", width=3)
        tip_border.pack(side="left", fill="y")

        tip_bg = "#1a2a35"
        tip_content = tk.Frame(tip_frame, bg=tip_bg)
        tip_content.pack(side="left", fill="x", expand=True)

        # Title
        tk.Label(
            tip_content,
            text=t("guide_title"),
            font=("Segoe UI", 10, "bold"),
            bg=tip_bg,
            fg="#5dade2",
            anchor="w",
            padx=10,
            pady=6,
        ).pack(fill="x")

        # Drag tip
        tk.Label(
            tip_content,
            text=t("drag_tip"),
            font=("Segoe UI", 9),
            bg=tip_bg,
            fg="#7fb3d5",
            anchor="w",
            justify="left",
            padx=10,
            pady=2,
        ).pack(fill="x")

        # Activate instruction
        tk.Label(
            tip_content,
            text=t("activate_instruction"),
            font=("Segoe UI", 9, "bold"),
            bg=tip_bg,
            fg="#f5b041",
            anchor="w",
            padx=10,
            pady=6,
        ).pack(fill="x")

        # Timeline canvas
        timeline_frame = tk.Frame(
            editor_frame, bg=colors["input_bg"], bd=2, relief="sunken"
        )
        timeline_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.timeline_canvas = tk.Canvas(
            timeline_frame, bg=colors["input_bg"], highlightthickness=0
        )
        self.timeline_canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self.on_timeline_drop)

        self._setup_bottom_controls(editor_frame)

    def _setup_bottom_controls(self, parent):
        """Setup trigger and action buttons"""
        bottom = tk.Frame(parent, bg=colors["bg"])
        bottom.pack(fill="x")

        trigger_frame = tk.Frame(bottom, bg=colors["bg"])
        trigger_frame.pack(side="left")

        tk.Label(trigger_frame, text="Trigger:", bg=colors["bg"], fg=colors["fg"]).pack(
            side="left", padx=5
        )
        self.btn_trigger = ModernButton(
            trigger_frame,
            text=self.trigger_key_var.get(),
            command=self.start_set_trigger,
            width=12,
            kind="secondary",
        )
        self.btn_trigger.pack(side="left", padx=5)

        tk.Label(trigger_frame, text="Mode:", bg=colors["bg"], fg=colors["fg"]).pack(
            side="left", padx=(15, 5)
        )
        from ..theme import ModernRadioButton

        for text, val in [("Once", "once"), ("Loop", "loop"), ("Hold", "hold")]:
            rb = ModernRadioButton(
                trigger_frame, text=text, variable=self.playback_mode_var, value=val
            )
            rb.pack(side="left", padx=3)

        action_frame = tk.Frame(bottom, bg=colors["bg"])
        action_frame.pack(side="right")

        self.btn_play = ModernButton(
            action_frame,
            text="▶ Test",
            command=self.test_combo,
            kind="success",
            width=10,
        )
        self.btn_play.pack(side="left", padx=5)

        ModernButton(
            action_frame,
            text="+ Add to Active",
            command=self.add_to_active,
            kind="primary",
            width=15,
        ).pack(side="left", padx=5)

        ModernButton(
            action_frame,
            text="💾 Save",
            command=self.save_combo,
            kind="secondary",
            width=8,
        ).pack(side="left", padx=5)

    def _setup_activity(self, parent):
        """Setup active combos panel"""
        activity_frame = tk.Frame(parent, bg=colors["sidebar"], width=250)
        activity_frame.pack(side="right", fill="y")
        activity_frame.pack_propagate(False)

        header = tk.Frame(activity_frame, bg=colors["header"])
        header.pack(fill="x")
        tk.Label(
            header,
            text=t("active_combos"),
            font=FONTS["h2"],
            bg=colors["header"],
            fg=colors["fg"],
        ).pack(side="left", padx=10, pady=8)

        ModernButton(
            header, text="🗑", command=self.clear_active_combos, kind="secondary"
        ).pack(side="right", padx=5, pady=5)

        self.active_container = tk.Frame(activity_frame, bg=colors["sidebar"])
        self.active_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.update_active_list()

        load_frame = tk.Frame(activity_frame, bg=colors["sidebar"])
        load_frame.pack(fill="x", pady=5)
        ModernButton(
            load_frame, text=t("load_combo"), command=self.load_combo, kind="secondary"
        ).pack(fill="x", padx=5)

    # === Rendering ===

    def _on_weapon_changed(self, event=None):
        """Handle weapon selection change"""
        self.render_palette()

    def _get_current_weapon_id(self) -> str:
        """Get currently selected weapon ID"""
        if hasattr(self, "_weapon_name_to_id"):
            weapon_name = self.current_weapon_var.get()
            return self._weapon_name_to_id.get(weapon_name, "common")
        return "common"

    def render_palette(self):
        """Render skill palette"""
        self.palette_canvas.delete("all")
        y = 5
        width = 240
        row_height = 42

        current_weapon_id = self._get_current_weapon_id()
        filtered_skills = self.skill_loader.get_skills_by_weapon(current_weapon_id)

        if current_weapon_id != "common":
            common_skills = self.skill_loader.get_skills_by_weapon("common")

            if filtered_skills and common_skills:
                for skill in filtered_skills:
                    y = self._render_palette_skill(skill, y, width, row_height)

                self.palette_canvas.create_line(
                    5, y + 3, width + 5, y + 3, fill=colors["border"], dash=(2, 2)
                )
                self.palette_canvas.create_text(
                    width / 2 + 5,
                    y + 12,
                    text="⭐ Chung",
                    fill=colors["fg_dim"],
                    font=FONTS["small"],
                )
                y += 22

                for skill in common_skills:
                    y = self._render_palette_skill(skill, y, width, row_height)
            else:
                all_skills = filtered_skills + common_skills
                for skill in all_skills:
                    y = self._render_palette_skill(skill, y, width, row_height)
        else:
            for skill in filtered_skills:
                y = self._render_palette_skill(skill, y, width, row_height)

        # Render Actions section (scroll actions for weapon switching)
        y += 5
        self.palette_canvas.create_line(
            5, y, width + 5, y, fill=colors["border"], dash=(2, 2)
        )
        self.palette_canvas.create_text(
            width / 2 + 5,
            y + 12,
            text="🔄 Actions",
            fill=colors["fg_dim"],
            font=FONTS["small"],
        )
        y += 25

        for action in ACTION_ITEMS:
            y = self._render_palette_action(action, y, width, row_height)

        self.palette_canvas.configure(scrollregion=(0, 0, width + 10, y + 10))

    def _render_palette_skill(
        self, skill: dict, y: int, width: int, row_height: int
    ) -> int:
        """Render a single skill in palette"""
        tag = f"skill_{skill['id']}"
        color = self.skill_loader.get_skill_color(skill)

        self.palette_canvas.create_rectangle(
            5, y, width + 5, y + row_height, fill="", outline="", tags=(tag, "skill")
        )

        if skill["id"] in self.image_cache:
            self.palette_canvas.create_image(
                25,
                y + row_height / 2,
                image=self.image_cache[skill["id"]],
                tags=(tag, "skill"),
            )
            text_x = 48
        else:
            self.palette_canvas.create_oval(
                8,
                y + row_height / 2 - 4,
                16,
                y + row_height / 2 + 4,
                fill=color,
                outline="",
                tags=(tag, "skill"),
            )
            text_x = 22

        self.palette_canvas.create_text(
            text_x,
            y + row_height / 2,
            text=skill["name"],
            anchor="w",
            fill=colors["fg"],
            font=FONTS["small"],
            tags=(tag, "skill"),
        )

        settings_service = get_user_settings_service()
        keybindings = settings_service.get_all_keybindings()

        # Get the actual key for this skill (from user settings or default)
        skill_id = skill["id"]
        default_key = skill["key"].lower()

        # Map skill_id to keybinding key
        # Weapon-specific skills like 'nameless_sword_skill_1' should use 'skill_1' keybinding
        # Perception skills (_skill_3, _skill_4) map to skill_1, skill_2 respectively
        # Common skills like 'light_attack', 'dodge' use their own keybinding
        keybind_key = skill_id

        # Check if this is a weapon-specific skill
        # but NOT a mystic_skill or common_ (those have their own keybindings)
        skill_id_lower = skill_id.lower()
        if not skill_id_lower.startswith(
            "mystic_skill_"
        ) and not skill_id_lower.startswith("common_"):
            # skill_1 and skill_3 (perception) both use Q slot
            if skill_id_lower.endswith("_skill_1") or skill_id_lower.endswith(
                "_skill_3"
            ):
                keybind_key = "skill_1"
            # skill_2 and skill_4 (perception) both use E/` slot
            elif skill_id_lower.endswith("_skill_2") or skill_id_lower.endswith(
                "_skill_4"
            ):
                keybind_key = "skill_2"

        # Check if user has custom keybinding for this skill type
        if keybind_key in keybindings:
            display_key = keybindings[keybind_key]
        else:
            display_key = default_key

        # Build display text with modifiers if present
        modifiers = skill.get("modifiers", [])
        if modifiers:
            mod_prefix = "+".join(m.upper() for m in modifiers) + "+"
            key_display_text = mod_prefix + display_key.upper().replace("`", "~")
        else:
            key_display_text = display_key.upper().replace("`", "~")

        self.palette_canvas.create_text(
            width,
            y + row_height / 2,
            text=f"[{key_display_text}]",
            anchor="e",
            fill=colors["fg_dim"],
            font=(FONTS["small"][0], 8),
            tags=(tag, "skill"),
        )

        if skill.get("description"):

            def on_enter(e, sk=skill, row_y=y):
                cx = self.palette_canvas.winfo_rootx() + (width // 2)
                cy = self.palette_canvas.winfo_rooty() + row_y + row_height

                if hasattr(self, "_current_tooltip") and self._current_tooltip:
                    self._current_tooltip.hidetip()

                self._current_tooltip = RichTooltip(
                    self.palette_canvas, lambda: sk, self.resources_dir, auto_bind=False
                )
                self._current_tooltip.show_at_manual(cx, cy)

            def on_leave(e):
                if hasattr(self, "_current_tooltip") and self._current_tooltip:
                    self._current_tooltip.hidetip()
                    self._current_tooltip = None

            self.palette_canvas.tag_bind(tag, "<Enter>", on_enter)
            self.palette_canvas.tag_bind(tag, "<Leave>", on_leave)

        return y + row_height + 2

    def _render_palette_action(
        self, action: dict, y: int, width: int, row_height: int
    ) -> int:
        """Render a single action item in palette (scroll actions)"""
        tag = f"action_{action['id']}"
        color = action.get("color", "#9b59b6")

        # Background rectangle
        self.palette_canvas.create_rectangle(
            5, y, width + 5, y + row_height, fill="", outline="", tags=(tag, "action")
        )

        # Colored circle indicator
        self.palette_canvas.create_oval(
            8,
            y + row_height / 2 - 8,
            24,
            y + row_height / 2 + 8,
            fill=color,
            outline="white",
            width=1,
            tags=(tag, "action"),
        )

        # Action name
        self.palette_canvas.create_text(
            30,
            y + row_height / 2,
            text=action["name"],
            anchor="w",
            fill=colors["fg"],
            font=FONTS["small"],
            tags=(tag, "action"),
        )

        # Description hint
        self.palette_canvas.create_text(
            width,
            y + row_height / 2,
            text="[SCROLL]",
            anchor="e",
            fill=colors["fg_dim"],
            font=(FONTS["small"][0], 8),
            tags=(tag, "action"),
        )

        return y + row_height + 2

    def refresh_timeline(self):
        """Refresh timeline display"""
        self.timeline_canvas.delete("all")
        self.item_rects = []
        x, y, h = 15, 15, 60

        for i, item in enumerate(self.combo_items):
            tag = f"item_{i}"

            if item["type"] == "delay":
                w = self._render_delay_item(x, y, h, i, item, tag)
            else:
                w = self._render_skill_item(x, y, h, i, item, tag)

            self.item_rects.append((x, y, x + w, y + h, i))
            self._render_delete_button(x, y, w, i)

            if i < len(self.combo_items) - 1:
                self.timeline_canvas.create_text(
                    x + w + 12,
                    y + h / 2,
                    text="→",
                    fill=colors["fg_dim"],
                    font=FONTS["h2"],
                )
                x += 25

            x += w + 10

            # Use actual canvas width or fallback to reasonable default when not yet rendered
            canvas_width = self.timeline_canvas.winfo_width()
            if canvas_width < 100:
                canvas_width = 800  # Fallback when canvas not yet rendered

            if x > canvas_width - 100:
                x = 15
                y += h + 15

    def _render_delay_item(self, x, y, h, idx, item, tag):
        """Render a delay item"""
        text = f"⏳ {item['value']:.2f}s"
        w = len(text) * 8 + 20

        self.timeline_canvas.create_rectangle(
            x,
            y,
            x + w,
            y + h,
            fill=colors["input_bg"],
            outline=colors["border"],
            tags=(tag, "draggable"),
        )
        self.timeline_canvas.create_text(
            x + w / 2,
            y + h / 2,
            text=text,
            fill=colors["fg_dim"],
            font=FONTS["bold"],
            tags=(tag, "draggable"),
        )

        self.timeline_canvas.tag_bind(
            tag, "<Double-1>", lambda e, i=idx: self.edit_delay(i)
        )
        return w

    def _render_skill_item(self, x, y, h, idx, item, tag):
        """Render a skill item"""
        modifiers = item.get("modifiers", [])
        base_key = item["key"].upper().replace("`", "~")
        if modifiers:
            key_display = "+".join(modifiers) + "+" + base_key
        else:
            key_display = base_key

        if item["id"] in self.image_cache:
            w = 50
        else:
            w = max(50, len(key_display) * 10 + 20)

        color = item.get("color", colors["accent"])

        self.timeline_canvas.create_rectangle(
            x, y, x + w, y + h, fill=color, outline="white", tags=(tag, "draggable")
        )

        if item["id"] in self.image_cache:
            self.timeline_canvas.create_image(
                x + w / 2,
                y + h / 2,
                image=self.image_cache[item["id"]],
                tags=(tag, "draggable"),
            )
        else:
            font_size = FONTS["h2"]
            if len(key_display) > 5:
                font_size = FONTS["body"]

            self.timeline_canvas.create_text(
                x + w / 2,
                y + h / 2,
                text=key_display,
                fill="white",
                font=font_size,
                tags=(tag, "draggable"),
            )

        # Double-click to edit hold value
        self.timeline_canvas.tag_bind(
            tag, "<Double-1>", lambda e, i=idx: self.edit_skill_hold(i)
        )
        return w

    def _render_delete_button(self, x, y, w, idx):
        """Render delete button"""
        del_tag = f"del_{idx}"
        self.timeline_canvas.create_text(
            x + w - 8,
            y + 8,
            text="✕",
            fill="white",
            font=("Arial", 9, "bold"),
            tags=del_tag,
        )
        self.timeline_canvas.tag_bind(
            del_tag, "<Button-1>", lambda e, i=idx: self.remove_item(i)
        )

    def update_active_list(self):
        """Update active combos display"""
        for widget in self.active_container.winfo_children():
            widget.destroy()

        if not self.active_combos:
            tk.Label(
                self.active_container,
                text="No active combos\n\nCreate a combo and click\n'+ Add to Active'",
                bg=colors["sidebar"],
                fg=colors["fg_dim"],
                font=FONTS["small"],
                justify="center",
            ).pack(pady=30)
            return

        for trigger_code, data in self.active_combos.items():
            self._create_active_card(trigger_code, data)

    def _create_active_card(self, trigger_code, data):
        """Create card for active combo"""
        card = tk.Frame(self.active_container, bg=colors["secondary"], pady=8, padx=8)
        card.pack(fill="x", pady=3)

        mode = data["settings"]["mode"]
        icon = "↻" if mode == "loop" else "✋" if mode == "hold" else "▶"
        tk.Label(
            card, text=icon, bg=colors["secondary"], fg="white", font=FONTS["h2"]
        ).pack(side="left", padx=(0, 8))

        info = tk.Frame(card, bg=colors["secondary"])
        info.pack(side="left", fill="both", expand=True)

        tk.Label(
            info,
            text=data["name"],
            bg=colors["secondary"],
            fg="white",
            font=FONTS["bold"],
        ).pack(anchor="w")
        tk.Label(
            info,
            text=f"⌨ {data['settings']['trigger']} • {len(data['items'])} items",
            bg=colors["secondary"],
            fg=colors["fg_dim"],
            font=FONTS["small"],
        ).pack(anchor="w")

        ModernButton(
            card,
            text="✕",
            width=3,
            kind="danger",
            command=lambda t=trigger_code: self._remove_active(t),
        ).pack(side="right")

    # === Event Handlers ===

    def on_palette_drag_start(self, event):
        """Start dragging from palette"""
        x, y = self.palette_canvas.canvasx(event.x), self.palette_canvas.canvasy(
            event.y
        )
        items = self.palette_canvas.find_closest(x, y)
        if not items:
            return

        tags = self.palette_canvas.gettags(items[0])
        skill_id = None
        action_id = None

        for t in tags:
            if t.startswith("skill_"):
                skill_id = t.split("_", 1)[1]
                break
            elif t.startswith("action_"):
                action_id = t.split("_", 1)[1]
                break

        if skill_id:
            skill = next((s for s in self.skills if s["id"] == skill_id), None)
            if skill:
                self.drag_data["skill_data"] = skill
                self.drag_data["is_action"] = False
                self._create_drag_ghost(skill, event)
        elif action_id:
            action = next((a for a in ACTION_ITEMS if a["id"] == action_id), None)
            if action:
                self.drag_data["skill_data"] = action
                self.drag_data["is_action"] = True
                self._create_drag_ghost(action, event)

    def on_palette_drag_motion(self, event):
        """Update drag ghost"""
        if self.drag_data.get("ghost"):
            self.drag_data["ghost"].geometry(f"+{event.x_root+10}+{event.y_root+10}")

    def on_palette_drag_stop(self, event):
        """Handle drop from palette"""
        if self.drag_data.get("ghost"):
            self.drag_data["ghost"].destroy()
            self.drag_data["ghost"] = None

            if self._is_over_timeline(event):
                item_data = self.drag_data.get("skill_data")
                is_action = self.drag_data.get("is_action", False)

                if item_data:
                    if is_action:
                        # Handle action items (scroll actions) - simpler flow
                        self.combo_items.append(
                            {
                                "type": "skill",  # Uses same execution path as skills
                                "id": item_data["id"],
                                "name": item_data["name"],
                                "key": item_data["key"],  # scroll_down or scroll_up
                                "color": item_data.get("color", "#9b59b6"),
                                "hold": item_data.get("hold", 0.05),
                                "click_count": 1,
                                "weapon": None,
                                "modifiers": [],
                                "description": item_data.get("description", ""),
                                "image": "",
                                "countdown": 0,
                                "is_action": True,  # Mark as action for display
                            }
                        )
                    else:
                        # Handle regular skills
                        skill = item_data
                        settings_service = get_user_settings_service()
                        keybindings = settings_service.get_all_keybindings()

                        # Get custom keybinding if exists, otherwise use default from skill
                        skill_id = skill["id"]

                        # Map skill_id to keybinding key
                        # Weapon-specific skills like 'nameless_sword_skill_1' should use 'skill_1' keybinding
                        # Perception skills (_skill_3, _skill_4) map to skill_1, skill_2 respectively
                        keybind_key = skill_id
                        skill_id_lower = skill_id.lower()
                        if not skill_id_lower.startswith(
                            "mystic_skill_"
                        ) and not skill_id_lower.startswith("common_"):
                            if skill_id_lower.endswith(
                                "_skill_1"
                            ) or skill_id_lower.endswith("_skill_3"):
                                keybind_key = "skill_1"
                            elif skill_id_lower.endswith(
                                "_skill_2"
                            ) or skill_id_lower.endswith("_skill_4"):
                                keybind_key = "skill_2"

                        if keybind_key in keybindings:
                            skill_key = keybindings[keybind_key]
                        else:
                            skill_key = skill["key"]

                        self.combo_items.append(
                            {
                                "type": "skill",
                                "id": skill["id"],
                                "name": skill["name"],
                                "key": skill_key,
                                "color": self.skill_loader.get_skill_color(skill),
                                "hold": skill.get("hold", 0.05),
                                "click_count": skill.get("click_count", 1),
                                "weapon": skill.get("weapon"),
                                "modifiers": skill.get("modifiers", []),
                                "description": skill.get("description", ""),
                                "image": skill.get("image", ""),
                                "countdown": skill.get("countdown", 0),
                            }
                        )

                    self.refresh_timeline()

        self.drag_data["skill_data"] = None
        self.drag_data["is_action"] = False

    def _create_drag_ghost(self, skill, event):
        """Create floating ghost"""
        self.drag_data["ghost"] = tk.Toplevel(self)
        self.drag_data["ghost"].overrideredirect(True)
        self.drag_data["ghost"].attributes("-alpha", 0.8)
        self.drag_data["ghost"].attributes("-topmost", True)

        # Get color - action items have color directly, skills use skill_loader
        if skill.get("is_action"):
            color = skill.get("color", "#9b59b6")
        else:
            color = self.skill_loader.get_skill_color(skill)

        f = tk.Frame(self.drag_data["ghost"], bg=color, bd=2, relief="solid")
        f.pack()

        if skill["id"] in self.image_cache:
            tk.Label(f, image=self.image_cache[skill["id"]], bg=color).pack(
                side="left", padx=2
            )

        tk.Label(
            f, text=skill["name"], fg="white", bg=color, font=FONTS["bold"], padx=5
        ).pack(side="left")

        self.drag_data["ghost"].geometry(f"+{event.x_root+10}+{event.y_root+10}")

    def _is_over_timeline(self, event) -> bool:
        """Check if over timeline"""
        tl_x = self.timeline_canvas.winfo_rootx()
        tl_y = self.timeline_canvas.winfo_rooty()
        tl_w = self.timeline_canvas.winfo_width()
        tl_h = self.timeline_canvas.winfo_height()
        return (
            tl_x <= event.x_root <= tl_x + tl_w and tl_y <= event.y_root <= tl_y + tl_h
        )

    def on_timeline_click(self, event):
        """Start dragging timeline item"""
        x, y = self.timeline_canvas.canvasx(event.x), self.timeline_canvas.canvasy(
            event.y
        )

        items = self.timeline_canvas.find_closest(x, y)
        if items:
            tags = self.timeline_canvas.gettags(items[0])
            for t in tags:
                if t.startswith("del_"):
                    return

        for x1, y1, x2, y2, idx in self.item_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.timeline_drag["index"] = idx
                self.timeline_drag["start_x"] = event.x
                self.timeline_drag["start_y"] = event.y

                tag = f"item_{idx}"
                for item_id in self.timeline_canvas.find_withtag(tag):
                    if self.timeline_canvas.type(item_id) == "rectangle":
                        self.timeline_canvas.itemconfig(
                            item_id, outline="#00ff00", width=3
                        )
                break

    def on_timeline_drag(self, event):
        """Drag timeline item"""
        if self.timeline_drag["index"] is None:
            return

        dx = abs(event.x - self.timeline_drag.get("start_x", event.x))
        dy = abs(event.y - self.timeline_drag.get("start_y", event.y))

        if dx > 5 or dy > 5:
            if not self.timeline_drag.get("ghost"):
                self._create_timeline_drag_ghost()

            self.timeline_drag["ghost"].geometry(
                f"+{event.x_root+10}+{event.y_root+10}"
            )
            self._update_timeline_drop_indicator(event)

    def _update_timeline_drop_indicator(self, event):
        """Show drop indicator"""
        self.timeline_canvas.delete("drop_indicator")

        drop_x, drop_y = self.timeline_canvas.canvasx(
            event.x
        ), self.timeline_canvas.canvasy(event.y)
        current_idx = self.timeline_drag["index"]

        self.timeline_drag["insert_before"] = None
        self.timeline_drag["insert_after"] = None

        for x1, y1, x2, y2, idx in self.item_rects:
            if idx == current_idx:
                continue

            if y1 <= drop_y <= y2:
                item_center_x = (x1 + x2) / 2

                if x1 - 15 <= drop_x <= item_center_x:
                    indicator_x = x1 - 4
                    self.timeline_canvas.create_rectangle(
                        indicator_x,
                        y1 - 2,
                        indicator_x + 4,
                        y2 + 2,
                        fill=colors["accent"],
                        outline=colors["accent"],
                        tags="drop_indicator",
                    )
                    self.timeline_drag["insert_before"] = idx
                    break
                elif item_center_x < drop_x <= x2 + 15:
                    indicator_x = x2 + 2
                    self.timeline_canvas.create_rectangle(
                        indicator_x,
                        y1 - 2,
                        indicator_x + 4,
                        y2 + 2,
                        fill=colors["accent"],
                        outline=colors["accent"],
                        tags="drop_indicator",
                    )
                    self.timeline_drag["insert_after"] = idx
                    break

    def _create_timeline_drag_ghost(self):
        """Create timeline drag ghost"""
        idx = self.timeline_drag["index"]
        item = self.combo_items[idx]

        self.timeline_drag["ghost"] = tk.Toplevel(self)
        self.timeline_drag["ghost"].overrideredirect(True)
        self.timeline_drag["ghost"].attributes("-alpha", 0.7)
        self.timeline_drag["ghost"].attributes("-topmost", True)

        if item["type"] == "delay":
            text = f"⏳ {item['value']:.2f}s"
            bg = colors["input_bg"]
        else:
            text = item["name"]
            bg = item.get("color", colors["accent"])

        tk.Label(
            self.timeline_drag["ghost"],
            text=text,
            bg=bg,
            fg="white",
            font=FONTS["bold"],
            padx=10,
            pady=5,
        ).pack()

    def on_timeline_drop(self, event):
        """Drop timeline item"""
        self.timeline_canvas.delete("drop_indicator")

        if self.timeline_drag["index"] is None:
            return

        src_idx = self.timeline_drag["index"]

        if self.timeline_drag.get("ghost"):
            self.timeline_drag["ghost"].destroy()
            self.timeline_drag["ghost"] = None

            target_idx = None

            if self.timeline_drag.get("insert_before") is not None:
                target_idx = self.timeline_drag["insert_before"]
                if src_idx < target_idx:
                    target_idx -= 1
            elif self.timeline_drag.get("insert_after") is not None:
                target_idx = self.timeline_drag["insert_after"]
                if src_idx > target_idx:
                    target_idx += 1

            if (
                target_idx is not None
                and target_idx != src_idx
                and 0 <= target_idx < len(self.combo_items)
            ):
                item = self.combo_items.pop(src_idx)
                self.combo_items.insert(target_idx, item)
                self.status_var.set(f"Moved item to position {target_idx + 1}")

        self.timeline_drag["index"] = None
        self.timeline_drag["insert_before"] = None
        self.timeline_drag["insert_after"] = None
        self.refresh_timeline()

    # === Actions ===

    def add_delay_item(self):
        """Add delay item"""
        delay = simpledialog.askfloat(
            "Add Delay",
            "Enter delay (seconds):",
            initialvalue=0.3,
            minvalue=0.01,
            maxvalue=10.0,
            parent=self,
        )
        if delay:
            self.combo_items.append({"type": "delay", "value": delay})
            self.refresh_timeline()

    def clear_combo(self):
        """Clear combo timeline"""
        self.combo_items = []
        if hasattr(self, "_variant_drag_count"):
            self._variant_drag_count = {}
        self.refresh_timeline()

    def edit_delay(self, idx):
        """Edit delay value"""
        if (
            0 <= idx < len(self.combo_items)
            and self.combo_items[idx]["type"] == "delay"
        ):
            current = self.combo_items[idx]["value"]
            new_val = simpledialog.askfloat(
                "Edit Delay",
                "Enter delay (seconds):",
                initialvalue=current,
                minvalue=0.01,
                maxvalue=10.0,
                parent=self,
            )
            if new_val:
                self.combo_items[idx]["value"] = new_val
                self.refresh_timeline()

    def edit_skill_hold(self, idx):
        """Edit skill hold duration"""
        if (
            0 <= idx < len(self.combo_items)
            and self.combo_items[idx]["type"] == "skill"
        ):
            item = self.combo_items[idx]
            current = item.get("hold", 0.05)
            new_val = simpledialog.askfloat(
                f"Edit Hold - {item.get('name', 'Skill')}",
                "Thời gian giữ phím (giây):",
                initialvalue=current,
                minvalue=0.01,
                maxvalue=5.0,
                parent=self,
            )
            if new_val is not None:
                self.combo_items[idx]["hold"] = new_val
                self.status_var.set(f"Updated hold to {new_val:.2f}s")
                self.refresh_timeline()

    def remove_item(self, idx):
        """Remove item from combo"""
        if 0 <= idx < len(self.combo_items):
            item = self.combo_items[idx]

            if item.get("type") == "skill" and hasattr(self, "_variant_drag_count"):
                combo_key = (item.get("weapon"), item.get("key"))
                if combo_key in self._variant_drag_count:
                    del self._variant_drag_count[combo_key]

            del self.combo_items[idx]
            self.refresh_timeline()

    def start_set_trigger(self):
        """Start setting trigger"""
        self.trigger_manager.start_setting_trigger()
        self.btn_trigger.configure(text="Press key...", kind="primary")
        self.status_var.set("Press any key or mouse button to set as trigger...")

    def _on_trigger_set(self, key_or_button):
        """Callback when trigger set"""
        name = TriggerManager.get_key_name(key_or_button)
        self.trigger_key_var.set(name)
        self.after(0, lambda: self.btn_trigger.configure(text=name, kind="secondary"))
        self.after(0, lambda: self.status_var.set(f"Trigger set to {name}"))

    def _on_trigger_press(self, key_or_button):
        """Callback when trigger pressed"""
        combo_data = self.combo_manager.get_active(key_or_button)
        if combo_data:
            mode = combo_data["settings"]["mode"]
            if mode == "hold":
                if not self.player.running:
                    self.after(0, lambda: self._play_combo(combo_data))
            else:
                if self.player.running:
                    self.after(0, self.player.stop)
                else:
                    self.after(0, lambda: self._play_combo(combo_data))

    def _on_trigger_release(self, key_or_button):
        """Callback when trigger released"""
        combo_data = self.combo_manager.get_active(key_or_button)
        if (
            combo_data
            and combo_data["settings"]["mode"] == "hold"
            and self.player.running
        ):
            self.after(0, self.player.stop)

    def test_combo(self):
        """Test play combo"""
        if not self.combo_items:
            messagebox.showwarning("Empty", "Add skills to the combo first!")
            return

        if self.player.running:
            self.player.stop()
            self.btn_play.configure(text="▶ Test")
        else:
            # Minimize parent window
            if isinstance(self.parent_window, tk.Toplevel):
                self.parent_window.iconify()
            self.btn_play.configure(text="⏹ Stop")
            self.player.play(
                self.combo_items, on_finish=self._on_test_finished, loop_count=1
            )

    def _on_test_finished(self):
        """Callback when test finished"""
        self.after(0, lambda: self.btn_play.configure(text="▶ Test"))
        if isinstance(self.parent_window, tk.Toplevel):
            self.after(0, self.parent_window.deiconify)

    def _play_combo(self, combo_data):
        """Play a combo"""
        items = combo_data["items"]
        mode = combo_data["settings"]["mode"]
        loop_count = 0 if mode in ("loop", "hold") else 1

        self.status_var.set(f"Playing: {combo_data['name']}")
        self.player.play(
            items, on_finish=lambda: self.status_var.set("Ready"), loop_count=loop_count
        )

    def add_to_active(self):
        """Add combo to active list"""
        if not self.combo_items:
            messagebox.showwarning("Empty", "Create a combo first!")
            return

        name = simpledialog.askstring("Combo Name", "Enter combo name:", parent=self)
        if not name:
            return

        trigger_code = self.trigger_manager.trigger_key_code
        trigger_name = self.trigger_key_var.get()

        # Normalize trigger for comparison (active_combos uses normalized string keys)
        normalized_trigger = self.combo_manager._normalize_trigger(trigger_code)
        if normalized_trigger in self.active_combos:
            if not messagebox.askyesno(
                "Confirm", f"Trigger '{trigger_name}' is already used. Overwrite?"
            ):
                return

        combo_data = {
            "name": name,
            "items": list(self.combo_items),
            "settings": {"mode": self.playback_mode_var.get(), "trigger": trigger_name},
        }

        self.combo_manager.add_active(trigger_code, combo_data)
        self.update_active_list()
        self.status_var.set(f"Added '{name}' to active combos")

    def clear_active_combos(self):
        """Clear all active combos"""
        self.combo_manager.clear_active()
        self.update_active_list()

    def _remove_active(self, trigger_code):
        """Remove active combo"""
        self.combo_manager.remove_active(trigger_code)
        self.update_active_list()

    def save_combo(self):
        """Save combo to file"""
        if not self.combo_items:
            messagebox.showwarning("Empty", "Create a combo first!")
            return

        filepath = filedialog.asksaveasfilename(
            initialdir=get_combos_dir(),
            defaultextension=".json",
            filetypes=[("Combo Files", "*.json")],
        )

        if filepath:
            settings = {
                "mode": self.playback_mode_var.get(),
                "trigger": self.trigger_key_var.get(),
            }
            if self.combo_manager.save_combo(filepath, self.combo_items, settings):
                self.status_var.set(f"Saved to {os.path.basename(filepath)}")

    def load_combo(self):
        """Load combo from file"""
        filepath = filedialog.askopenfilename(
            initialdir=get_combos_dir(), filetypes=[("Combo Files", "*.json")]
        )

        if filepath:
            data = self.combo_manager.load_combo(filepath)
            if data:
                self.combo_items = data.get("items", [])
                settings = data.get("settings", {})

                self.playback_mode_var.set(settings.get("mode", "once"))
                trigger = settings.get("trigger", "Button.x1")
                self.trigger_key_var.set(trigger)
                self.trigger_manager.trigger_key_code = (
                    TriggerManager.parse_trigger_string(trigger)
                )
                self.btn_trigger.configure(text=trigger)

                self.refresh_timeline()
                self.status_var.set(f"Loaded {os.path.basename(filepath)}")
            else:
                messagebox.showerror("Error", "Failed to load combo file")

    def on_close(self):
        """Handle window close - save state and keep combo services running in background"""
        # Save session state using the helper method
        self._save_session_state()

        # DON'T stop trigger_manager and player - they run in background
        # Active combos will continue to work even with UI closed
        # as long as the launcher is still running
        if self._toplevel_window and hasattr(self._toplevel_window, "destroy"):
            self._toplevel_window.destroy()

    def _open_settings(self):
        """Open settings dialog"""

        def on_save():
            self.render_palette()
            self.status_var.set("Settings saved!")

        SettingsDialog(self, on_save=on_save)
