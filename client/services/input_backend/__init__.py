from .pynput_backend import PynputBackend
from .win32_backend import Win32Backend
from typing import Literal

_current_backend = None


def get_input_backend(type: Literal["pynput", "win32"] = "win32"):
    global _current_backend
    if _current_backend:
        return _current_backend

    if type == "win32":
        try:
            _current_backend = Win32Backend()
            print("[InputBackend] Using Win32 SendInput (Scancode)")
        except Exception as e:
            print(f"[InputBackend] Win32 init failed ({e}), falling back to pynput")
            _current_backend = PynputBackend()
    else:
        _current_backend = PynputBackend()
        print("[InputBackend] Using pynput (Software)")

    return _current_backend
