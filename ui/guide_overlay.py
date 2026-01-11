"""
Guide Mode Overlay - Falling Notes Visualization
Guitar Hero-style overlay for MIDI piano practice
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Tuple, Dict
import threading
import time

from core.config import LOW_KEYS, MED_KEYS, HIGH_KEYS


class GuideOverlay:
    """
    Transparent overlay showing falling notes synchronized with MIDI playback.
    Notes fall from top to bottom, hitting a "strike line" when they should be pressed.
    """

    _instance: Optional["GuideOverlay"] = None

    # Colors
    COLORS = {
        "bg": "#0a0a14",
        "bg_transparent": "#000001",  # Near-black for transparency key
        "melody": "#4da6ff",  # Blue for right hand
        "bass": "#4dff88",  # Green for left hand
        "sharp": "#ffd700",  # Gold for sharp notes
        "flat": "#ff6b6b",  # Red for flat notes
        "strike_line": "#ffffff",
        "key_normal": "#2a2a3a",
        "key_highlight": "#5a5a7a",
        "text": "#ffffff",
        "text_dim": "#888888",
    }

    # Layout constants
    KEY_WIDTH = 45
    KEY_HEIGHT = 50
    KEY_GAP = 2
    STRIKE_LINE_Y = 0.85  # 85% from top
    NOTE_WIDTH = 40
    LOOK_AHEAD_SECONDS = 3.0  # How far ahead to show notes

    # Keyboard layout (matches config.py)
    KEYBOARD_ROWS = [
        ("HIGH", HIGH_KEYS, "C5-B5"),  # qwertyu
        ("MED", MED_KEYS, "C4-B4"),  # asdfghj
        ("LOW", LOW_KEYS, "C3-B3"),  # zxcvbnm
    ]

    def __init__(self):
        self.window: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.is_active = False
        self.is_playing = False

        # Playback sync
        self.notes: List[Dict] = []  # Preprocessed notes for visualization
        self.current_time = 0.0
        self.start_time = 0.0
        self.speed = 1.0

        # Animation
        self._animation_id = None
        self._last_frame_time = 0

        # Key positions cache
        self._key_positions: Dict[str, Tuple[int, int]] = {}

    @classmethod
    def get_instance(cls) -> "GuideOverlay":
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def show(self, notes: List[Dict] = None):
        """Show the overlay window"""
        if notes:
            self.notes = notes

        if self.window is not None:
            try:
                self.window.deiconify()
                self.window.lift()
                self.is_active = True
                return
            except:
                pass

        self._create_window()
        self.is_active = True

    def hide(self):
        """Hide the overlay window"""
        self.is_active = False
        self.stop_playback()

        if self.window:
            try:
                self.window.withdraw()
            except:
                pass

    def close(self):
        """Close and destroy the overlay"""
        self.is_active = False
        self.stop_playback()

        if self.window:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None
            self.canvas = None

    def _create_window(self):
        """Create the overlay window"""
        self.window = tk.Toplevel()
        self.window.title("🎹 Guide Mode")
        self.window.attributes("-topmost", True)
        self.window.configure(bg=self.COLORS["bg"])

        # Window size and position
        width = 800
        height = 500
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        # Make it semi-transparent (Windows)
        try:
            self.window.attributes("-alpha", 0.95)
        except:
            pass

        # Title bar with controls
        self._create_header()

        # Main canvas for notes
        self.canvas = tk.Canvas(
            self.window,
            bg=self.COLORS["bg"],
            highlightthickness=0,
            width=width,
            height=height - 40,  # Minus header
        )
        self.canvas.pack(fill="both", expand=True)

        # Calculate key positions
        self._calculate_key_positions()

        # Draw initial state
        self._draw_static_elements()

        # Close handler
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

    def _create_header(self):
        """Create header with title and controls"""
        header = tk.Frame(self.window, bg=self.COLORS["bg"], height=40)
        header.pack(fill="x", padx=10, pady=5)
        header.pack_propagate(False)

        # Title
        tk.Label(
            header,
            text="🎹 Guide Mode",
            font=("Segoe UI", 14, "bold"),
            fg=self.COLORS["text"],
            bg=self.COLORS["bg"],
        ).pack(side="left")

        # Speed control
        speed_frame = tk.Frame(header, bg=self.COLORS["bg"])
        speed_frame.pack(side="left", padx=20)

        tk.Label(
            speed_frame,
            text="Preview:",
            font=("Segoe UI", 10),
            fg=self.COLORS["text_dim"],
            bg=self.COLORS["bg"],
        ).pack(side="left")

        self.speed_var = tk.StringVar(value="3s")
        speed_combo = ttk.Combobox(
            speed_frame,
            textvariable=self.speed_var,
            values=["2s", "3s", "4s", "5s"],
            width=5,
            state="readonly",
        )
        speed_combo.pack(side="left", padx=5)
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)

        # Close button
        close_btn = tk.Button(
            header,
            text="✕",
            font=("Segoe UI", 12),
            fg=self.COLORS["text"],
            bg=self.COLORS["bg"],
            activebackground="#ff4444",
            activeforeground="white",
            bd=0,
            padx=10,
            cursor="hand2",
            command=self.hide,
        )
        close_btn.pack(side="right")

    def _on_speed_change(self, event=None):
        """Handle preview speed change"""
        value = self.speed_var.get()
        self.LOOK_AHEAD_SECONDS = float(value.replace("s", ""))

    def _calculate_key_positions(self):
        """Calculate x,y positions for each key"""
        if not self.canvas:
            return

        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()

        # Calculate keyboard width
        keys_per_row = 7
        keyboard_width = keys_per_row * (self.KEY_WIDTH + self.KEY_GAP)
        start_x = (canvas_width - keyboard_width) // 2

        # Strike line Y position
        strike_y = int(canvas_height * self.STRIKE_LINE_Y)

        # Position each row
        for row_idx, (row_name, keys, _) in enumerate(self.KEYBOARD_ROWS):
            row_y = strike_y + row_idx * (self.KEY_HEIGHT + self.KEY_GAP)

            for key_idx, key_char in enumerate(keys):
                key_x = start_x + key_idx * (self.KEY_WIDTH + self.KEY_GAP)
                self._key_positions[key_char.lower()] = (key_x, row_y)

    def _draw_static_elements(self):
        """Draw keyboard and strike line"""
        if not self.canvas:
            return

        self.canvas.delete("static")

        canvas_width = self.canvas.winfo_reqwidth()
        canvas_height = self.canvas.winfo_reqheight()
        strike_y = int(canvas_height * self.STRIKE_LINE_Y)

        # Strike line
        self.canvas.create_line(
            0,
            strike_y,
            canvas_width,
            strike_y,
            fill=self.COLORS["strike_line"],
            width=2,
            dash=(10, 5),
            tags="static",
        )

        # Strike line label
        self.canvas.create_text(
            10,
            strike_y - 10,
            text="▶ HIT",
            font=("Segoe UI", 10, "bold"),
            fill=self.COLORS["text_dim"],
            anchor="w",
            tags="static",
        )

        # Draw keyboard
        for row_name, keys, octave_label in self.KEYBOARD_ROWS:
            for key_idx, key_char in enumerate(keys):
                pos = self._key_positions.get(key_char.lower())
                if pos:
                    x, y = pos
                    # Key background
                    self.canvas.create_rectangle(
                        x,
                        y,
                        x + self.KEY_WIDTH,
                        y + self.KEY_HEIGHT,
                        fill=self.COLORS["key_normal"],
                        outline=self.COLORS["key_highlight"],
                        tags=("static", f"key_{key_char.lower()}"),
                    )
                    # Key label
                    self.canvas.create_text(
                        x + self.KEY_WIDTH // 2,
                        y + self.KEY_HEIGHT // 2,
                        text=key_char.upper(),
                        font=("Segoe UI", 12, "bold"),
                        fill=self.COLORS["text"],
                        tags="static",
                    )

            # Row label
            first_pos = self._key_positions.get(keys[0].lower())
            if first_pos:
                self.canvas.create_text(
                    first_pos[0] - 40,
                    first_pos[1] + self.KEY_HEIGHT // 2,
                    text=octave_label,
                    font=("Segoe UI", 9),
                    fill=self.COLORS["text_dim"],
                    anchor="e",
                    tags="static",
                )

    def set_notes(self, notes: List[Dict]):
        """
        Set the notes to display.
        Each note should have: key, modifier, start_time, end_time, hand (0=left, 1=right)
        """
        self.notes = notes
        print(f"[GuideOverlay] Loaded {len(notes)} notes")

    def start_playback(self, start_offset: float = 0.0):
        """Start the falling notes animation"""
        self.is_playing = True
        self.current_time = start_offset
        self.start_time = time.time() - start_offset
        self._last_frame_time = time.time()

        self._animate()

    def stop_playback(self):
        """Stop the animation"""
        self.is_playing = False

        if self._animation_id:
            try:
                self.window.after_cancel(self._animation_id)
            except:
                pass
            self._animation_id = None

    def sync_time(self, current_time: float):
        """Sync with external playback time"""
        self.current_time = current_time

    def _animate(self):
        """Animation loop - draw falling notes"""
        if not self.is_playing or not self.canvas or not self.is_active:
            return

        now = time.time()
        dt = now - self._last_frame_time
        self._last_frame_time = now

        # Update current time based on playback speed
        self.current_time += dt * self.speed

        # Clear previous notes
        self.canvas.delete("note")

        # Get canvas dimensions
        canvas_height = self.canvas.winfo_reqheight()
        strike_y = int(canvas_height * self.STRIKE_LINE_Y)

        # Draw visible notes
        for note in self.notes:
            note_start = note.get("start_time", 0)
            note_end = note.get("end_time", note_start + 0.1)
            key_char = note.get("key", "").lower()
            modifier = note.get("modifier")
            hand = note.get("hand", 1)  # 1 = right (melody), 0 = left (bass)

            # Check if note is visible (within look-ahead window)
            time_to_hit = note_start - self.current_time

            if time_to_hit < -0.5:  # Already passed
                continue
            if time_to_hit > self.LOOK_AHEAD_SECONDS:  # Too far ahead
                continue

            # Calculate Y position (falls from top to strike line)
            progress = 1 - (time_to_hit / self.LOOK_AHEAD_SECONDS)
            note_y = progress * strike_y

            # Note duration visualized as height
            duration = note_end - note_start
            note_height = max(10, int(duration * 50))

            # Get X position from key
            pos = self._key_positions.get(key_char)
            if not pos:
                continue
            note_x = pos[0] + (self.KEY_WIDTH - self.NOTE_WIDTH) // 2

            # Choose color based on hand and modifier
            if modifier == "shift":
                color = self.COLORS["sharp"]
            elif modifier == "ctrl":
                color = self.COLORS["flat"]
            elif hand == 0:
                color = self.COLORS["bass"]
            else:
                color = self.COLORS["melody"]

            # Draw note
            self.canvas.create_rectangle(
                note_x,
                note_y - note_height,
                note_x + self.NOTE_WIDTH,
                note_y,
                fill=color,
                outline="white",
                width=1,
                tags="note",
            )

            # Add modifier indicator
            if modifier:
                mod_text = "#" if modifier == "shift" else "♭"
                self.canvas.create_text(
                    note_x + self.NOTE_WIDTH // 2,
                    note_y - note_height // 2,
                    text=mod_text,
                    font=("Segoe UI", 10, "bold"),
                    fill="white",
                    tags="note",
                )

        # Schedule next frame (~60 FPS)
        self._animation_id = self.window.after(16, self._animate)


# Convenience functions
def show_guide_overlay(notes: List[Dict] = None):
    """Show the guide overlay"""
    overlay = GuideOverlay.get_instance()
    overlay.show(notes)
    return overlay


def hide_guide_overlay():
    """Hide the guide overlay"""
    if GuideOverlay._instance:
        GuideOverlay._instance.hide()


def close_guide_overlay():
    """Close the guide overlay completely"""
    if GuideOverlay._instance:
        GuideOverlay._instance.close()
        GuideOverlay._instance = None
