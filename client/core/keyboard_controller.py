"""
Keyboard controller for sending key presses using Advanced Input Backend
"""

from services.input_backend import get_input_backend


class KeyboardController:
    """Handles real keyboard input simulation using Win32 API"""

    def __init__(self):
        # Use Win32 backend by default for better anti-cheat safety
        self.backend = get_input_backend("win32")

    def press_key(self, key_char, pressed=True, modifier=None):
        """
        Press or release a key on the keyboard with optional modifier

        Args:
            key_char: Character to press
            pressed: True to press, False to release
            modifier: 'shift' for sharp, 'ctrl' for flat, None for natural
        """
        try:
            # Press modifier if needed
            if modifier and pressed:
                # Map simple modifier strings to backend expected keys if needed
                # Win32Backend handles "shift", "ctrl" directly
                self.backend.press_key(modifier)

            # Press/release main key
            if pressed:
                self.backend.press_key(key_char)
            else:
                self.backend.release_key(key_char)

            # Release modifier if it was pressed
            if modifier and pressed:
                self.backend.release_key(modifier)

        except Exception as e:
            print(f"Error pressing key {key_char} with modifier {modifier}: {e}")
