import tkinter as tk
from tkinter import ttk
import os
import glob
from ..theme import colors, FONTS, ModernButton, apply_theme, set_window_icon
from utils.stealth_utils import stealth_manager


class SequenceLibraryWindow(tk.Toplevel):
    """Sequence Library List UI"""

    def __init__(self, parent, on_select_callback):
        super().__init__(parent)
        self.on_select_callback = on_select_callback

        self.title(stealth_manager.get_safe_window_title())
        self.geometry("400x500")
        self.configure(bg=colors["bg"])

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
            text=stealth_manager.get_safe_window_title(),
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
        # Find all JSON files in sequences directory
        sequences_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sequences"
        )
        # Note: adjust path because we are now in client/ui/sequence_ui/ (3 levels deep) vs client/ui/ (2 levels)
        # client/ui/sequence_window_old.py -> dirname(dirname(__file__)) -> client/
        # client/ui/sequence_ui/library_window.py -> dirname(dirname(dirname(__file__))) -> client/

        if not os.path.exists(sequences_dir):
            os.makedirs(sequences_dir)

        macro_files = glob.glob(os.path.join(sequences_dir, "*.json"))

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
        sequences_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sequences"
        )
        filepath = os.path.join(sequences_dir, filename)

        self.on_select_callback(filepath)
        self.destroy()
