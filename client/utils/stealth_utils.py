import random
import string
from typing import List


class StealthManager:
    """Manages stealth features like random window titles"""

    _safe_titles = [
        "Calculator",
        "Notepad",
        "Task Manager",
        "System Settings",
        "Windows Update",
        "Microsoft Edge",
        "Command Prompt",
        "File Explorer",
        "Services",
        "Registry Editor",
        "Paint",
        "Snipping Tool",
        "Windows Security",
        "Photos",
        "Clock",
        "Calendar",
        "Weather",
        "Camera",
        "Voice Recorder",
        "Sticky Notes",
    ]

    _generated_title = None

    @classmethod
    def get_safe_window_title(cls) -> str:
        """Get a safe, consistent window title for this session"""
        if cls._generated_title:
            return cls._generated_title

        # 30% chance of using a completely random string
        # 70% chance of using a fake common app name
        if random.random() < 0.3:
            cls._generated_title = cls._generate_random_string()
        else:
            cls._generated_title = random.choice(cls._safe_titles)

        return cls._generated_title

    @staticmethod
    def _generate_random_string(length: int = 12) -> str:
        """Generate a random alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))


stealth_manager = StealthManager()
