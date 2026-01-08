import tkinter as tk
from tkinter import simpledialog
from ..theme import colors, FONTS


class SequenceTimelineCanvas(tk.Canvas):
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

        # Handle trailing delay (delay at end of macro, before loop)
        if pending_delay > 0:
            # Add a special "delay_only" event that player will just sleep on
            new_events.append(
                {"type": "delay_only", "delay": pending_delay, "data": {}}
            )

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
