"""
Keyboard controller for sending key presses using Advanced Input Backend
"""

import threading
from services.input_backend import get_input_backend


class KeyboardController:
    """Handles real keyboard input simulation using Win32 API"""

    def __init__(self):
        # Use Win32 backend by default for better anti-cheat safety
        self.backend = get_input_backend("win32")
        self._lock = threading.RLock()

    def press_key(self, key_char, pressed=True, modifier=None):
        """
        Press or release a key on the keyboard with optional modifier

        Args:
            key_char: Character to press
            pressed: True to press, False to release
            modifier: 'shift' for sharp, 'ctrl' for flat, None for natural
        """
        try:
            with self._lock:
                if pressed:
                    # ON PRESS: Modifier → Key → Release Modifier immediately
                    # This simulates a quick tap like a real player would do
                    if modifier:
                        self.backend.press_key(modifier)

                    # Press main key
                    self.backend.press_key(key_char)

                    # Release modifier immediately after key press
                    # This prevents modifier getting "stuck" when multiple notes use it
                    if modifier:
                        self.backend.release_key(modifier)
                else:
                    # ON RELEASE: Just release the main key
                    # Modifier was already released during press
                    self.backend.release_key(key_char)

        except Exception as e:
            print(f"Error pressing key {key_char} with modifier {modifier}: {e}")
