from .base import InputBackend
from pynput import keyboard, mouse
import time


class PynputBackend(InputBackend):
    """Legacy backend using pynput (Software Input)."""

    def __init__(self):
        self.keyboard = keyboard.Controller()
        self.mouse = mouse.Controller()
        self.special_keys = {
            "space": keyboard.Key.space,
            "shift": keyboard.Key.shift,
            "ctrl": keyboard.Key.ctrl,
            "alt": keyboard.Key.alt,
            "tab": keyboard.Key.tab,
            "enter": keyboard.Key.enter,
            "esc": keyboard.Key.esc,
            "backspace": keyboard.Key.backspace,
            "delete": keyboard.Key.delete,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
        }

    def _parse_key(self, key_str: str):
        key_lower = key_str.lower()
        if key_lower in self.special_keys:
            return self.special_keys[key_lower]
        if len(key_str) == 1:
            return key_str.lower()
        return key_str

    def press_key(self, key_code: str):
        key = self._parse_key(key_code)
        self.keyboard.press(key)

    def release_key(self, key_code: str):
        key = self._parse_key(key_code)
        self.keyboard.release(key)

    def click_mouse(self, button: str, down: bool = True, up: bool = True):
        btn = mouse.Button.left
        b_lower = button.lower()

        if b_lower in ("right", "rmb", "right_click", "mouse2"):
            btn = mouse.Button.right
        elif b_lower in ("middle", "mmb", "middle_click", "mouse3"):
            btn = mouse.Button.middle
        elif b_lower in ("x1", "mouse4", "back"):
            btn = mouse.Button.x1
        elif b_lower in ("x2", "mouse5", "forward"):
            btn = mouse.Button.x2

        if down:
            self.mouse.press(btn)
        if up:
            self.mouse.release(btn)

    def scroll(self, dx: int, dy: int):
        self.mouse.scroll(dx, dy)

    def move_mouse(self, dx: int, dy: int):
        self.mouse.move(dx, dy)
