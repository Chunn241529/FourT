"""
Macro Recorder UI (Refactored)
This file now serves as a facade for components moved to client/ui/sequence_ui/
"""

import tkinter as tk
from .theme import colors, apply_theme, set_window_icon

# Re-export components for backward compatibility
from .sequence_ui.library_window import SequenceLibraryWindow
from .sequence_ui.quick_panel import SequenceQuickPanel
from .sequence_ui.timeline_canvas import SequenceTimelineCanvas
from .sequence_ui.recorder_frame import MacroRecorderFrame


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
