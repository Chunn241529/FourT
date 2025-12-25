"""
Macro Recorder UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pynput import keyboard, mouse
import json
import os
import threading
import time
import glob
from core.macro_recorder import MacroRecorder
from core.macro_player import MacroPlayer
from .theme import colors, FONTS, ModernButton
from .modern_menu import ModernMenu
from .i18n import t


class MacroLibraryWindow(tk.Toplevel):
    """Macro Library List UI"""

    def __init__(self, parent, on_select_callback):
        super().__init__(parent)
        self.on_select_callback = on_select_callback

        self.title("Macro Library")
        self.geometry("400x500")
        self.configure(bg=colors["bg"])

        # Apply theme and icon
        from .theme import apply_theme, set_window_icon

        apply_theme(self)
        set_window_icon(self)

        self.setup_ui()
        self.load_macro_list()

    def setup_ui(self):
        # Header
        header = tk.Frame(self, bg=colors["header"], height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Macro Library",
            font=FONTS["h2"],
            bg=colors["header"],
            fg=colors["fg"],
        ).pack(side="left", padx=10)

        # List
        list_frame = tk.Frame(self, bg=colors["bg"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.listbox = tk.Listbox(
            list_frame,
            bg=colors["input_bg"],
            fg=colors["fg"],
            font=FONTS["body"],
            selectmode="single",
            highlightthickness=0,
            borderwidth=0,
        )
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Double click to load
        self.listbox.bind("<Double-Button-1>", self.on_double_click)

        # Buttons
        btn_frame = tk.Frame(self, bg=colors["bg"])
        btn_frame.pack(fill="x", padx=10, pady=10)

        ModernButton(
            btn_frame, text="Load", command=self.load_selected, kind="primary"
        ).pack(side="right", padx=5)
        ModernButton(
            btn_frame, text="Cancel", command=self.destroy, kind="secondary"
        ).pack(side="right")

    def load_macro_list(self):
        # Find all JSON files in macros directory
        macros_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "macros")
        if not os.path.exists(macros_dir):
            os.makedirs(macros_dir)

        macro_files = glob.glob(os.path.join(macros_dir, "*.json"))

        for filepath in macro_files:
            filename = os.path.basename(filepath)
            self.listbox.insert("end", filename)

    def on_double_click(self, event):
        self.load_selected()

    def load_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            return

        filename = self.listbox.get(selection[0])
        macros_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "macros")
        filepath = os.path.join(macros_dir, filename)

        self.on_select_callback(filepath)
        self.destroy()


class MacroQuickPanel(tk.Frame):
    """
    Macro Quick List Panel - embedded in main UI
    - Single-click: Load macro to editor
    - Double-click: Play macro immediately
    - Delete icon: Remove macro from library
    """

    def __init__(
        self,
        parent,
        on_load_callback,
        on_play_callback,
        on_delete_callback=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors["bg"])
        self.on_load_callback = on_load_callback
        self.on_play_callback = on_play_callback
        self.on_delete_callback = on_delete_callback

        self.macros_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "macros"
        )
        self.macro_files = []  # List of (filename, filepath)

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # Header with title and refresh button
        header = tk.Frame(self, bg=colors["header"], height=35)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📚 Library",
            font=FONTS["bold"],
            bg=colors["header"],
            fg=colors["fg"],
        ).pack(side="left", padx=8, pady=5)

        # Refresh button
        refresh_btn = tk.Label(
            header,
            text="🔄",
            font=FONTS["body"],
            bg=colors["header"],
            fg=colors["fg"],
            cursor="hand2",
        )
        refresh_btn.pack(side="right", padx=8)
        refresh_btn.bind("<Button-1>", lambda e: self.refresh_list())

        # Use ScrollableFrame for hidden scrollbar effect
        from .theme import ScrollableFrame

        self.scroll_frame = ScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True)

        # Items frame is inside the scrollable frame
        self.items_frame = self.scroll_frame.inner_frame

    def refresh_list(self):
        # Clear current items
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        self.macro_files = []

        if not os.path.exists(self.macros_dir):
            os.makedirs(self.macros_dir)
            return

        # Load keybindings info
        keybindings = {}
        keybindings_file = os.path.join(self.macros_dir, "keybindings.json")
        if os.path.exists(keybindings_file):
            try:
                with open(keybindings_file, "r") as f:
                    keybindings = json.load(f)
            except:
                pass

        # Get all macro files
        macro_files = glob.glob(os.path.join(self.macros_dir, "*.json"))
        macro_files = [f for f in macro_files if not f.endswith("keybindings.json")]

        if not macro_files:
            # Empty state
            tk.Label(
                self.items_frame,
                text="Chưa có macro nào",
                bg=colors["bg"],
                fg=colors["fg_dim"],
                font=FONTS["small"],
            ).pack(pady=20)
            return

        for filepath in sorted(macro_files):
            filename = os.path.basename(filepath)
            self.macro_files.append((filename, filepath))

            # Get trigger info
            binding = keybindings.get(filename, {})
            trigger = binding.get("key", "") if isinstance(binding, dict) else binding

            # Create item card
            self._create_item(filename, filepath, trigger)

    def _create_item(self, filename, filepath, trigger):
        """Create a clickable macro item with delete button"""
        # Card style: darker background, small padding
        card_bg = colors["sidebar"]
        hover_bg = colors["sidebar_active"]

        item = tk.Frame(self.items_frame, bg=card_bg, cursor="hand2")
        item.pack(fill="x", padx=5, pady=2)  # Add spacing between items

        # Hover effect
        def on_enter(e):
            item.configure(bg=hover_bg)
            for child in item.winfo_children():
                if hasattr(child, "configure"):
                    try:
                        child.configure(bg=hover_bg)
                    except:
                        pass
                for subchild in child.winfo_children():
                    if hasattr(subchild, "configure"):
                        try:
                            subchild.configure(bg=hover_bg)
                        except:
                            pass

        def on_leave(e):
            item.configure(bg=card_bg)
            for child in item.winfo_children():
                if hasattr(child, "configure"):
                    try:
                        child.configure(bg=card_bg)
                    except:
                        pass
                for subchild in child.winfo_children():
                    if hasattr(subchild, "configure"):
                        try:
                            subchild.configure(bg=card_bg)
                        except:
                            pass

        item.bind("<Enter>", on_enter)
        item.bind("<Leave>", on_leave)

        # Single click to load
        item.bind("<Button-1>", lambda e, fp=filepath: self._on_single_click(fp))

        # Double click to play
        item.bind("<Double-Button-1>", lambda e, fp=filepath: self._on_double_click(fp))

        # Content frame
        content = tk.Frame(item, bg=card_bg)
        content.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        content.bind("<Button-1>", lambda e, fp=filepath: self._on_single_click(fp))
        content.bind(
            "<Double-Button-1>", lambda e, fp=filepath: self._on_double_click(fp)
        )

        # Macro name (without .json)
        name = filename.replace(".json", "")
        name_label = tk.Label(
            content,
            text=name,
            font=FONTS["bold"],
            bg=card_bg,
            fg=colors["fg"],
            anchor="w",
        )
        name_label.pack(fill="x")
        name_label.bind("<Button-1>", lambda e, fp=filepath: self._on_single_click(fp))
        name_label.bind(
            "<Double-Button-1>", lambda e, fp=filepath: self._on_double_click(fp)
        )

        # Trigger info (if set)
        if trigger:
            trigger_label = tk.Label(
                content,
                text=f"⌨ {trigger}",
                font=FONTS["small"],
                bg=card_bg,
                fg=colors["accent"],
            )
            trigger_label.pack(anchor="w", pady=(2, 0))
            trigger_label.bind(
                "<Button-1>", lambda e, fp=filepath: self._on_single_click(fp)
            )
            trigger_label.bind(
                "<Double-Button-1>", lambda e, fp=filepath: self._on_double_click(fp)
            )

        # Delete button (right side, vertically centered)
        # Using a frame to center the button
        btn_frame = tk.Frame(item, bg=card_bg)
        btn_frame.pack(side="right", fill="y", padx=2)

        delete_btn = tk.Label(
            btn_frame,
            text="✕",
            font=FONTS["small"],
            bg=card_bg,
            fg=colors["fg_dim"],
            cursor="hand2",
        )
        delete_btn.pack(side="right", padx=5, pady=5)

        # Delete button specific hover
        def on_del_enter(e):
            delete_btn.configure(fg=colors["danger"], bg=hover_bg)

        def on_del_leave(e):
            delete_btn.configure(fg=colors["fg_dim"], bg=card_bg)  # revert to dim

        delete_btn.bind("<Enter>", on_del_enter)
        delete_btn.bind("<Leave>", on_del_leave)
        delete_btn.bind(
            "<Button-1>", lambda e, fp=filepath, fn=filename: self._on_delete(fp, fn)
        )

    def _on_single_click(self, filepath):
        """Load macro to editor"""
        if self.on_load_callback:
            self.on_load_callback(filepath)

    def _on_double_click(self, filepath):
        """Load and play macro immediately"""
        if self.on_load_callback:
            self.on_load_callback(filepath)
        # Small delay to ensure load completes
        self.after(
            100, lambda: self.on_play_callback() if self.on_play_callback else None
        )

    def _on_delete(self, filepath, filename):
        """Delete macro file"""
        if messagebox.askyesno(
            "Xác nhận", f"Xóa macro '{filename.replace('.json', '')}'?"
        ):
            try:
                os.remove(filepath)
                if self.on_delete_callback:
                    self.on_delete_callback(filepath)
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa macro: {e}")


class MacroTimelineCanvas(tk.Canvas):
    """
    Custom Canvas for rendering macro events with:
    - Independent Delay dragging
    - Delete event button
    - Wrapping layout (flow)
    - Drag and Drop reordering
    - Modern visual style
    """

    def __init__(self, parent, on_reorder_callback, on_edit_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_reorder_callback = on_reorder_callback
        self.on_edit_callback = on_edit_callback
        self.events = []
        self.ui_items = []  # Flattened list: [{'type': 'delay'/'event', 'data': ...}]

        # Style config
        self.item_height = 36
        self.item_padding = 8
        self.row_spacing = 15
        self.bg_color = colors["bg"]

        # Drag state
        self.drag_data = {
            "item": None,
            "x": 0,
            "y": 0,
            "index": None,
            "start_x": 0,
            "start_y": 0,
            "dragging": False,
        }
        self.drop_indicator_id = None
        self.drag_threshold = 5  # Minimum pixels to start drag

        # Bindings
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_drop)
        self.bind("<Configure>", self.on_resize)

    def set_events(self, events):
        self.events = events
        self.flatten_events()
        self.redraw()

    def flatten_events(self):
        """Flatten events into UI items (Delay separate from Event)"""
        self.ui_items = []
        for evt in self.events:
            # 1. Add delay item if exists
            if evt["delay"] > 0:
                self.ui_items.append({"ui_type": "delay", "value": evt["delay"]})

            # 2. Add event item
            # We treat the event data as the item, ignoring its delay field during UI manipulation
            self.ui_items.append({"ui_type": "event", "data": evt})

    def reconstruct_events(self):
        """Reconstruct event list from UI items"""
        new_events = []
        pending_delay = 0.0

        for item in self.ui_items:
            if item["ui_type"] == "delay":
                pending_delay += item["value"]
            elif item["ui_type"] == "event":
                evt = item["data"].copy()
                evt["delay"] = pending_delay
                new_events.append(evt)
                pending_delay = 0.0  # Consumed

        # pending_delay at the end is discarded (or could be trailing wait)
        return new_events

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        if width < 100:
            width = 600

        x = 10
        y = 15

        # Hit detection rects: (x1, y1, x2, y2, ui_index)
        self.item_rects = []

        for i, item in enumerate(self.ui_items):
            if item["ui_type"] == "delay":
                # Draw Delay Chip
                text = f"{item['value']:.2f}s ⏳"
                w = len(text) * 7 + 10

                if x + w > width - 10:
                    x = 10
                    y += self.item_height + self.row_spacing

                tag = f"item_{i}"
                # Background
                self.create_rectangle(
                    x,
                    y,
                    x + w,
                    y + self.item_height,
                    fill=colors["input_bg"],
                    outline=colors["border"],
                    tags=(tag, "draggable"),
                )
                # Text
                self.create_text(
                    x + w / 2,
                    y + self.item_height / 2,
                    text=text,
                    fill=colors["fg_dim"],
                    font=FONTS["small"],
                    tags=(tag, "draggable"),
                )

                self.item_rects.append((x, y, x + w, y + self.item_height, i))
                x += w + self.item_padding

            elif item["ui_type"] == "event":
                # Draw Event Box
                details = self._format_event_text(item["data"])
                w = len(details) * 7 + 40  # Extra space for delete button

                if x + w > width - 10:
                    x = 10
                    y += self.item_height + self.row_spacing

                tag = f"item_{i}"
                bg = self._get_event_color(item["data"])

                # Shadow
                self.create_rectangle(
                    x + 2,
                    y + 2,
                    x + w + 2,
                    y + self.item_height + 2,
                    fill=colors["bg"],
                    outline="",
                    tags=tag,
                )

                # Main Box
                self.create_rectangle(
                    x,
                    y,
                    x + w,
                    y + self.item_height,
                    fill=bg,
                    outline=colors["border"],
                    width=1,
                    tags=(tag, "draggable"),
                )

                # Text
                self.create_text(
                    x + (w - 20) / 2,
                    y + self.item_height / 2,
                    text=details,
                    fill="white",
                    font=FONTS["bold"],
                    tags=(tag, "draggable"),
                )

                # Delete Button [X]
                del_x = x + w - 15
                del_y = y + self.item_height / 2
                del_tag = f"del_{i}"

                self.create_text(
                    del_x,
                    del_y,
                    text="✕",
                    fill="white",
                    font=("Arial", 9, "bold"),
                    tags=(tag, del_tag),
                )

                # Bind delete specifically
                self.tag_bind(
                    del_tag, "<Button-1>", lambda e, idx=i: self.delete_item(idx)
                )
                # Hover effect for delete
                self.tag_bind(
                    del_tag,
                    "<Enter>",
                    lambda e, t=del_tag: self.itemconfig(t, fill=colors["danger"]),
                )
                self.tag_bind(
                    del_tag,
                    "<Leave>",
                    lambda e, t=del_tag: self.itemconfig(t, fill="white"),
                )

                self.item_rects.append((x, y, x + w, y + self.item_height, i))
                x += w + self.item_padding

        self.configure(scrollregion=(0, 0, width, y + self.item_height + 20))

    def _get_event_color(self, data):
        if data["type"] == "key_press":
            return colors["primary"]
        if data["type"] == "mouse_click":
            return colors["accent"]
        if data["type"] == "mouse_scroll":
            return "#17a2b8"
        return colors["secondary"]

    def _format_event_text(self, data):
        # Implementation same as before, simplified to take data dict
        evt = {"type": data["type"], "data": data["data"]}
        # reusing logic:
        d = evt["data"]
        if evt["type"] == "mouse_click":
            action = "↓" if d["action"] == "pressed" else "↑"
            return f"🖱{d['button']} {action}"
        elif evt["type"] == "mouse_scroll":
            dy = d.get("dy", 0)
            return f"🖱⟳ {'↑' if dy > 0 else '↓'}"
        elif evt["type"] == "key_press":
            return f"⌨ {d['key']} ↓"
        elif evt["type"] == "key_release":
            return f"⌨ {d['key']} ↑"
        return str(d)

    def on_resize(self, event):
        self.redraw()

    def on_click(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        # Check if clicked delete (handled by tag_bind) or edit delay
        items = self.find_closest(x, y)
        if not items:
            return
        item = items[0]
        tags = self.gettags(item)

        # If clicked delete button, ignore (propagation handled by return "break" but safe to check)
        for t in tags:
            if t.startswith("del_"):
                return

        # Edit Delay Check
        ui_idx = -1
        for t in tags:
            if t.startswith("item_"):
                try:
                    ui_idx = int(t.split("_")[1])
                except:
                    pass
                break

        if ui_idx >= 0 and ui_idx < len(self.ui_items):
            ui_item = self.ui_items[ui_idx]
            if ui_item["ui_type"] == "delay":
                # Store for potential drag, will edit on simple click (no drag)
                pass

        # Prepare for potential drag
        if "draggable" in tags and ui_idx >= 0:
            self.drag_data["item"] = item
            self.drag_data["index"] = ui_idx
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.drag_data["start_x"] = event.x
            self.drag_data["start_y"] = event.y
            self.drag_data["dragging"] = False

    def on_drag(self, event):
        if self.drag_data["index"] is None:
            return

        dx = abs(event.x - self.drag_data["start_x"])
        dy = abs(event.y - self.drag_data["start_y"])

        # Check if we should start dragging
        if not self.drag_data["dragging"]:
            if dx > self.drag_threshold or dy > self.drag_threshold:
                self.drag_data["dragging"] = True
                # Highlight the dragged item
                tag = f"item_{self.drag_data['index']}"
                for gi in self.find_withtag(tag):
                    if self.type(gi) == "rectangle" and "draggable" in self.gettags(gi):
                        self.itemconfig(gi, outline="white", width=2)
            else:
                return

        # Move the item being dragged
        move_dx = event.x - self.drag_data["x"]
        move_dy = event.y - self.drag_data["y"]
        self.move(f"item_{self.drag_data['index']}", move_dx, move_dy)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        # Update drop indicator
        self._update_drop_indicator(event)

    def _update_drop_indicator(self, event):
        """Show a visual indicator of where the item will be dropped"""
        # Remove old indicator
        if self.drop_indicator_id:
            self.delete(self.drop_indicator_id)
            self.drop_indicator_id = None

        drop_x, drop_y = self.canvasx(event.x), self.canvasy(event.y)
        current_idx = self.drag_data["index"]

        # Clear previous insert position markers
        self.drag_data["insert_before"] = None
        self.drag_data["insert_after"] = None

        # Find target position based on item positions
        for x1, y1, x2, y2, idx in self.item_rects:
            if idx == current_idx:
                continue

            # Check if cursor is near this item's row
            if y1 <= drop_y <= y2:
                item_center_x = (x1 + x2) / 2

                # Determine if we're on the left or right side of the item
                if x1 - 15 <= drop_x <= item_center_x:
                    # Show indicator on the left side of item
                    indicator_x = x1 - 4
                    self.drop_indicator_id = self.create_rectangle(
                        indicator_x,
                        y1 - 2,
                        indicator_x + 4,
                        y2 + 2,
                        fill=colors["accent"],
                        outline=colors["accent"],
                        tags="drop_indicator",
                    )
                    self.drag_data["insert_before"] = idx
                    break
                elif item_center_x < drop_x <= x2 + 15:
                    # Show indicator on the right side of item
                    indicator_x = x2 + 2
                    self.drop_indicator_id = self.create_rectangle(
                        indicator_x,
                        y1 - 2,
                        indicator_x + 4,
                        y2 + 2,
                        fill=colors["accent"],
                        outline=colors["accent"],
                        tags="drop_indicator",
                    )
                    self.drag_data["insert_after"] = idx
                    break

    def on_drop(self, event):
        idx = self.drag_data["index"]

        # Remove drop indicator
        if self.drop_indicator_id:
            self.delete(self.drop_indicator_id)
            self.drop_indicator_id = None

        if idx is not None:
            # If we weren't actually dragging, check for click-to-edit on delay
            if not self.drag_data["dragging"]:
                ui_item = self.ui_items[idx] if idx < len(self.ui_items) else None
                if ui_item and ui_item["ui_type"] == "delay":
                    # Edit Delay
                    new_val = simpledialog.askfloat(
                        "Delay",
                        "Enter delay (seconds):",
                        initialvalue=ui_item["value"],
                        parent=self,
                    )
                    if new_val is not None and new_val >= 0:
                        self.ui_items[idx]["value"] = new_val
                        self.update_output()
                self._reset_drag_state()
                return

            # Visual reset
            tag = f"item_{idx}"
            for gi in self.find_withtag(tag):
                if self.type(gi) == "rectangle" and "draggable" in self.gettags(gi):
                    self.itemconfig(gi, outline=colors["border"], width=1)

            # Reorder logic using insert position from drag indicator
            target_idx = None

            # Determine target based on insert markers
            if self.drag_data.get("insert_before") is not None:
                target_idx = self.drag_data["insert_before"]
                # Adjust if moving forward
                if idx < target_idx:
                    target_idx -= 1
            elif self.drag_data.get("insert_after") is not None:
                target_idx = self.drag_data["insert_after"]
                # Adjust if moving backward
                if idx > target_idx:
                    target_idx += 1

            if (
                target_idx is not None
                and target_idx != idx
                and 0 <= target_idx < len(self.ui_items)
            ):
                # Move in ui_items
                item = self.ui_items.pop(idx)
                self.ui_items.insert(target_idx, item)
                self.update_output()
            else:
                self.redraw()

        self._reset_drag_state()

    def _reset_drag_state(self):
        """Reset drag state to initial values"""
        self.drag_data = {
            "item": None,
            "x": 0,
            "y": 0,
            "index": None,
            "start_x": 0,
            "start_y": 0,
            "dragging": False,
        }

    def delete_item(self, index):
        if 0 <= index < len(self.ui_items):
            del self.ui_items[index]
            self.update_output()
        return "break"  # Stop event propagation

    def clear_all(self):
        self.ui_items = []
        self.update_output()

    def add_delay_item(self, delay_value):
        """Add a delay item to the timeline"""
        self.ui_items.append({"ui_type": "delay", "value": delay_value})
        self.update_output()

    def update_output(self):
        new_events = self.reconstruct_events()
        self.on_reorder_callback(new_events)
        self.redraw()


class MacroRecorderFrame(tk.Frame):
    """Macro Recorder UI Component"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors["bg"])

        self.recorder = MacroRecorder()
        self.player = MacroPlayer()
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

        from .theme import ModernRadioButton

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

    def on_global_press(self, key):
        if self.is_setting_trigger:
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

    def check_trigger_press(self, key_or_button):
        try:
            if not self.recorder.running:
                # 1. Check current editing macro trigger
                if key_or_button == self.trigger_key_code:
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
                    if key_or_button == trigger_code:
                        self.play_active_macro(macro_data)
                        return

        except Exception as e:
            print(f"Trigger error: {e}")

    def check_trigger_release(self, key_or_button):
        try:
            # 1. Check current macro
            if key_or_button == self.trigger_key_code:
                mode = self.playback_mode_var.get()
                if mode == "hold" and self.player.running:
                    self.after(0, self.stop_playback)

            # 2. Check active macros (for hold mode)
            for trigger_code, macro_data in self.active_macros.items():
                if key_or_button == trigger_code:
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
            maxvalue=10.0,
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

    def on_frame_configure(self, event):
        pass  # Handled by canvas

    def on_canvas_configure(self, event):
        pass  # Handled by canvas

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

        x = self.btn_menu.winfo_rootx() + self.btn_menu.winfo_width() - 200
        y = self.btn_menu.winfo_rooty() + self.btn_menu.winfo_height()

        ModernMenu(self, x, y, items)

    def show_macro_library(self):
        MacroLibraryWindow(self, self.load_macro_from_path)

    def start_set_trigger(self):
        self.is_setting_trigger = True
        self.btn_trigger.configure(text="Press Key/Btn...", kind="primary")
        self.status_var.set("Press any key or mouse button to set as Trigger...")

    def set_trigger_key(self, key_or_button):
        try:
            name = self.get_key_name(key_or_button)
            self.trigger_key_var.set(name)
            self.trigger_key_code = key_or_button

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

    def get_key_name(self, key):
        if isinstance(key, mouse.Button):
            return str(key)

        if hasattr(key, "name"):
            return key.name.upper()
        elif hasattr(key, "char"):
            return key.char.upper() if key.char else "UNKNOWN"
        return str(key)

    def parse_trigger_string(self, trigger_str):
        """Parse trigger string back to key/button object"""
        try:
            # Mouse button format: "Button.x1", "Button.left", etc.
            if trigger_str.startswith("Button."):
                button_name = trigger_str.split(".")[-1]
                return getattr(mouse.Button, button_name, mouse.Button.x1)

            # Keyboard Key format: "F9", "ENTER", etc.
            if hasattr(keyboard.Key, trigger_str.lower()):
                return getattr(keyboard.Key, trigger_str.lower())

            # Single character
            if len(trigger_str) == 1:
                return trigger_str.lower()

            # Default fallback
            return mouse.Button.x1
        except Exception as e:
            print(f"Error parsing trigger '{trigger_str}': {e}")
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
        # Remove last F9 press and release events
        filtered_events = []
        for event in self.current_macro:
            # Check if this is an F9 key event
            if event["type"] in ["key_press", "key_release"]:
                key = event["data"].get("key", "")
                # F9 can be stored as "Key.f9" or "F9" or keyboard.Key.f9
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
        # Keep UI hidden - running in background

    def play_macro(self):
        if not self.current_macro:
            messagebox.showwarning("Warning", "No macro to play!")
            return

        self.status_var.set("Playing...")
        self.btn_play.configure(text="⏹ Stop")
        # Use withdraw instead of iconify for FramelessWindow (overrideredirect)
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
            self.current_macro, self.on_play_finished, loop_count=loop_count
        )

    def on_play_finished(self):
        # Show UI again after playback finishes
        self.winfo_toplevel().deiconify()
        self.winfo_toplevel().lift()
        self.status_var.set("Playback finished")
        self.btn_play.configure(text="▶ Play (Trigger)")

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

        macros_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "macros")
        if not os.path.exists(macros_dir):
            os.makedirs(macros_dir)

        # Check limit
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

            # Update current name
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

            # Map old settings to new mode
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

        # Update name
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

        # Check if trigger already used
        if trigger_code in self.active_macros:
            if not messagebox.askyesno(
                "Confirm", f"Trigger '{trigger_name}' is already used. Overwrite?"
            ):
                return

        # Create macro data object
        macro_name = (
            self.current_macro_name
            if self.current_macro_name
            else f"Macro {len(self.active_macros) + 1}"
        )

        macro_data = {
            "name": macro_name,
            "events": list(self.current_macro),  # Copy
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
        # If called from button, find selection
        if trigger_code is None:
            pass  # UI doesn't support selection removal yet, use X button on card

    def update_active_list(self):
        # Clear container
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

        # Icon
        mode = data["settings"]["mode"]
        icon = "↻" if mode == "loop" else "✋" if mode == "hold" else "▶"
        tk.Label(
            card, text=icon, bg=colors["secondary"], fg="white", font=FONTS["h2"]
        ).pack(side="left", padx=5)

        # Info
        info_frame = tk.Frame(card, bg=colors["secondary"])
        info_frame.pack(side="left", fill="both", expand=True)

        # Name and Trigger
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

        # Remove Button
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

    def play_active_macro(self, macro_data):
        if self.player.running:
            self.player.stop()
            # Small delay to ensure stop
            self.after(100, lambda: self._start_active_playback(macro_data))
        else:
            self._start_active_playback(macro_data)

    def _start_active_playback(self, macro_data):
        events = macro_data["events"]
        settings = macro_data["settings"]
        mode = settings.get("mode", "once")

        loop_count = 1
        if mode == "loop":
            loop_count = 0  # Assume infinite for active background macros
        elif mode == "hold":
            loop_count = 0

        self.status_var.set(f"Playing active macro (Trigger: {settings['trigger']})...")
        self.player.play(events, self.on_play_finished, loop_count=loop_count)

    def cleanup(self):
        if self.key_listener:
            self.key_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.recorder.running:
            self.recorder.stop()
        if self.player.running:
            self.player.stop()


class MacroWindow:
    def __init__(self, master=None):
        if master:
            self.root = tk.Toplevel(master)
            self.is_toplevel = True
        else:
            self.root = tk.Tk()
            self.is_toplevel = False

        self.root.title("FourT Macro Recorder")
        self.root.geometry("600x700")
        self.root.configure(bg=colors["bg"])

        from .theme import apply_theme, set_window_icon

        apply_theme(self.root)
        set_window_icon(self.root)

        self.frame = MacroRecorderFrame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.frame.cleanup()
        if self.is_toplevel:
            self.root.destroy()
        else:
            self.root.quit()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MacroWindow()
    app.run()
