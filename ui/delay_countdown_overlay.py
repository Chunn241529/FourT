"""
Delay Countdown Overlay - Floating countdown timer for macro delays
Shows a small overlay on the right-center of screen with countdown.
"""

import tkinter as tk
from typing import Optional
import threading


class DelayCountdownOverlay:
    """Singleton overlay showing delay countdown during macro playback"""

    _instance: Optional["DelayCountdownOverlay"] = None
    _hidden_root: Optional[tk.Tk] = None

    def __init__(self):
        self.window: Optional[tk.Toplevel] = None
        self.timer_label: Optional[tk.Label] = None
        self.remaining = 0.0
        self._tick_id = None
        self._closed = True

    @classmethod
    def _get_root(cls):
        """Get or create hidden root window for overlay"""
        if cls._hidden_root is None:
            try:
                cls._hidden_root = tk.Tk()
                cls._hidden_root.withdraw()  # Hide the root
                cls._hidden_root.attributes("-alpha", 0)  # Fully transparent
            except:
                return None
        return cls._hidden_root

    @classmethod
    def get_instance(cls) -> "DelayCountdownOverlay":
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def show_countdown(self, delay_seconds: float):
        """Show countdown overlay for the given delay"""
        if delay_seconds < 1:  # Don't show for very short delays
            return

        print(f"[DelayCountdownOverlay] Showing countdown for {delay_seconds}s")

        def _create():
            try:
                root = self._get_root()
                if root is None:
                    print("[DelayCountdownOverlay] No root available")
                    return
                self._create_window(root)
                self.remaining = delay_seconds
                self._update_display()
                self._tick()
            except Exception as e:
                print(f"[DelayCountdownOverlay] Error: {e}")

        if threading.current_thread() is threading.main_thread():
            _create()
        else:
            try:
                root = self._get_root()
                if root:
                    root.after(0, _create)
            except Exception as e:
                print(f"[DelayCountdownOverlay] Threading error: {e}")

    def _create_window(self, root):
        """Create or reset the overlay window"""
        if self.window is not None:
            try:
                self.window.destroy()
            except:
                pass

        self._closed = False
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.9)
        self.window.configure(bg="#1a1a2e")

        # Container with border
        frame = tk.Frame(
            self.window,
            bg="#1a1a2e",
            padx=10,
            pady=8,
            highlightbackground="#00ff88",
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True)

        # Title
        title = tk.Label(
            frame, text="⏳ Delay", font=("Segoe UI", 10), fg="#888888", bg="#1a1a2e"
        )
        title.pack()

        # Timer
        self.timer_label = tk.Label(
            frame,
            text="0:00",
            font=("Segoe UI", 24, "bold"),
            fg="#00ff88",
            bg="#1a1a2e",
        )
        self.timer_label.pack()

        # Position: right-center of screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = screen_width - 150
        y = (screen_height - 80) // 2
        self.window.geometry(f"130x80+{x}+{y}")

    def _format_time(self, seconds: float) -> str:
        """Format seconds as M:SS or S.s"""
        if seconds >= 60:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}:{secs:02d}"
        elif seconds >= 10:
            return f"{int(seconds)}s"
        else:
            return f"{seconds:.1f}s"

    def _update_display(self):
        """Update the timer display"""
        if self.timer_label and not self._closed:
            self.timer_label.config(text=self._format_time(self.remaining))

            # Color based on time remaining
            if self.remaining <= 3:
                self.timer_label.config(fg="#ff4444")
            elif self.remaining <= 10:
                self.timer_label.config(fg="#ffaa00")
            else:
                self.timer_label.config(fg="#00ff88")

    def _tick(self):
        """Countdown tick every 100ms"""
        if self._closed:
            return

        self.remaining -= 0.1

        if self.remaining <= 0:
            self.close()
        else:
            self._update_display()
            if self.window:
                self._tick_id = self.window.after(100, self._tick)

    def close(self):
        """Close the overlay"""
        if self._closed:
            return
        self._closed = True

        if self._tick_id:
            try:
                self.window.after_cancel(self._tick_id)
            except:
                pass
            self._tick_id = None

        if self.window:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None


# Convenience function
def show_delay_countdown(root: tk.Tk, delay_seconds: float):
    """Show delay countdown overlay"""
    overlay = DelayCountdownOverlay.get_instance()
    if overlay:
        overlay.show_countdown(delay_seconds)


def hide_delay_countdown():
    """Hide delay countdown overlay"""
    if DelayCountdownOverlay._instance:
        DelayCountdownOverlay._instance.close()
