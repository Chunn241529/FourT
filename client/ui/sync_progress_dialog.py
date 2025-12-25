"""
Sync Progress Dialog - Compact modern dialog showing sync & update progress
Combines: Connection check, License, Skills, Templates, MIDI, Version check
"""

import tkinter as tk
from tkinter import Canvas
import threading
from typing import Optional, Callable


class SyncProgressDialog(tk.Toplevel):
    """
    Compact floating dialog with progress bar for sync/update operations.
    Modern design matching UpdateCompleteDialog style.
    """
    
    # Colors matching app theme
    BG_DARK = "#1a1a2e"
    BG_CARD = "#16213e"
    ACCENT = "#667eea"
    SUCCESS = "#2ecc71"
    WARNING = "#f1c40f"
    ERROR = "#e74c3c"
    TEXT = "#ffffff"
    TEXT_DIM = "#8892b0"
    
    def __init__(self, parent, on_complete: Optional[Callable] = None, 
                 on_update_available: Optional[Callable] = None):
        """
        Initialize sync progress dialog.
        
        Args:
            parent: Parent window
            on_complete: Called when sync completes (no update)
            on_update_available: Called with update_info when update is found
        """
        super().__init__(parent)
        
        self.parent = parent
        self.on_complete = on_complete
        self.on_update_available = on_update_available
        
        self._current_percent = 0
        self._target_percent = 0
        self._status_text = "Initializing..."
        self._animation_id = None
        self._closed = False
        
        self._setup_window()
        self._create_ui()
        
    def _setup_window(self):
        """Configure window properties"""
        self.title("")
        self.overrideredirect(True)  # Borderless
        self.configure(bg=self.BG_DARK)
        self.attributes('-topmost', True)
        
        # Size and position
        width, height = 380, 140
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make draggable
        self.bind('<Button-1>', self._start_drag)
        self.bind('<B1-Motion>', self._do_drag)
        
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
        
    def _do_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")
        
    def _create_ui(self):
        """Create the dialog UI"""
        # Main container with padding
        container = tk.Frame(self, bg=self.BG_CARD, padx=20, pady=15)
        container.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Title row with icon and close button
        title_row = tk.Frame(container, bg=self.BG_CARD)
        title_row.pack(fill='x', pady=(0, 12))
        
        # Icon
        icon_label = tk.Label(
            title_row, text="🔄", font=("Segoe UI Emoji", 16),
            bg=self.BG_CARD, fg=self.ACCENT
        )
        icon_label.pack(side='left')
        
        # Title
        title_label = tk.Label(
            title_row, text="Sync & Update",
            font=("Segoe UI", 12, "bold"),
            bg=self.BG_CARD, fg=self.TEXT
        )
        title_label.pack(side='left', padx=(8, 0))
        
        # Close button
        close_btn = tk.Label(
            title_row, text="×", font=("Segoe UI", 16, "bold"),
            bg=self.BG_CARD, fg=self.TEXT_DIM, cursor="hand2"
        )
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self._close())
        close_btn.bind('<Enter>', lambda e: close_btn.configure(fg=self.ERROR))
        close_btn.bind('<Leave>', lambda e: close_btn.configure(fg=self.TEXT_DIM))
        
        # Status text
        self.status_label = tk.Label(
            container, text=self._status_text,
            font=("Segoe UI", 10),
            bg=self.BG_CARD, fg=self.TEXT_DIM,
            anchor='w'
        )
        self.status_label.pack(fill='x', pady=(0, 8))
        
        # Progress bar container
        progress_frame = tk.Frame(container, bg=self.BG_DARK, height=8)
        progress_frame.pack(fill='x', pady=(0, 8))
        progress_frame.pack_propagate(False)
        
        # Progress bar background
        self.progress_bg = tk.Frame(progress_frame, bg="#2d2d4a", height=6)
        self.progress_bg.place(relx=0, rely=0.5, relwidth=1, anchor='w')
        
        # Progress bar fill
        self.progress_fill = tk.Frame(progress_frame, bg=self.ACCENT, height=6)
        self.progress_fill.place(relx=0, rely=0.5, relwidth=0, anchor='w')
        
        # Percent label
        self.percent_label = tk.Label(
            container, text="0%",
            font=("Segoe UI", 9),
            bg=self.BG_CARD, fg=self.ACCENT
        )
        self.percent_label.pack(anchor='e')
        
    def update_progress(self, status: str, percent: int):
        """Update progress bar and status text (thread-safe)"""
        if self._closed:
            return
            
        def do_update():
            if self._closed:
                return
            try:
                self._status_text = status
                self._target_percent = min(100, max(0, percent))
                
                # Update status label
                self.status_label.configure(text=status)
                
                # Animate progress bar
                self._animate_progress()
            except tk.TclError:
                pass  # Widget destroyed
                
        self.after(0, do_update)
        
    def _animate_progress(self):
        """Smooth progress bar animation"""
        if self._closed:
            return
            
        try:
            # Ease towards target
            diff = self._target_percent - self._current_percent
            if abs(diff) < 0.5:
                self._current_percent = self._target_percent
            else:
                self._current_percent += diff * 0.2
            
            # Update UI
            progress = self._current_percent / 100
            self.progress_fill.place(relwidth=progress)
            self.percent_label.configure(text=f"{int(self._current_percent)}%")
            
            # Change color based on progress
            if self._current_percent >= 100:
                self.progress_fill.configure(bg=self.SUCCESS)
            
            # Continue animation if not at target
            if abs(self._current_percent - self._target_percent) > 0.5:
                self._animation_id = self.after(16, self._animate_progress)
                
        except tk.TclError:
            pass  # Widget destroyed
            
    def show_success(self, message: str = "Sync complete!"):
        """Show success state"""
        if self._closed:
            return
        self.update_progress(f"✅ {message}", 100)
        
    def show_error(self, message: str = "Sync failed"):
        """Show error state"""
        if self._closed:
            return
        def do_update():
            try:
                self.progress_fill.configure(bg=self.ERROR)
                self.status_label.configure(text=f"❌ {message}", fg=self.ERROR)
            except tk.TclError:
                pass
        self.after(0, do_update)
        
    def _close(self):
        """Close the dialog"""
        self._closed = True
        if self._animation_id:
            self.after_cancel(self._animation_id)
        try:
            self.destroy()
        except:
            pass
            
    def close_after(self, delay_ms: int = 1500):
        """Close dialog after delay"""
        if not self._closed:
            self.after(delay_ms, self._close)


def show_sync_progress(parent, feature_manager=None, 
                       on_complete: Optional[Callable] = None,
                       on_update_available: Optional[Callable] = None):
    """
    Show sync progress dialog and run sync.
    
    Args:
        parent: Parent window
        feature_manager: FeatureManager for license sync
        on_complete: Called when sync completes (no update)
        on_update_available: Called with (dialog, update_info) when update found
    """
    from services.sync_service import SyncService
    
    # Create dialog
    dialog = SyncProgressDialog(parent, on_complete, on_update_available)
    
    def on_progress(status: str, percent: int):
        dialog.update_progress(status, percent)
    
    def on_sync_complete(result):
        if result.get('has_update') and result.get('update_info'):
            # Update found - notify caller
            dialog.show_success("Update available!")
            if on_update_available:
                dialog.after(500, lambda: on_update_available(dialog, result['update_info']))
        elif result.get('success'):
            # Sync successful, no update
            dialog.show_success("All synced!")
            dialog.close_after(1500)
            if on_complete:
                dialog.after(1500, on_complete)
        else:
            # Sync failed
            errors = result.get('errors', ['Unknown error'])
            dialog.show_error(errors[0] if errors else "Sync failed")
            dialog.close_after(3000)
    
    # Start sync
    sync_service = SyncService(feature_manager)
    sync_service.sync_all(
        on_progress=on_progress,
        on_complete=on_sync_complete,
        threaded=True
    )
    
    return dialog
