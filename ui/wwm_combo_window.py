"""
WWM Combo Window - Backward Compatibility Module

This module re-exports WWMComboWindow from the new modular package
for backward compatibility with existing imports.

Original location: ui/wwm_combo_window.py
New location: ui/wwm_combo/main_window.py
"""

# Re-export from new package location
from .wwm_combo import WWMComboWindow, RichTooltip, SettingsDialog

__all__ = ['WWMComboWindow', 'RichTooltip', 'SettingsDialog']


# Standalone runner (for direct execution)
if __name__ == "__main__":
    import tkinter as tk
    
    root = tk.Tk()
    root.withdraw()
    
    app = WWMComboWindow(root)
    app.protocol("WM_DELETE_WINDOW", lambda: (app.on_close(), root.quit()))
    
    root.mainloop()
