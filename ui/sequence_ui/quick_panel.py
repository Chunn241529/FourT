import tkinter as tk
from tkinter import messagebox
import os
import glob
import json
from ..theme import colors, FONTS, ScrollableFrame


class SequenceQuickPanel(tk.Frame):
    """
    Sequence Quick List Panel - embedded in main UI
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

        self.sequences_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sequences"
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
        self.scroll_frame = ScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True)

        # Items frame is inside the scrollable frame
        self.items_frame = self.scroll_frame.inner_frame

    def refresh_list(self):
        # Clear current items
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        self.macro_files = []

        if not os.path.exists(self.sequences_dir):
            os.makedirs(self.sequences_dir)
            return

        # Load keybindings info
        keybindings = {}
        keybindings_file = os.path.join(self.sequences_dir, "keybindings.json")
        if os.path.exists(keybindings_file):
            try:
                with open(keybindings_file, "r") as f:
                    keybindings = json.load(f)
            except:
                pass

        # Get all sequence files
        macro_files = glob.glob(os.path.join(self.sequences_dir, "*.json"))
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
