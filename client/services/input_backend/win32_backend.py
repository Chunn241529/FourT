from .base import InputBackend
import ctypes
import time
from ctypes import wintypes

# Windows API Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

# DirectInput Scan Codes
DIK_ESCAPE = 0x01
DIK_1 = 0x02
DIK_2 = 0x03
DIK_3 = 0x04
DIK_4 = 0x05
DIK_5 = 0x06
DIK_6 = 0x07
DIK_7 = 0x08
DIK_8 = 0x09
DIK_9 = 0x0A
DIK_0 = 0x0B
DIK_MINUS = 0x0C
DIK_EQUALS = 0x0D
DIK_BACK = 0x0E
DIK_TAB = 0x0F
DIK_Q = 0x10
DIK_W = 0x11
DIK_E = 0x12
DIK_R = 0x13
DIK_T = 0x14
DIK_Y = 0x15
DIK_U = 0x16
DIK_I = 0x17
DIK_O = 0x18
DIK_P = 0x19
DIK_LBRACKET = 0x1A
DIK_RBRACKET = 0x1B
DIK_RETURN = 0x1C
DIK_LCONTROL = 0x1D
DIK_A = 0x1E
DIK_S = 0x1F
DIK_D = 0x20
DIK_F = 0x21
DIK_G = 0x22
DIK_H = 0x23
DIK_J = 0x24
DIK_K = 0x25
DIK_L = 0x26
DIK_SEMICOLON = 0x27
DIK_APOSTROPHE = 0x28
DIK_GRAVE = 0x29
DIK_LSHIFT = 0x2A
DIK_BACKSLASH = 0x2B
DIK_Z = 0x2C
DIK_X = 0x2D
DIK_C = 0x2E
DIK_V = 0x2F
DIK_B = 0x30
DIK_N = 0x31
DIK_M = 0x32
DIK_COMMA = 0x33
DIK_PERIOD = 0x34
DIK_SLASH = 0x35
DIK_RSHIFT = 0x36
DIK_MULTIPLY = 0x37
DIK_LALT = 0x38
DIK_SPACE = 0x39
DIK_CAPITAL = 0x3A
DIK_F1 = 0x3B
DIK_F2 = 0x3C
DIK_F3 = 0x3D
DIK_F4 = 0x3E
DIK_F5 = 0x3F
DIK_F6 = 0x40
DIK_F7 = 0x41
DIK_F8 = 0x42
DIK_F9 = 0x43
DIK_F10 = 0x44
DIK_NUMLOCK = 0x45
DIK_SCROLL = 0x46
DIK_NUMPAD7 = 0x47
DIK_NUMPAD8 = 0x48
DIK_NUMPAD9 = 0x49
DIK_SUBTRACT = 0x4A
DIK_NUMPAD4 = 0x4B
DIK_NUMPAD5 = 0x4C
DIK_NUMPAD6 = 0x4D
DIK_ADD = 0x4E
DIK_NUMPAD1 = 0x4F
DIK_NUMPAD2 = 0x50
DIK_NUMPAD3 = 0x51
DIK_NUMPAD0 = 0x52
DIK_DECIMAL = 0x53
DIK_F11 = 0x57
DIK_F12 = 0x58
DIK_UP = 0xC8
DIK_LEFT = 0xCB
DIK_RIGHT = 0xCD
DIK_DOWN = 0xD0
DIK_INSERT = 0xD2
DIK_DELETE = 0xD3

# Map generic names to DIK Scan Codes
KEY_MAPPING = {
    "esc": DIK_ESCAPE,
    "escape": DIK_ESCAPE,
    "1": DIK_1,
    "2": DIK_2,
    "3": DIK_3,
    "4": DIK_4,
    "5": DIK_5,
    "6": DIK_6,
    "7": DIK_7,
    "8": DIK_8,
    "9": DIK_9,
    "0": DIK_0,
    "-": DIK_MINUS,
    "=": DIK_EQUALS,
    "backspace": DIK_BACK,
    "tab": DIK_TAB,
    "q": DIK_Q,
    "w": DIK_W,
    "e": DIK_E,
    "r": DIK_R,
    "t": DIK_T,
    "y": DIK_Y,
    "u": DIK_U,
    "i": DIK_I,
    "o": DIK_O,
    "p": DIK_P,
    "[": DIK_LBRACKET,
    "]": DIK_RBRACKET,
    "enter": DIK_RETURN,
    "return": DIK_RETURN,
    "ctrl": DIK_LCONTROL,
    "lctrl": DIK_LCONTROL,
    "a": DIK_A,
    "s": DIK_S,
    "d": DIK_D,
    "f": DIK_F,
    "g": DIK_G,
    "h": DIK_H,
    "j": DIK_J,
    "k": DIK_K,
    "l": DIK_L,
    ";": DIK_SEMICOLON,
    "'": DIK_APOSTROPHE,
    "`": DIK_GRAVE,
    "shift": DIK_LSHIFT,
    "lshift": DIK_LSHIFT,
    "\\": DIK_BACKSLASH,
    "z": DIK_Z,
    "x": DIK_X,
    "c": DIK_C,
    "v": DIK_V,
    "b": DIK_B,
    "n": DIK_N,
    "m": DIK_M,
    ",": DIK_COMMA,
    ".": DIK_PERIOD,
    "/": DIK_SLASH,
    "rshift": DIK_RSHIFT,
    "alt": DIK_LALT,
    "lalt": DIK_LALT,
    "space": DIK_SPACE,
    "f1": DIK_F1,
    "f2": DIK_F2,
    "f3": DIK_F3,
    "f4": DIK_F4,
    "f5": DIK_F5,
    "f6": DIK_F6,
    "f7": DIK_F7,
    "f8": DIK_F8,
    "f9": DIK_F9,
    "f10": DIK_F10,
    "f11": DIK_F11,
    "f12": DIK_F12,
    "up": DIK_UP,
    "left": DIK_LEFT,
    "right": DIK_RIGHT,
    "down": DIK_DOWN,
    "insert": DIK_INSERT,
    "delete": DIK_DELETE,
}


# Structures for SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]


class Win32Backend(InputBackend):
    """
    Advanced backend utilizing Win32 SendInput.
    Sends proper hardware scancodes which are harder to detect than virtual key events.
    """

    def __init__(self):
        self.user32 = ctypes.windll.user32

    def _send_input(self, inp):
        self.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

    def _get_scancode(self, key_code: str) -> int:
        key_lower = key_code.lower()
        return KEY_MAPPING.get(key_lower, 0)

    def press_key(self, key_code: str):
        scancode = self._get_scancode(key_code)
        if scancode == 0:
            # Fallback for unknown keys: simple mapping attempt
            # (Note: robust implementation would map char to vk to scan)
            pass

        flags = KEYEVENTF_SCANCODE
        if scancode in [DIK_UP, DIK_DOWN, DIK_LEFT, DIK_RIGHT, DIK_INSERT, DIK_DELETE]:
            flags |= KEYEVENTF_EXTENDEDKEY

        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki = KEYBDINPUT(0, scancode, flags, 0, None)
        self._send_input(inp)

    def release_key(self, key_code: str):
        scancode = self._get_scancode(key_code)

        flags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
        if scancode in [DIK_UP, DIK_DOWN, DIK_LEFT, DIK_RIGHT, DIK_INSERT, DIK_DELETE]:
            flags |= KEYEVENTF_EXTENDEDKEY

        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki = KEYBDINPUT(0, scancode, flags, 0, None)
        self._send_input(inp)

    def click_mouse(self, button: str, down: bool = True, up: bool = True):
        b_lower = button.lower()
        flags_down = 0
        flags_up = 0
        data = 0

        if b_lower in ("left", "lmb", "left_click", "mouse1"):
            flags_down = MOUSEEVENTF_LEFTDOWN
            flags_up = MOUSEEVENTF_LEFTUP
        elif b_lower in ("right", "rmb", "right_click", "mouse2"):
            flags_down = MOUSEEVENTF_RIGHTDOWN
            flags_up = MOUSEEVENTF_RIGHTUP
        elif b_lower in ("middle", "mmb", "middle_click", "mouse3"):
            flags_down = MOUSEEVENTF_MIDDLEDOWN
            flags_up = MOUSEEVENTF_MIDDLEUP
        elif b_lower in ("x1", "mouse4", "back"):
            flags_down = MOUSEEVENTF_XDOWN
            flags_up = MOUSEEVENTF_XUP
            data = 1  # XBUTTON1
        elif b_lower in ("x2", "mouse5", "forward"):
            flags_down = MOUSEEVENTF_XDOWN
            flags_up = MOUSEEVENTF_XUP
            data = 2  # XBUTTON2

        if down and flags_down:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.mi = MOUSEINPUT(0, 0, data, flags_down, 0, None)
            self._send_input(inp)

        if up and flags_up:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.mi = MOUSEINPUT(0, 0, data, flags_up, 0, None)
            self._send_input(inp)

    def scroll(self, dx: int, dy: int):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        # Wheel delta: 120 per notch. input is usually -1 or 1 in our app.
        amount = dy * 120
        inp.mi = MOUSEINPUT(0, 0, amount, MOUSEEVENTF_WHEEL, 0, None)
        self._send_input(inp)

    def move_mouse(self, dx: int, dy: int):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        # Move relative
        inp.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
        self._send_input(inp)
