import random
import string
from typing import List


class StealthManager:
    """Manages stealth features like random window titles"""

    _safe_titles = [
        "Calculator",
        "Notepad",
        "Untitled - Notepad",
        "Microsoft Edge",
        "Google Chrome",
        "File Explorer",
        "Paint",
        "Snipping Tool",
        "Photos",
        "Clock",
        "Calendar",
        "Weather",
        "Camera",
        "Voice Recorder",
        "Sticky Notes",
        "Unikey",
        "Zalo",
        "Discord",
        "Spotify",
        "VLC Media Player",
        "Telegram",
        "Steam",
        "Obsidian",
    ]

    _generated_title = None

    @classmethod
    def get_safe_window_title(cls) -> str:
        """Get a safe, consistent window title for this session"""
        if cls._generated_title:
            return cls._generated_title

        # Always use a common app name
        cls._generated_title = random.choice(cls._safe_titles)

        return cls._generated_title

    @staticmethod
    def get_random_delay(base_ms: float, jitter_percent: float = 0.15) -> float:
        """
        Get a random delay based on base_ms with some jitter
        to avoid bot-like periodic behavior
        """
        if base_ms <= 0:
            return 0

        # Calculate random multiplier between (1-jitter) and (1+jitter)
        # e.g., 0.85 to 1.15
        multiplier = 1.0 + random.uniform(-jitter_percent, jitter_percent)

        return max(0, base_ms * multiplier)


stealth_manager = StealthManager()
