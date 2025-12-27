"""
Base Tab class for Admin UI tabs
"""

import tkinter as tk
from tkinter import ttk, messagebox


class BaseTab:
    """Base class for Admin UI tabs"""

    def __init__(self, parent_frame: tk.Frame, admin_window):
        """
        Initialize the tab

        Args:
            parent_frame: The tkinter Frame that contains this tab
            admin_window: Reference to the main AdminWindow instance
        """
        self.parent = parent_frame
        self.admin = admin_window

        # Shortcuts to commonly used attributes
        self.root = admin_window.root
        self.backend_dir = admin_window.backend_dir
        self.client_dir = admin_window.client_dir
        self.data_dir = admin_window.data_dir

        # Import theme here to avoid circular imports
        from ui.theme import COLORS, FONTS, ModernButton

        self.COLORS = COLORS
        self.FONTS = FONTS
        self.ModernButton = ModernButton

        # Setup the tab
        self.setup()

    def setup(self):
        """
        Setup the tab UI. Override in subclasses.
        """
        raise NotImplementedError("Subclasses must implement setup()")
