"""
WWM Combo Settings Dialog - Modern Drag & Drop Keybinding UI
Features:
- Left panel with searchable key buttons
- Right panel with skill drop zones
- Drag & drop to assign keys to skills
"""

import tkinter as tk
from .tooltip import RichTooltip

# Import theme and components
try:
    from ..theme import colors, FONTS, ModernButton
    from ..components import FramelessWindow
except ImportError:
    import sys
    import os

    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from ui.theme import colors, FONTS, ModernButton
    from ui.components import FramelessWindow


# Available keys for binding - Complete list
AVAILABLE_KEYS = [
    # === MOUSE ===
    {"id": "lmb", "name": "LMB"},
    {"id": "rmb", "name": "RMB"},
    {"id": "mmb", "name": "MMB"},
    {"id": "mouse4", "name": "Mouse 4"},
    {"id": "mouse5", "name": "Mouse 5"},
    {"id": "x1", "name": "X1"},
    {"id": "x2", "name": "X2"},
    {"id": "scroll_up", "name": "Scroll Up"},
    {"id": "scroll_down", "name": "Scroll Down"},
    # === MODIFIERS ===
    {"id": "shift", "name": "SHIFT"},
    {"id": "ctrl", "name": "CTRL"},
    {"id": "alt", "name": "ALT"},
    {"id": "lshift", "name": "Left Shift"},
    {"id": "rshift", "name": "Right Shift"},
    {"id": "lctrl", "name": "Left Ctrl"},
    {"id": "rctrl", "name": "Right Ctrl"},
    {"id": "lalt", "name": "Left Alt"},
    {"id": "ralt", "name": "Right Alt"},
    # === SPECIAL KEYS ===
    {"id": "space", "name": "SPACE"},
    {"id": "tab", "name": "TAB"},
    {"id": "enter", "name": "ENTER"},
    {"id": "escape", "name": "ESC"},
    {"id": "backspace", "name": "Backspace"},
    {"id": "delete", "name": "Delete"},
    {"id": "insert", "name": "Insert"},
    {"id": "home", "name": "Home"},
    {"id": "end", "name": "End"},
    {"id": "pageup", "name": "Page Up"},
    {"id": "pagedown", "name": "Page Down"},
    {"id": "capslock", "name": "Caps Lock"},
    # === ARROW KEYS ===
    {"id": "up", "name": "↑ Up"},
    {"id": "down", "name": "↓ Down"},
    {"id": "left", "name": "← Left"},
    {"id": "right", "name": "→ Right"},
    # === FUNCTION KEYS ===
    {"id": "f1", "name": "F1"},
    {"id": "f2", "name": "F2"},
    {"id": "f3", "name": "F3"},
    {"id": "f4", "name": "F4"},
    {"id": "f5", "name": "F5"},
    {"id": "f6", "name": "F6"},
    {"id": "f7", "name": "F7"},
    {"id": "f8", "name": "F8"},
    {"id": "f9", "name": "F9"},
    {"id": "f10", "name": "F10"},
    {"id": "f11", "name": "F11"},
    {"id": "f12", "name": "F12"},
    # === NUMBERS ===
    {"id": "1", "name": "1"},
    {"id": "2", "name": "2"},
    {"id": "3", "name": "3"},
    {"id": "4", "name": "4"},
    {"id": "5", "name": "5"},
    {"id": "6", "name": "6"},
    {"id": "7", "name": "7"},
    {"id": "8", "name": "8"},
    {"id": "9", "name": "9"},
    {"id": "0", "name": "0"},
    # === LETTERS ===
    {"id": "a", "name": "A"},
    {"id": "b", "name": "B"},
    {"id": "c", "name": "C"},
    {"id": "d", "name": "D"},
    {"id": "e", "name": "E"},
    {"id": "f", "name": "F"},
    {"id": "g", "name": "G"},
    {"id": "h", "name": "H"},
    {"id": "i", "name": "I"},
    {"id": "j", "name": "J"},
    {"id": "k", "name": "K"},
    {"id": "l", "name": "L"},
    {"id": "m", "name": "M"},
    {"id": "n", "name": "N"},
    {"id": "o", "name": "O"},
    {"id": "p", "name": "P"},
    {"id": "q", "name": "Q"},
    {"id": "r", "name": "R"},
    {"id": "s", "name": "S"},
    {"id": "t", "name": "T"},
    {"id": "u", "name": "U"},
    {"id": "v", "name": "V"},
    {"id": "w", "name": "W"},
    {"id": "x", "name": "X"},
    {"id": "y", "name": "Y"},
    {"id": "z", "name": "Z"},
    # === SYMBOLS ===
    {"id": "`", "name": "` ~"},
    {"id": "-", "name": "- _"},
    {"id": "=", "name": "= +"},
    {"id": "[", "name": "[ {"},
    {"id": "]", "name": "] }"},
    {"id": "\\", "name": "\\ |"},
    {"id": ";", "name": "; :"},
    {"id": "'", "name": "' \""},
    {"id": ",", "name": ", <"},
    {"id": ".", "name": ". >"},
    {"id": "/", "name": "/ ?"},
    # === NUMPAD ===
    {"id": "num0", "name": "Num 0"},
    {"id": "num1", "name": "Num 1"},
    {"id": "num2", "name": "Num 2"},
    {"id": "num3", "name": "Num 3"},
    {"id": "num4", "name": "Num 4"},
    {"id": "num5", "name": "Num 5"},
    {"id": "num6", "name": "Num 6"},
    {"id": "num7", "name": "Num 7"},
    {"id": "num8", "name": "Num 8"},
    {"id": "num9", "name": "Num 9"},
    {"id": "numlock", "name": "Num Lock"},
    {"id": "numdivide", "name": "Num /"},
    {"id": "nummultiply", "name": "Num *"},
    {"id": "numminus", "name": "Num -"},
    {"id": "numplus", "name": "Num +"},
    {"id": "numenter", "name": "Num Enter"},
    {"id": "numdot", "name": "Num ."},
]

# Skills to bind
COMBAT_SKILLS = [
    ("skill_1", "Skill 1"),
    ("skill_2", "Skill 2"),
    ("light_attack", "Light Attack"),
    ("heavy_attack", "Heavy Attack"),
    ("charge_attack", "Charge Attack"),
    ("deflect", "Deflect"),
    ("defend", "Defend"),
    ("dodge", "Dodge"),
    ("jump", "Jump"),
    ("tab", "Tab"),
    ("switch_weapon", "Switch Weapon"),
]

MYSTIC_SKILLS = [
    ("mystic_skill_skill_1", "Mystic 1"),
    ("mystic_skill_skill_2", "Mystic 2"),
    ("mystic_skill_skill_3", "Mystic 3"),
    ("mystic_skill_skill_4", "Mystic 4"),
    ("mystic_skill_skill_5", "Mystic Alt 1"),
    ("mystic_skill_skill_6", "Mystic Alt 2"),
    ("mystic_skill_skill_7", "Mystic Alt 3"),
    ("mystic_skill_skill_8", "Mystic Alt 4"),
]

# Uniform key color
KEY_COLOR = "#4a5568"  # Gray color for all keys
KEY_HOVER_COLOR = "#5a6578"


class SettingsDialog:
    """Modern drag & drop keybinding settings dialog"""

    def __init__(self, parent, on_save=None):
        self.parent = parent
        self.on_save = on_save
        self.drag_data = {"key": None, "ghost": None}
        self.drop_zones = {}  # skill_id -> (frame, label)
        self.key_widgets = []  # List of key button widgets

        # Create frameless window with custom title bar
        self.dialog = FramelessWindow(
            parent, title="⚙ Keybinding Settings", icon_path=None
        )
        self.dialog.geometry("680x640")
        self.dialog.attributes("-topmost", True)

        # Center relative to parent's toplevel window
        self._center_on_parent()

        # Get settings service
        from services.user_settings_service import get_user_settings_service

        self.settings_service = get_user_settings_service()
        self.keybindings = self.settings_service.get_all_keybindings()

        self._setup_ui()

    def _center_on_parent(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()

        # Get the toplevel parent window
        parent = self.parent
        while parent and not isinstance(parent, (tk.Tk, tk.Toplevel)):
            parent = parent.master

        if parent:
            parent.update_idletasks()
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()

            x = parent_x + (parent_w - 680) // 2
            y = parent_y + (parent_h - 640) // 2

            screen_w = self.dialog.winfo_screenwidth()
            screen_h = self.dialog.winfo_screenheight()
            x = max(0, min(x, screen_w - 680))
            y = max(0, min(y, screen_h - 640))

            self.dialog.geometry(f"680x640+{x}+{y}")

    def _setup_ui(self):
        """Setup the main UI layout"""
        content = self.dialog.content_frame
        content.configure(bg=colors["bg"])

        # Main container
        main = tk.Frame(content, bg=colors["bg"])
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # === LEFT PANEL - Key Palette ===
        left_panel = tk.Frame(main, bg=colors["sidebar"], width=180)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)

        self._setup_key_palette(left_panel)

        # === RIGHT PANEL - Skill Bindings ===
        right_panel = tk.Frame(main, bg=colors["bg"])
        right_panel.pack(side="left", fill="both", expand=True)

        self._setup_skill_bindings(right_panel)

        # === BOTTOM - Buttons ===
        btn_frame = tk.Frame(content, bg=colors["bg"])
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        ModernButton(
            btn_frame,
            text="Reset Default",
            command=self._reset_defaults,
            kind="secondary",
            width=12,
        ).pack(side="left")

        ModernButton(
            btn_frame, text="Cancel", command=self._close, kind="secondary", width=10
        ).pack(side="right", padx=(5, 0))

        ModernButton(
            btn_frame,
            text="Save",
            command=self._save_settings,
            kind="primary",
            width=10,
        ).pack(side="right")

    def _setup_key_palette(self, parent):
        """Setup left panel with searchable keys"""
        # Header
        header = tk.Frame(parent, bg=colors["sidebar"])
        header.pack(fill="x", padx=8, pady=(8, 5))

        tk.Label(
            header,
            text="🎮 Available Keys",
            font=FONTS["bold"],
            bg=colors["sidebar"],
            fg=colors["fg"],
        ).pack(anchor="w")

        # Search box
        search_frame = tk.Frame(parent, bg=colors["sidebar"])
        search_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.search_var = tk.StringVar()
        self._is_placeholder = True  # Set before creating entry

        self.search_entry = tk.Entry(
            search_frame,
            font=FONTS["body"],
            bg=colors["input_bg"],
            fg=colors["fg_dim"],
            insertbackground=colors["fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=colors["accent"],
        )
        self.search_entry.pack(fill="x", ipady=5)
        self.search_entry.insert(0, "🔍 Search...")
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # Bind KeyRelease for search instead of trace (more reliable)
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_keys())

        # Key list with hidden scrollbar
        list_frame = tk.Frame(parent, bg=colors["sidebar"])
        list_frame.pack(fill="both", expand=True, padx=8)

        self.keys_canvas = tk.Canvas(
            list_frame,
            bg=colors["sidebar"],
            highlightthickness=0,
        )
        self.keys_canvas.pack(fill="both", expand=True)

        self.keys_container = tk.Frame(self.keys_canvas, bg=colors["sidebar"])
        self.canvas_window = self.keys_canvas.create_window(
            (0, 0), window=self.keys_container, anchor="nw"
        )

        def configure_scroll(event):
            self.keys_canvas.configure(scrollregion=self.keys_canvas.bbox("all"))

        def configure_canvas(event):
            self.keys_canvas.itemconfig(self.canvas_window, width=event.width)

        self.keys_container.bind("<Configure>", configure_scroll)
        self.keys_canvas.bind("<Configure>", configure_canvas)

        # Mouse wheel scroll (hidden scrollbar)
        def on_mousewheel(event):
            self.keys_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.keys_canvas.bind("<MouseWheel>", on_mousewheel)
        self.keys_container.bind("<MouseWheel>", on_mousewheel)
        list_frame.bind("<MouseWheel>", on_mousewheel)

        # Populate keys after a short delay to ensure canvas is ready
        self.dialog.after(50, self._populate_keys)

        # Hint at bottom
        hint_frame = tk.Frame(parent, bg=colors["card"])
        hint_frame.pack(fill="x", padx=8, pady=8)

        tk.Label(
            hint_frame,
            text="⟵ Drag keys to assign →",
            font=FONTS["small"],
            bg=colors["card"],
            fg=colors["accent"],
        ).pack(pady=6)

    def _on_search_focus_in(self, event):
        """Handle search focus in"""
        if self._is_placeholder:
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=colors["fg"])
            self._is_placeholder = False

    def _on_search_focus_out(self, event):
        """Handle search focus out"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "🔍 Search...")
            self.search_entry.config(fg=colors["fg_dim"])
            self._is_placeholder = True

    def _populate_keys(self, filter_text=""):
        """Populate key buttons"""
        # Clear existing
        for widget in self.keys_container.winfo_children():
            widget.destroy()
        self.key_widgets = []

        filter_lower = filter_text.lower().strip()
        if filter_lower == "🔍 search..." or filter_lower == "":
            filter_lower = ""

        for key_data in AVAILABLE_KEYS:
            if (
                filter_lower
                and filter_lower not in key_data["name"].lower()
                and filter_lower not in key_data["id"].lower()
            ):
                continue

            btn_frame = tk.Frame(self.keys_container, bg=colors["sidebar"])
            btn_frame.pack(fill="x", pady=2)

            # Create draggable key button with uniform color
            key_btn = tk.Frame(
                btn_frame,
                bg=KEY_COLOR,
                cursor="hand2",
            )
            key_btn.pack(fill="x", padx=2, ipady=4)

            # Drag grip
            grip = tk.Label(
                key_btn,
                text="⋮⋮",
                font=("Arial", 10),
                bg=KEY_COLOR,
                fg="#a0aec0",
            )
            grip.pack(side="left", padx=(5, 0))

            # Key name
            name_label = tk.Label(
                key_btn,
                text=key_data["name"],
                font=FONTS["bold"],
                bg=KEY_COLOR,
                fg="white",
            )
            name_label.pack(side="left", padx=8, pady=2)

            # Store key data reference
            key_btn._key_data = key_data

            # Bind drag events
            for widget in [key_btn, grip, name_label]:
                widget.bind(
                    "<ButtonPress-1>",
                    lambda e, k=key_data: self._on_key_drag_start(e, k),
                )
                widget.bind("<B1-Motion>", self._on_key_drag_motion)
                widget.bind("<ButtonRelease-1>", self._on_key_drag_end)
                widget.bind(
                    "<MouseWheel>",
                    lambda e: self.keys_canvas.yview_scroll(
                        int(-1 * (e.delta / 120)), "units"
                    ),
                )

            # Hover effect
            def on_enter(e, btn=key_btn):
                btn.configure(bg=KEY_HOVER_COLOR)
                for child in btn.winfo_children():
                    child.configure(bg=KEY_HOVER_COLOR)

            def on_leave(e, btn=key_btn):
                btn.configure(bg=KEY_COLOR)
                for child in btn.winfo_children():
                    child.configure(bg=KEY_COLOR)

            key_btn.bind("<Enter>", on_enter)
            key_btn.bind("<Leave>", on_leave)

            self.key_widgets.append(key_btn)

    def _filter_keys(self):
        """Filter keys based on search"""
        if self._is_placeholder:
            return
        search_text = self.search_entry.get()
        self._populate_keys(search_text)

    def _setup_skill_bindings(self, parent):
        """Setup right panel with skill drop zones"""
        # Simple frame layout (no canvas needed for small number of items)
        main_frame = tk.Frame(parent, bg=colors["bg"])
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Two columns
        columns_frame = tk.Frame(main_frame, bg=colors["bg"])
        columns_frame.pack(fill="both", expand=True)

        # Left column - Combat
        left_col = tk.Frame(columns_frame, bg=colors["bg"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            left_col,
            text="⚔ Combat Skills",
            font=FONTS["h2"],
            bg=colors["bg"],
            fg=colors["accent"],
        ).pack(anchor="w", pady=(0, 10))

        for skill_id, skill_name in COMBAT_SKILLS:
            self._create_skill_row(left_col, skill_id, skill_name)

        # Right column - Mystic
        right_col = tk.Frame(columns_frame, bg=colors["bg"])
        right_col.pack(side="left", fill="both", expand=True, padx=(10, 0))

        tk.Label(
            right_col,
            text="✨ Mystic Skills",
            font=FONTS["h2"],
            bg=colors["bg"],
            fg="#a855f7",  # Purple for mystic
        ).pack(anchor="w", pady=(0, 10))

        for skill_id, skill_name in MYSTIC_SKILLS:
            self._create_skill_row(right_col, skill_id, skill_name)

    def _create_skill_row(self, parent, skill_id, skill_name):
        """Create a skill row with drop zone"""
        row = tk.Frame(parent, bg=colors["bg"])
        row.pack(fill="x", pady=4)

        # Skill name
        tk.Label(
            row,
            text=skill_name,
            font=FONTS["body"],
            bg=colors["bg"],
            fg=colors["fg"],
            width=12,
            anchor="w",
        ).pack(side="left")

        # Drop zone container
        drop_container = tk.Frame(row, bg=colors["bg"])
        drop_container.pack(side="left", fill="x", expand=True, padx=5)

        # Drop zone
        current_key = self.keybindings.get(skill_id, "")

        # Fixed width drop zone
        DROP_ZONE_WIDTH = 120

        drop_zone = tk.Frame(
            drop_container,
            bg=colors["input_bg"] if current_key else colors["card"],
            highlightthickness=2,
            highlightbackground=colors["border"] if current_key else colors["fg_dim"],
            width=DROP_ZONE_WIDTH,
            height=32,
        )
        drop_zone.pack(side="left")
        drop_zone.pack_propagate(False)  # Prevent children from resizing

        # Key label inside drop zone - centered
        if current_key:
            # Inner frame for layout
            inner = tk.Frame(drop_zone, bg=colors["input_bg"])
            inner.pack(fill="both", expand=True)

            key_label = tk.Label(
                inner,
                text=current_key.upper(),
                font=FONTS["bold"],
                bg=colors["accent"],
                fg="white",
                padx=8,
            )
            key_label.pack(side="left", padx=4, pady=4)

            # Clear button
            clear_btn = tk.Label(
                inner,
                text="✕",
                font=("Arial", 9, "bold"),
                bg=colors["input_bg"],
                fg=colors["error"],
                cursor="hand2",
            )
            clear_btn.pack(side="right", padx=4)
            clear_btn.bind(
                "<Button-1>", lambda e, sid=skill_id: self._clear_binding(sid)
            )
        else:
            key_label = tk.Label(
                drop_zone,
                text="Drop key here",
                font=FONTS["small"],
                bg=colors["card"],
                fg=colors["fg_dim"],
            )
            key_label.pack(expand=True)

        # Store reference
        self.drop_zones[skill_id] = (drop_zone, key_label, drop_container)

        # Bind drop events
        for widget in [drop_zone, key_label]:
            widget.bind("<Enter>", lambda e, dz=drop_zone: self._on_drop_zone_enter(dz))
            widget.bind(
                "<Leave>",
                lambda e, dz=drop_zone, sid=skill_id: self._on_drop_zone_leave(dz, sid),
            )

    def _on_key_drag_start(self, event, key_data):
        """Start dragging a key"""
        self.drag_data["key"] = key_data

        # Create ghost
        ghost = tk.Toplevel(self.dialog)
        ghost.overrideredirect(True)
        ghost.attributes("-alpha", 0.85)
        ghost.attributes("-topmost", True)

        ghost_frame = tk.Frame(ghost, bg=colors["accent"], bd=2, relief="solid")
        ghost_frame.pack()

        tk.Label(
            ghost_frame,
            text=key_data["name"],
            font=FONTS["bold"],
            bg=colors["accent"],
            fg="white",
            padx=12,
            pady=6,
        ).pack()

        ghost.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        self.drag_data["ghost"] = ghost

    def _on_key_drag_motion(self, event):
        """Update ghost position during drag"""
        if self.drag_data.get("ghost"):
            self.drag_data["ghost"].geometry(
                f"+{event.x_root + 10}+{event.y_root + 10}"
            )

            # Check which drop zone we're over
            for skill_id, (drop_zone, _, _) in self.drop_zones.items():
                try:
                    x = drop_zone.winfo_rootx()
                    y = drop_zone.winfo_rooty()
                    w = drop_zone.winfo_width()
                    h = drop_zone.winfo_height()

                    if x <= event.x_root <= x + w and y <= event.y_root <= y + h:
                        drop_zone.configure(
                            highlightbackground=colors["accent"], highlightthickness=3
                        )
                    else:
                        current_key = self.keybindings.get(skill_id, "")
                        drop_zone.configure(
                            highlightbackground=(
                                colors["border"] if current_key else colors["fg_dim"]
                            ),
                            highlightthickness=2,
                        )
                except:
                    pass

    def _on_key_drag_end(self, event):
        """End drag and check for drop"""
        if self.drag_data.get("ghost"):
            self.drag_data["ghost"].destroy()
            self.drag_data["ghost"] = None

        key_data = self.drag_data.get("key")
        if not key_data:
            return

        # Check which drop zone we dropped on
        for skill_id, (drop_zone, key_label, container) in self.drop_zones.items():
            try:
                x = drop_zone.winfo_rootx()
                y = drop_zone.winfo_rooty()
                w = drop_zone.winfo_width()
                h = drop_zone.winfo_height()

                if x <= event.x_root <= x + w and y <= event.y_root <= y + h:
                    # Update binding
                    self.keybindings[skill_id] = key_data["id"]
                    self._update_drop_zone(skill_id, key_data)
                    break
            except:
                pass

        # Reset highlight
        for skill_id, (drop_zone, _, _) in self.drop_zones.items():
            current_key = self.keybindings.get(skill_id, "")
            drop_zone.configure(
                highlightbackground=(
                    colors["border"] if current_key else colors["fg_dim"]
                ),
                highlightthickness=2,
            )

        self.drag_data["key"] = None

    def _update_drop_zone(self, skill_id, key_data):
        """Update a drop zone with new key"""
        drop_zone, old_label, container = self.drop_zones[skill_id]

        # Clear old content
        for widget in drop_zone.winfo_children():
            widget.destroy()

        # Add new key
        drop_zone.configure(bg=colors["input_bg"], highlightbackground=colors["border"])

        # Inner frame for layout
        inner = tk.Frame(drop_zone, bg=colors["input_bg"])
        inner.pack(fill="both", expand=True)

        key_label = tk.Label(
            inner,
            text=key_data["name"],
            font=FONTS["bold"],
            bg=colors["accent"],
            fg="white",
            padx=8,
        )
        key_label.pack(side="left", padx=4, pady=4)

        # Add clear button
        clear_btn = tk.Label(
            inner,
            text="✕",
            font=("Arial", 9, "bold"),
            bg=colors["input_bg"],
            fg=colors["error"],
            cursor="hand2",
        )
        clear_btn.pack(side="right", padx=4)
        clear_btn.bind("<Button-1>", lambda e, sid=skill_id: self._clear_binding(sid))

        # Update reference
        self.drop_zones[skill_id] = (drop_zone, key_label, container)

    def _clear_binding(self, skill_id):
        """Clear a key binding"""
        self.keybindings[skill_id] = ""

        drop_zone, old_label, container = self.drop_zones[skill_id]

        # Clear content
        for widget in drop_zone.winfo_children():
            widget.destroy()

        # Reset to empty state
        drop_zone.configure(bg=colors["card"], highlightbackground=colors["fg_dim"])

        key_label = tk.Label(
            drop_zone,
            text="Drop key here",
            font=FONTS["small"],
            bg=colors["card"],
            fg=colors["fg_dim"],
        )
        key_label.pack(expand=True)

        self.drop_zones[skill_id] = (drop_zone, key_label, container)

    def _on_drop_zone_enter(self, drop_zone):
        """Highlight drop zone on hover"""
        if self.drag_data.get("key"):
            drop_zone.configure(
                highlightbackground=colors["accent"], highlightthickness=3
            )

    def _on_drop_zone_leave(self, drop_zone, skill_id):
        """Remove highlight when leaving drop zone"""
        current_key = self.keybindings.get(skill_id, "")
        drop_zone.configure(
            highlightbackground=colors["border"] if current_key else colors["fg_dim"],
            highlightthickness=2,
        )

    def _save_settings(self):
        """Save settings and close"""
        for skill_id, key in self.keybindings.items():
            self.settings_service.set_keybind(skill_id, key.strip() if key else "")
        self.settings_service.save_settings()

        if self.on_save:
            self.on_save()
        self._close()

    def _reset_defaults(self):
        """Reset to default keybindings"""
        self.settings_service.reset_to_defaults()
        self.keybindings = self.settings_service.get_all_keybindings()

        # Refresh all drop zones
        for skill_id in list(self.drop_zones.keys()):
            current_key = self.keybindings.get(skill_id, "")
            if current_key:
                # Find key data
                key_data = next(
                    (k for k in AVAILABLE_KEYS if k["id"] == current_key), None
                )
                if key_data:
                    self._update_drop_zone(skill_id, key_data)
                else:
                    # Custom key not in list
                    self._update_drop_zone(
                        skill_id, {"id": current_key, "name": current_key.upper()}
                    )
            else:
                self._clear_binding(skill_id)

    def _close(self):
        """Close the dialog"""
        try:
            self.dialog.destroy()
        except:
            pass
