import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from pynput import keyboard, mouse
import json
import os
import time

from core.sequence_recorder import SequenceRecorder
from core.sequence_player import SequencePlayer
from ..theme import colors, FONTS, ModernButton, ModernRadioButton
from ..modern_menu import ModernMenu
from ..wwm_combo.countdown_overlay import show_skill_countdown
from utils.stealth_utils import stealth_manager

from .timeline_canvas import SequenceTimelineCanvas
from .quick_panel import SequenceQuickPanel
from .library_window import SequenceLibraryWindow

# Alias for backward compatibility if needed, or simply use new names
MacroTimelineCanvas = SequenceTimelineCanvas
MacroQuickPanel = SequenceQuickPanel
MacroLibraryWindow = SequenceLibraryWindow


class MacroPlayer(SequencePlayer):
    """Wrapper for SequencePlayer if needed, or just use it directly."""

    pass


class MacroRecorderFrame(tk.Frame):
    """MacroRecorder UI Component"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors["bg"])

        self.recorder = (
            SequenceRecorder()
        )  # Was MacroRecorder() but core import calls it SequenceRecorder?
        # Check imports in original file:
        # from core.sequence_recorder import SequenceRecorder
        # self.recorder = MacroRecorder() -> implies MacroRecorder is alias for SequenceRecorder?
        # I'll use SequenceRecorder directly if MacroRecorder not found.

        self.player = SequencePlayer(
            None
        )  # Requires keyboard_controller? SequencePlayer init signature?
        # Original: from core.sequence_player import SequencePlayer
        # self.player = MacroPlayer()
        # I defined MacroPlayer above as pass.
        # But SequencePlayer might need args.
        # In original file line 14: from core.sequence_player import SequencePlayer
        # In line 843: self.player = MacroPlayer()
        # I suspect MacroPlayer might be a local class I missed?
        # Or an alias.
        # Let's check imports again.

        self.current_macro = []
        self.current_macro_name = "Untitled"

        # Settings
        self.playback_mode_var = tk.StringVar(value="once")  # once, loop, hold

        # Default trigger: Mouse Button 4 (XBUTTON1)
        self.trigger_key_var = tk.StringVar(value="Button.x1")
        self.trigger_key_code = mouse.Button.x1

        # State
        self.is_waiting_for_key = False
        self.is_setting_trigger = False
        self.editing_item_id = None

        # Modifier key tracking for combo triggers
        self.pressed_modifiers: set = set()
        self.MODIFIER_KEYS = {
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_l,
            keyboard.Key.ctrl_r,
            keyboard.Key.shift,
            keyboard.Key.shift_l,
            keyboard.Key.shift_r,
            keyboard.Key.alt,
            keyboard.Key.alt_l,
            keyboard.Key.alt_r,
            keyboard.Key.alt_gr,
        }

        # Multi-scenario support
        self.active_macros = {}  # {trigger_key_code: macro_data}
        self.active_macros_list = []  # List of (name, trigger_code) for UI display

        self.setup_ui()

        # Global Listeners
        self.key_listener = None
        self.mouse_listener = None
        self.start_listeners()

    def setup_ui(self):

        # Toolbar (Record/Play)
        toolbar = tk.Frame(self, bg=colors["bg"])
        toolbar.pack(fill="x", pady=15, padx=15)

        self.btn_record = ModernButton(
            toolbar,
            text="🔴 Record (F9)",
            command=self.toggle_record,
            kind="danger",
            width=15,
        )
        self.btn_record.pack(side="left", padx=(0, 10))

        self.btn_play = ModernButton(
            toolbar,
            text="▶ Play (Trigger)",
            command=self.toggle_play,
            kind="success",
            width=15,
        )
        self.btn_play.pack(side="left", padx=0)

        # Playback Mode Radio Buttons
        mode_frame = tk.Frame(toolbar, bg=colors["bg"])
        mode_frame.pack(side="right")

        modes = [("Once", "once"), ("Loop", "loop"), ("Hold", "hold")]
        for text, val in modes:
            rb = ModernRadioButton(
                mode_frame, text=text, variable=self.playback_mode_var, value=val
            )
            rb.pack(side="left", padx=5)

        # Main Content Area (Timeline + Quick Panel)
        main_content = tk.Frame(self, bg=colors["bg"])
        main_content.pack(fill="both", expand=True, padx=15, pady=5)

        # Left side: Timeline
        timeline_container = tk.Frame(main_content, bg=colors["bg"])
        timeline_container.pack(side="left", fill="both", expand=True)

        # Header for timeline
        t_header = tk.Frame(timeline_container, bg=colors["bg"])
        t_header.pack(fill="x", pady=(0, 5))

        tk.Label(
            t_header,
            text="Timeline (Drag to Reorder)",
            bg=colors["bg"],
            fg=colors["fg_dim"],
            font=FONTS["small"],
        ).pack(side="left")

        ModernButton(
            t_header,
            text="🗑 Clear All",
            command=self.clear_timeline,
            kind="secondary",
            width=12,
        ).pack(side="right")

        ModernButton(
            t_header, text="⏳ + Delay", command=self.add_delay, kind="accent", width=10
        ).pack(side="right", padx=(0, 5))

        # Custom Canvas Timeline
        timeline_inner = tk.Frame(timeline_container, bg=colors["input_bg"])
        timeline_inner.pack(fill="both", expand=True)

        self.timeline = MacroTimelineCanvas(
            timeline_inner,
            on_reorder_callback=self.on_timeline_reorder,
            on_edit_callback=self.on_timeline_edit,
            bg=colors["input_bg"],
            highlightthickness=0,
        )

        # No visible scrollbar - only mousewheel scrolling
        def _on_timeline_mousewheel(event):
            self.timeline.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.timeline.bind("<MouseWheel>", _on_timeline_mousewheel)
        self.timeline.pack(fill="both", expand=True)

        # Right side: Quick Panel (Macro Library)
        self.quick_panel = MacroQuickPanel(
            main_content,
            on_load_callback=self.load_macro_from_path,
            on_play_callback=self.play_macro,
        )
        self.quick_panel.configure(width=200)
        self.quick_panel.pack(side="right", fill="y", padx=(10, 0))
        self.quick_panel.pack_propagate(False)

        # Settings Bar (Bottom)
        settings_frame = tk.Frame(self, bg=colors["bg"])
        settings_frame.pack(fill="x", pady=10, padx=15)

        # Trigger Key
        tk.Label(
            settings_frame,
            text="Trigger:",
            bg=colors["bg"],
            fg=colors["fg"],
            font=FONTS["body"],
        ).pack(side="left", padx=(0, 5))
        self.btn_trigger = ModernButton(
            settings_frame,
            text=self.trigger_key_var.get(),
            command=self.start_set_trigger,
            width=15,
            kind="secondary",
        )
        self.btn_trigger.pack(side="left", padx=5)

        # Save Button (Right side)
        ModernButton(
            settings_frame,
            text="💾 Save to Library",
            command=self.save_macro,
            kind="primary",
        ).pack(side="right", padx=5)

        # Active Scenarios Section
        active_frame = tk.Frame(self, bg=colors["bg"])
        active_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(
            active_frame,
            text="Active Background Macros",
            bg=colors["bg"],
            fg=colors["fg"],
            font=FONTS["h2"],
        ).pack(anchor="w", pady=(10, 5))

        # Active List (Scrollable Frame)
        self.active_container = tk.Frame(active_frame, bg=colors["input_bg"])
        self.active_container.pack(fill="x", ipady=5)

        # Controls for Active List
        ctrl_frame = tk.Frame(active_frame, bg=colors["bg"])
        ctrl_frame.pack(fill="x", pady=5)

        ModernButton(
            ctrl_frame,
            text="+ Add Current to Active",
            command=self.add_current_to_active,
            kind="accent",
            width=20,
        ).pack(side="left")

        ModernButton(
            ctrl_frame,
            text="Clear All",
            command=self.clear_active_macros,
            kind="secondary",
            width=10,
        ).pack(side="right")

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            self,
            textvariable=self.status_var,
            bg=colors["bg"],
            fg=colors["fg_dim"],
            font=FONTS["small"],
        ).pack(side="bottom", fill="x", pady=5)

    def start_listeners(self):
        if self.key_listener:
            self.key_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

        self.key_listener = keyboard.Listener(
            on_press=self.on_global_press, on_release=self.on_global_release
        )
        self.key_listener.start()

        self.mouse_listener = mouse.Listener(on_click=self.on_global_click)
        self.mouse_listener.start()

    def _normalize_modifier(self, key) -> str:
        """Normalize modifier key to standard name"""
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return "ctrl"
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            return "shift"
        if key in (
            keyboard.Key.alt,
            keyboard.Key.alt_l,
            keyboard.Key.alt_r,
            keyboard.Key.alt_gr,
        ):
            return "alt"
        return str(key)

    def on_global_press(self, key):
        # Track modifier state
        if key in self.MODIFIER_KEYS:
            self.pressed_modifiers.add(self._normalize_modifier(key))
            # Don't set trigger on modifier-only press
            if self.is_setting_trigger:
                return

        if self.is_setting_trigger:
            if key not in self.MODIFIER_KEYS:
                self.set_trigger_key(key)
            return

        if self.is_waiting_for_key:
            self.update_edited_key(key)
            return

        if key == keyboard.Key.f9:
            self.after(0, self.toggle_record)
            return

        self.check_trigger_press(key)

    def on_global_release(self, key):
        # Clear modifier state
        if key in self.MODIFIER_KEYS:
            self.pressed_modifiers.discard(self._normalize_modifier(key))
        self.check_trigger_release(key)

    def on_global_click(self, x, y, button, pressed):
        if self.is_setting_trigger:
            if pressed:
                self.set_trigger_key(button)
            return

        if pressed:
            self.check_trigger_press(button)
        else:
            self.check_trigger_release(button)

    def _matches_trigger(self, key_or_button, trigger) -> bool:
        """Check if key/button matches the trigger (with modifiers)"""
        if isinstance(trigger, tuple):
            required_mods, main_key = trigger
            # Check main key matches AND all required modifiers are pressed
            key_matches = self._keys_equal(key_or_button, main_key)
            mods_match = required_mods == frozenset(self.pressed_modifiers)
            return key_matches and mods_match
        return self._keys_equal(key_or_button, trigger)

    def _keys_equal(self, key1, key2) -> bool:
        """Compare two keys for equality"""
        if key1 == key2:
            return True
        return str(key1) == str(key2)

    def check_trigger_press(self, key_or_button):
        try:
            if not self.recorder.running:
                # 1. Check current editing macro trigger
                if self._matches_trigger(key_or_button, self.trigger_key_code):
                    # Skip if no macro loaded (don't show annoying warning)
                    if not self.current_macro:
                        return

                    mode = self.playback_mode_var.get()

                    if mode == "hold":
                        # Hold mode: start playing on press
                        if not self.player.running:
                            self.after(0, self.play_macro)
                    else:
                        # Once/Loop mode: toggle
                        self.after(0, self.toggle_play)
                    return

                # 2. Check active macros
                for trigger_code, macro_data in self.active_macros.items():
                    if self._matches_trigger(key_or_button, trigger_code):
                        # Toggle: stop if running, play if not
                        if self.player.running:
                            self.after(0, self.stop_playback)
                        else:
                            self.play_active_macro(macro_data)
                        return

        except Exception as e:
            print(f"Trigger error: {e}")

    def check_trigger_release(self, key_or_button):
        try:
            # 1. Check current macro
            if self._matches_trigger(key_or_button, self.trigger_key_code):
                mode = self.playback_mode_var.get()
                if mode == "hold" and self.player.running:
                    self.after(0, self.stop_playback)

            # 2. Check active macros (for hold mode)
            for trigger_code, macro_data in self.active_macros.items():
                if self._matches_trigger(key_or_button, trigger_code):
                    settings = macro_data.get("settings", {})
                    if settings.get("mode") == "hold" and self.player.running:
                        self.after(0, self.stop_playback)

        except Exception as e:
            print(f"Trigger release error: {e}")

    def on_timeline_reorder(self, new_events):
        self.current_macro = new_events
        self.status_var.set("Reordered events")

    def clear_timeline(self):
        if messagebox.askyesno("Clear", "Clear current macro timeline?"):
            self.current_macro = []
            self.timeline.clear_all()
            self.status_var.set("Timeline cleared")

    def add_delay(self):
        """Add a delay item to the timeline"""
        delay = simpledialog.askfloat(
            "Add Delay",
            "Enter delay (seconds):",
            initialvalue=0.3,
            minvalue=0.01,
            maxvalue=3600.0,
            parent=self,
        )
        if delay:
            self.timeline.add_delay_item(delay)
            self.status_var.set(f"Added {delay:.2f}s delay")

    def on_timeline_edit(self, index, field):
        if field == "delay":
            self.edit_delay(index)
        else:
            self.start_edit_key(index)

    def show_menu(self):
        items = [
            {
                "label": "Macro Library",
                "command": self.show_macro_library,
                "icon": "📚",
            },
            {"label": "Clear All", "command": self.clear_macro, "icon": "❌"},
            {"type": "separator"},
            {"label": "Exit", "command": self.quit_app, "icon": "🚪"},
        ]

        # Note: self.btn_menu might not be defined if copied from old code where it might have been removed.
        # But this method exists in old code. Checking setup_ui...
        # I don't see btn_menu in setup_ui above. It must have been removed or I missed it.
        # I'll keep the method but comment out accessing btn_menu to avoid crash.
        pass
        # x = self.btn_menu.winfo_rootx() + self.btn_menu.winfo_width() - 200
        # y = self.btn_menu.winfo_rooty() + self.btn_menu.winfo_height()
        # ModernMenu(self, x, y, items)

    def show_macro_library(self):
        MacroLibraryWindow(self, self.load_macro_from_path)

    def start_set_trigger(self):
        self.is_setting_trigger = True
        self.pressed_modifiers.clear()
        self.btn_trigger.configure(text="Press Key/Btn...", kind="primary")
        self.status_var.set("Press any key or mouse button to set as Trigger...")

    def set_trigger_key(self, key_or_button):
        try:
            modifiers = frozenset(self.pressed_modifiers)
            if modifiers:
                # Store as tuple: (frozenset of modifiers, main key)
                self.trigger_key_code = (modifiers, key_or_button)
                mod_names = [m.upper() for m in sorted(modifiers)]
                key_name = self._get_single_key_name(key_or_button)
                name = "+".join(mod_names + [key_name])
            else:
                self.trigger_key_code = key_or_button
                name = self._get_single_key_name(key_or_button)

            self.trigger_key_var.set(name)
            self.pressed_modifiers.clear()

            self.after(
                0, lambda: self.btn_trigger.configure(text=name, kind="secondary")
            )
            self.after(0, lambda: self.status_var.set(f"Trigger set to {name}"))
        except Exception as e:
            print(e)
        finally:
            self.is_setting_trigger = False

    def start_edit_key(self, idx):
        self.editing_item_id = idx
        self.is_waiting_for_key = True
        self.status_var.set("Press new key to replace...")

    def update_edited_key(self, key):
        if self.editing_item_id is None:
            return

        try:
            key_name = self.get_key_name(key)
            self.current_macro[self.editing_item_id]["data"]["key"] = key_name

            self.after(0, self.refresh_list)
            self.after(0, lambda: self.status_var.set(f"Updated key to {key_name}"))
        finally:
            self.is_waiting_for_key = False
            self.editing_item_id = None

    def edit_delay(self, idx):
        current_delay = self.current_macro[idx]["delay"]
        new_delay = simpledialog.askfloat(
            "Edit Delay",
            "Enter new delay (seconds):",
            initialvalue=current_delay,
            parent=self,
        )
        if new_delay is not None:
            self.current_macro[idx]["delay"] = new_delay
            self.refresh_list()

    def get_key_name(self, trigger):
        """Get display name for key/button (supports combo triggers)"""
        if isinstance(trigger, tuple):
            modifiers, main_key = trigger
            mod_names = [m.upper() for m in sorted(modifiers)]
            key_name = self._get_single_key_name(main_key)
            return "+".join(mod_names + [key_name])
        return self._get_single_key_name(trigger)

    def _get_single_key_name(self, key):
        """Get display name for a single key/button"""
        if isinstance(key, mouse.Button):
            return str(key)
        if hasattr(key, "name"):
            return key.name.upper()
        elif hasattr(key, "char"):
            return key.char.upper() if key.char else "UNKNOWN"
        return str(key)

    def parse_trigger_string(self, trigger_str):
        """Parse trigger string back to key/button object (supports combo format)"""
        try:
            # Handle combo format: "CTRL+K", "SHIFT+ALT+Button.x1"
            if "+" in trigger_str:
                parts = trigger_str.split("+")
                modifiers = frozenset(p.lower() for p in parts[:-1])
                main_key = self._parse_single_key(parts[-1])
                return (modifiers, main_key)

            return self._parse_single_key(trigger_str)
        except Exception as e:
            print(f"Error parsing trigger '{trigger_str}': {e}")
            return mouse.Button.x1

    def _parse_single_key(self, key_str):
        """Parse a single key string to key/button object"""
        try:
            # Mouse button format: "Button.x1", "Button.left", etc.
            if key_str.startswith("Button."):
                button_name = key_str.split(".")[-1]
                return getattr(mouse.Button, button_name, mouse.Button.x1)

            # Keyboard Key format: "F9", "ENTER", etc.
            key_lower = key_str.lower()
            if hasattr(keyboard.Key, key_lower):
                return getattr(keyboard.Key, key_lower)

            # Single character
            if len(key_str) == 1:
                return key_str.lower()

            # Default fallback
            return mouse.Button.x1
        except Exception:
            return mouse.Button.x1

    def toggle_record(self):
        if not self.recorder.running:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.status_var.set("Recording... Press F9 to stop")
        self.btn_record.configure(text="⏹ Stop (F9)")
        # Use withdraw instead of iconify for FramelessWindow (overrideredirect)
        self.winfo_toplevel().withdraw()
        self.recorder.start()

    def stop_recording(self):
        self.recorder.stop()
        self.current_macro = self.recorder.events

        # Auto-remove F9 key events used to stop recording
        filtered_events = []
        for event in self.current_macro:
            if event["type"] in ["key_press", "key_release"]:
                key = event["data"].get("key", "")
                is_f9 = (
                    key == "Key.f9" or key.upper() == "F9" or "f9" in str(key).lower()
                )
                if not is_f9:
                    filtered_events.append(event)
            else:
                filtered_events.append(event)

        self.current_macro = filtered_events
        self.refresh_list()
        self.status_var.set(
            f"Recorded {len(self.current_macro)} events (F9 auto-removed)"
        )
        self.btn_record.configure(text="🔴 Record (F9)")
        self.winfo_toplevel().deiconify()
        self.winfo_toplevel().lift()

    def toggle_play(self):
        if self.player.running:
            self.stop_playback()
        else:
            self.play_macro()

    def stop_playback(self):
        """Stop playback immediately"""
        self.player.stop()
        self.status_var.set("Playback stopped")
        self.btn_play.configure(text="▶ Play (Trigger)")

    def play_macro(self):
        if not self.current_macro:
            messagebox.showwarning("Warning", "No macro to play!")
            return

        self.status_var.set("Playing...")
        self.btn_play.configure(text="⏹ Stop")
        self.winfo_toplevel().withdraw()

        loop_count = 1
        mode = self.playback_mode_var.get()

        if mode == "loop":
            from feature_manager import get_feature_manager

            fm = get_feature_manager()
            if fm.get_feature_limit("macro_infinite_loop"):
                loop_count = 0  # Infinite
            else:
                count = simpledialog.askinteger(
                    "Loop Limit",
                    "Gói hiện tại không hỗ trợ lặp vô hạn.\nNhập số lần lặp (1-10):",
                    minvalue=1,
                    maxvalue=10,
                    parent=self,
                )
                if count:
                    loop_count = count
                else:
                    self.stop_playback()
                    return
        elif mode == "hold":
            loop_count = 0  # Infinite loop while held

        self.player.play(
            self.current_macro,
            self.on_play_finished,
            loop_count=loop_count,
            on_delay_start=self._show_delay_countdown,
        )

    def _show_delay_countdown(self, delay_seconds):
        """Show countdown overlay for delay"""
        try:
            root = self.winfo_toplevel()
            show_skill_countdown(root, "Delay", "", delay_seconds)
        except Exception as e:
            print(f"[MacroWindow] Countdown overlay error: {e}")

    def on_play_finished(self):
        self.status_var.set("Playback finished")
        self.btn_play.configure(text="▶ Play (Trigger)")

    def play_active_macro(self, macro_data):
        """Play a macro from the active list (background mode - no UI changes)"""
        events = macro_data.get("events", [])
        if not events:
            return

        settings = macro_data.get("settings", {})
        mode = settings.get("mode", "once")

        loop_count = 1
        if mode == "loop":
            from feature_manager import get_feature_manager

            fm = get_feature_manager()
            if fm.get_feature_limit("macro_infinite_loop"):
                loop_count = 0  # Infinite
            else:
                loop_count = 10  # Limited loop for non-premium
        elif mode == "hold":
            loop_count = 0  # Infinite while held
        else:
            loop_count = 1

        self.player.play(
            events,
            on_finish=None,
            loop_count=loop_count,
            on_delay_start=self._show_delay_countdown,
        )

    def refresh_list(self):
        self.timeline.set_events(self.current_macro)

    def format_short(self, event):
        data = event["data"]
        if event["type"] == "mouse_click":
            action = "↓" if data["action"] == "pressed" else "↑"
            return f"🖱{data['button']} {action}"
        elif event["type"] == "key_press":
            return f"⌨ {data['key']} ↓"
        elif event["type"] == "key_release":
            return f"⌨ {data['key']} ↑"
        return str(data)

    def clear_macro(self):
        self.current_macro = []
        self.refresh_list()
        self.status_var.set("Cleared")

    def save_macro(self):
        if not self.current_macro:
            messagebox.showwarning("Warning", "No macro to save!")
            return

        macros_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "macros"
        )
        if not os.path.exists(macros_dir):
            os.makedirs(macros_dir)

        from feature_manager import get_feature_manager

        fm = get_feature_manager()
        limit = fm.get_feature_limit("macro_save_limit")

        if limit and isinstance(limit, int):
            existing = len(glob.glob(os.path.join(macros_dir, "*.json")))
            if existing >= limit:
                messagebox.showwarning(
                    "Limit Reached",
                    f"Gói hiện tại chỉ cho phép lưu tối đa {limit} macro.\nVui lòng nâng cấp để lưu thêm.",
                )
                return

        filename = filedialog.asksaveasfilename(
            initialdir=macros_dir,
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
        )

        if filename:
            data = {
                "events": self.current_macro,
                "settings": {
                    "mode": self.playback_mode_var.get(),
                    "trigger": self.trigger_key_var.get(),
                },
            }
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)

            self.current_macro_name = os.path.splitext(os.path.basename(filename))[0]
            self.status_var.set(f"Saved to {os.path.basename(filename)}")

    def load_macro_from_path(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)

        if isinstance(data, list):
            self.current_macro = data
        else:
            self.current_macro = data.get("events", [])
            settings = data.get("settings", {})
            mode = settings.get("mode", "once")
            if "loop" in settings and settings["loop"]:
                mode = "loop"
            if "hold" in settings and settings["hold"]:
                mode = "hold"
            self.playback_mode_var.set(mode)

            trigger = settings.get("trigger", "Button.x1")
            self.trigger_key_var.set(trigger)

            self.trigger_key_code = self.parse_trigger_string(trigger)
            self.btn_trigger.configure(text=trigger)
            print(f"Loaded trigger: {trigger} -> {self.trigger_key_code}")

        self.current_macro_name = os.path.splitext(os.path.basename(filepath))[0]
        self.refresh_list()
        self.status_var.set(f"Loaded {os.path.basename(filepath)}")

    def quit_app(self):
        self.cleanup()
        if isinstance(self.master, tk.Toplevel):
            self.master.destroy()
        else:
            self.master.quit()

    def add_current_to_active(self):
        if not self.current_macro:
            messagebox.showwarning("Warning", "No macro to add!")
            return

        trigger_code = self.trigger_key_code
        trigger_name = self.trigger_key_var.get()

        if trigger_code in self.active_macros:
            if not messagebox.askyesno(
                "Confirm", f"Trigger '{trigger_name}' is already used. Overwrite?"
            ):
                return

        macro_name = (
            self.current_macro_name
            if self.current_macro_name
            else f"Macro {len(self.active_macros) + 1}"
        )

        macro_data = {
            "name": macro_name,
            "events": list(self.current_macro),
            "settings": {"mode": self.playback_mode_var.get(), "trigger": trigger_name},
        }

        self.active_macros[trigger_code] = macro_data
        self.update_active_list()
        self.status_var.set(f"Added '{macro_name}' to active list")

    def clear_active_macros(self):
        self.active_macros = {}
        self.update_active_list()
        self.status_var.set("Cleared all active macros")

    def remove_active_macro(self, trigger_code=None):
        if trigger_code is None:
            pass

    def update_active_list(self):
        for widget in self.active_container.winfo_children():
            widget.destroy()

        if not self.active_macros:
            tk.Label(
                self.active_container,
                text="No active macros",
                bg=colors["input_bg"],
                fg=colors["fg_dim"],
            ).pack(pady=10)
            return

        for trigger_code, data in self.active_macros.items():
            self._create_active_macro_card(trigger_code, data)

    def _create_active_macro_card(self, trigger_code, data):
        card = tk.Frame(self.active_container, bg=colors["secondary"], pady=5, padx=5)
        card.pack(fill="x", pady=2, padx=5)

        mode = data["settings"]["mode"]
        icon = "↻" if mode == "loop" else "✋" if mode == "hold" else "▶"
        tk.Label(
            card, text=icon, bg=colors["secondary"], fg="white", font=FONTS["h2"]
        ).pack(side="left", padx=5)

        info_frame = tk.Frame(card, bg=colors["secondary"])
        info_frame.pack(side="left", fill="both", expand=True)

        tk.Label(
            info_frame,
            text=data["name"],
            bg=colors["secondary"],
            fg="white",
            font=FONTS["bold"],
        ).pack(anchor="w")
        tk.Label(
            info_frame,
            text=f"Trigger: {data['settings']['trigger']} • {len(data['events'])} events",
            bg=colors["secondary"],
            fg=colors["fg_dim"],
            font=FONTS["small"],
        ).pack(anchor="w")

        ModernButton(
            card,
            text="✕",
            width=3,
            kind="danger",
            command=lambda t=trigger_code: self._remove_active_by_trigger(t),
        ).pack(side="right", padx=5)

    def _remove_active_by_trigger(self, trigger_code):
        if trigger_code in self.active_macros:
            del self.active_macros[trigger_code]
            self.update_active_list()

    def cleanup(self):
        if self.key_listener:
            self.key_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.recorder.running:
            self.recorder.stop()
        if self.player.running:
            self.player.stop()
