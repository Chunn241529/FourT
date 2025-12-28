"""
Story Log Window
Displays a history of translated text (dialogue history)
"""

import tkinter as tk
from tkinter import ttk
import datetime
from ..theme import colors, FONTS
from ..i18n import t


class StoryLogWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📜 Story Log")
        self.geometry("400x500")

        # Configure window style
        self.configure(bg=colors["bg"])
        self.attributes("-alpha", 0.95)
        self.attributes("-topmost", True)

        # UI Setup
        self._setup_ui()

        # Data
        self.log_entries = []

    def _setup_ui(self):
        # Header
        header = tk.Frame(self, bg=colors["bg"], padx=10, pady=5)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Story Log",
            font=("Segoe UI", 11, "bold"),
            bg=colors["bg"],
            fg=colors["fg"],
        ).pack(side="left")

        # Controls
        btn_frame = tk.Frame(header, bg=colors["bg"])
        btn_frame.pack(side="right")

        # Clear button
        clear_btn = tk.Label(
            btn_frame,
            text="🗑",
            font=("Segoe UI", 12),
            bg=colors["bg"],
            fg=colors["fg_dim"],
            cursor="hand2",
            padx=5,
        )
        clear_btn.pack(side="left")
        clear_btn.bind("<Button-1>", lambda e: self.clear_log())
        self._add_hover_effect(clear_btn)

        # Always on top toggle
        self.pinned = True
        pin_btn = tk.Label(
            btn_frame,
            text="📌",
            font=("Segoe UI", 12),
            bg=colors["bg"],
            fg=colors["accent"],
            cursor="hand2",
            padx=5,
        )
        pin_btn.pack(side="left")

        def toggle_pin(e):
            self.pinned = not self.pinned
            self.attributes("-topmost", self.pinned)
            pin_btn.configure(fg=colors["accent"] if self.pinned else colors["fg_dim"])

        pin_btn.bind("<Button-1>", toggle_pin)

        # Main content area
        self.canvas = tk.Canvas(self, bg=colors["card"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas, bg=colors["card"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw", width=380
        )  # Initial width
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Resize listener to adjust frame width
        def on_resize(event):
            self.canvas.itemconfig(
                self.canvas.find_withtag("all")[0], width=event.width
            )

        self.canvas.bind("<Configure>", on_resize)

        self.canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.scrollbar.pack(side="right", fill="y", pady=5)

        # Mousewheel scrolling
        self.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if self.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _add_hover_effect(self, widget):
        widget.bind("<Enter>", lambda e: widget.configure(fg=colors["fg"]))
        widget.bind("<Leave>", lambda e: widget.configure(fg=colors["fg_dim"]))

    def add_entry(self, original: str, translated: str):
        """Add new entry to log"""
        if not translated or not translated.strip():
            return

        # Limit entries
        if len(self.log_entries) > 100:
            # Remove oldest widget
            if self.log_entries[0]["widget"]:
                self.log_entries[0]["widget"].destroy()
            self.log_entries.pop(0)

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Entry container
        entry_frame = tk.Frame(self.scrollable_frame, bg=colors["card"], pady=5)
        entry_frame.pack(fill="x", padx=5)

        # Timestamp
        tk.Label(
            entry_frame,
            text=timestamp,
            font=("Segoe UI", 8),
            fg=colors["fg_dim"],
            bg=colors["card"],
        ).pack(anchor="w")

        # Translated Text (Main)
        trans_lbl = tk.Label(
            entry_frame,
            text=translated,
            font=("Segoe UI", 11),
            fg=colors["fg"],
            bg=colors["card"],
            wraplength=350,
            justify="left",
        )
        trans_lbl.pack(anchor="w", fill="x")

        # Original Text (Sub)
        orig_lbl = tk.Label(
            entry_frame,
            text=original,
            font=("Segoe UI", 9, "italic"),
            fg="#6e7681",
            bg=colors["card"],
            wraplength=350,
            justify="left",
        )
        orig_lbl.pack(anchor="w", fill="x")

        # Separator
        tk.Frame(entry_frame, bg="#30363d", height=1).pack(fill="x", pady=(5, 0))

        # Store
        self.log_entries.append(
            {
                "original": original,
                "translated": translated,
                "timestamp": timestamp,
                "widget": entry_frame,
            }
        )

        # Auto scroll to bottom
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def clear_log(self):
        for entry in self.log_entries:
            if entry["widget"]:
                entry["widget"].destroy()
        self.log_entries.clear()

    def show(self):
        self.deiconify()
        self.lift()

    def hide(self):
        self.withdraw()
