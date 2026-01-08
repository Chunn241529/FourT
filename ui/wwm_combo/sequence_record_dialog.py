"""
Macro Record Dialog - Record keyboard/mouse actions and add to combo timeline
Styled to match WWM Combo but using standard Toplevel for compatibility
"""

import tkinter as tk
from tkinter import messagebox
from pynput import keyboard, mouse
import time
import threading

try:
    from ..theme import colors, FONTS, ModernButton
except ImportError:
    from ui.theme import colors, FONTS, ModernButton

from core.sequence_recorder import SequenceRecorder
from utils.stealth_utils import stealth_manager


class SequenceRecordDialog(tk.Toplevel):
    """Dialog for recording sequence actions with custom titlebar"""

    def __init__(self, parent, on_add_callback=None):
        super().__init__(parent)

        # Frameless window - hide initially to prevent flicker
        self.withdraw()
        self.overrideredirect(True)
        self.configure(bg=colors["bg"])

        # Window size
        self._width = 650
        self._height = 550

        # Position centered on screen BEFORE showing
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self._width) // 2
        y = (screen_height - self._height) // 2
        self.geometry(f"{self._width}x{self._height}+{x}+{y}")

        # For dragging
        self._drag_data = {"x": 0, "y": 0}

        self.on_add_callback = on_add_callback
        self.recorder = SequenceRecorder()
        self.recorded_events = []
        self.is_recording = False

        self._setup_ui()
        self._start_recording()

        # Now show the window
        self.deiconify()

        # Force focus and always on top
        self.attributes("-topmost", True)
        self.focus_force()
        self.lift()

    def _setup_ui(self):
        """Setup dialog UI matching WWM Combo style"""
        # Custom titlebar
        titlebar = tk.Frame(self, bg=colors["header"], height=40)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)

        # Bind drag events
        titlebar.bind("<Button-1>", self._start_drag)
        titlebar.bind("<B1-Motion>", self._do_drag)

        # Title
        title_label = tk.Label(
            titlebar,
            text=f"🔴 {stealth_manager.get_safe_window_title()}",
            font=FONTS["h2"],
            bg=colors["header"],
            fg=colors["fg"],
        )
        title_label.pack(side="left", padx=15, pady=8)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        # Close button
        close_btn = tk.Label(
            titlebar,
            text="✕",
            font=("Segoe UI", 14, "bold"),
            bg=colors["header"],
            fg=colors["fg_dim"],
            cursor="hand2",
            padx=15,
        )
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Button-1>", lambda e: self._on_close())
        close_btn.bind(
            "<Enter>", lambda e: close_btn.configure(fg="#ff4444", bg=colors["danger"])
        )
        close_btn.bind(
            "<Leave>",
            lambda e: close_btn.configure(fg=colors["fg_dim"], bg=colors["header"]),
        )

        # Border frame for content
        border_frame = tk.Frame(self, bg=colors["border"])
        border_frame.pack(fill="both", expand=True, padx=2, pady=(0, 2))

        content_frame = tk.Frame(border_frame, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Main container - now inside content_frame
        main_container = tk.Frame(content_frame, bg=colors["bg"])
        main_container.pack(fill="both", expand=True, padx=15, pady=15)

        # Event count label
        self.event_count_label = tk.Label(
            titlebar,
            text="0 events",
            font=FONTS["small"],
            bg=colors["header"],
            fg=colors["fg_dim"],
        )
        self.event_count_label.pack(side="right", padx=(0, 10), pady=8)

        # Status indicator
        status_frame = tk.Frame(main_container, bg=colors["sidebar"], height=45)
        status_frame.pack(fill="x", pady=(0, 10))
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame,
            text="🔴 Recording... Press keys or click mouse",
            font=FONTS["bold"],
            bg=colors["sidebar"],
            fg="#ff4444",
        )
        self.status_label.pack(side="left", padx=15, pady=10)

        # Timeline container
        timeline_frame = tk.Frame(main_container, bg=colors["sidebar"])
        timeline_frame.pack(fill="both", expand=True, pady=(0, 15))

        # Timeline header
        timeline_header = tk.Frame(timeline_frame, bg=colors["header"])
        timeline_header.pack(fill="x")
        tk.Label(
            timeline_header,
            text="📋 Recorded Events Timeline",
            font=FONTS["bold"],
            bg=colors["header"],
            fg=colors["fg"],
        ).pack(side="left", padx=10, pady=8)

        # Timeline canvas with scrollbar
        canvas_container = tk.Frame(timeline_frame, bg=colors["input_bg"])
        canvas_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(
            canvas_container,
            bg=colors["input_bg"],
            highlightthickness=0,
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar_y = tk.Scrollbar(
            canvas_container, orient="vertical", command=self.canvas.yview
        )
        scrollbar_y.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar_y.set)

        # Buttons frame
        btn_frame = tk.Frame(main_container, bg=colors["bg"], height=60)
        btn_frame.pack(fill="x")
        btn_frame.pack_propagate(False)

        # Left side - Stop button
        self.btn_stop = ModernButton(
            btn_frame,
            text="⏹ Stop Recording",
            command=self._stop_recording,
            kind="danger",
            width=18,
        )
        self.btn_stop.pack(side="left", padx=5, pady=10)

        # Right side - Cancel and Add buttons
        ModernButton(
            btn_frame,
            text="✕ Cancel",
            command=self._on_close,
            kind="secondary",
            width=12,
        ).pack(side="right", padx=5, pady=10)

        self.btn_add = ModernButton(
            btn_frame,
            text="✓ Add to Combo",
            command=self._add_to_combo,
            kind="primary",
            width=16,
        )
        self.btn_add.pack(side="right", padx=5, pady=10)
        self.btn_add.configure(state="disabled")

    def _start_recording(self):
        """Start recording keyboard/mouse events"""
        self.is_recording = True
        self.recorded_events = []

        # Override recorder callbacks to update UI
        original_add_event = self.recorder.add_event

        def custom_add_event(event_type, data):
            original_add_event(event_type, data)
            # Update UI in main thread
            self.after(0, self._update_timeline)

        self.recorder.add_event = custom_add_event
        self.recorder.start()

    def _stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        self.recorder.stop()
        self.recorded_events = self.recorder.events.copy()

        self.status_label.configure(
            text="⏹ Recording Stopped - Review and add to combo", fg=colors["fg"]
        )
        self.btn_stop.configure(state="disabled")
        self.btn_add.configure(state="normal")

        self._update_timeline()

    def _update_timeline(self):
        """Update the timeline canvas with recorded events - horizontal layout"""
        self.canvas.delete("all")

        events = self.recorder.events if self.is_recording else self.recorded_events
        self.event_count_label.configure(text=f"{len(events)} events")

        if not events:
            self.canvas.create_text(
                320,
                100,
                text="⏳ Waiting for input...\n\nPress keys or click mouse to record actions",
                font=FONTS["body"],
                fill=colors["fg_dim"],
                justify="center",
            )
            return

        # Horizontal timeline like WWM Combo
        x, y, h = 15, 15, 50
        canvas_width = max(600, self.canvas.winfo_width())
        row_spacing = 20

        for i, event in enumerate(events):
            event_text = self._format_event(event)
            delay = event.get("delay", 0)

            # Determine item width and color
            w = max(70, len(event_text) * 8 + 25)

            if event["type"] in ("key_press", "key_release"):
                color = "#3498db"  # Blue for keyboard
            elif event["type"] in ("mouse_click", "mouse_scroll"):
                color = "#e74c3c"  # Red for mouse
            else:
                color = colors["accent"]

            # Wrap to next row if needed
            if x + w > canvas_width - 20:
                x = 15
                y += h + row_spacing

            # Draw event box with rounded look
            self.canvas.create_rectangle(
                x,
                y,
                x + w,
                y + h,
                fill=color,
                outline="white",
                width=2,
            )

            # Event text
            self.canvas.create_text(
                x + w / 2,
                y + h / 2,
                text=event_text,
                font=FONTS["small"],
                fill="white",
            )

            # Delay indicator if significant
            if delay > 0.05:
                delay_text = f"+{delay:.2f}s"
                self.canvas.create_text(
                    x + w / 2,
                    y + h + 10,
                    text=delay_text,
                    font=("Segoe UI", 8),
                    fill=colors["fg_dim"],
                )

            x += w + 10

        # Update scroll region
        total_height = y + h + 40
        self.canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

    def _format_event(self, event):
        """Format event for display"""
        data = event["data"]
        event_type = event["type"]

        if event_type == "mouse_click":
            action = "↓" if data["action"] == "pressed" else "↑"
            btn = str(data["button"]).split(".")[-1]
            return f"🖱 {btn} {action}"
        elif event_type == "mouse_scroll":
            dy = data.get("dy", 0)
            return f"🖱 Scroll {'↑' if dy > 0 else '↓'}"
        elif event_type == "key_press":
            key = str(data["key"]).replace("Key.", "")
            return f"⌨ {key} ↓"
        elif event_type == "key_release":
            key = str(data["key"]).replace("Key.", "")
            return f"⌨ {key} ↑"
        return str(event_type)

    def _add_to_combo(self):
        """Add recorded events to combo"""
        if not self.recorded_events:
            messagebox.showwarning("Empty", "No events recorded!", parent=self)
            return

        if self.on_add_callback:
            self.on_add_callback(self.recorded_events)

        self.destroy()

    def _start_drag(self, event):
        """Start window drag"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        """Handle window drag"""
        x = self.winfo_x() + (event.x - self._drag_data["x"])
        y = self.winfo_y() + (event.y - self._drag_data["y"])
        self.geometry(f"+{x}+{y}")

    def _on_close(self):
        """Handle close"""
        if self.is_recording:
            self.recorder.stop()
        self.destroy()
