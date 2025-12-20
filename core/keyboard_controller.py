"""
Keyboard controller for sending key presses
"""

from pynput.keyboard import Controller, Key


class KeyboardController:
    """Handles real keyboard input simulation"""

    def __init__(self):
        self.controller = Controller()

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
                if modifier == 'shift':
                    self.controller.press(Key.shift)
                elif modifier == 'ctrl':
                    self.controller.press(Key.ctrl)
            
            # Press/release main key
            if pressed:
                self.controller.press(key_char)
            else:
                self.controller.release(key_char)
                
            # Release modifier if it was pressed
            if modifier and pressed:
                if modifier == 'shift':
                    self.controller.release(Key.shift)
                elif modifier == 'ctrl':
                    self.controller.release(Key.ctrl)
                    
        except Exception as e:
            print(f"Error pressing key {key_char} with modifier {modifier}: {e}")

