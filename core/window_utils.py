"""
Window Utilities
Helper functions for window management using ctypes (Windows only).
"""

import ctypes
from typing import Optional

# Windows API Constants
SW_RESTORE = 9
SW_SHOW = 5
SW_SHOWMAXIMIZED = 3


def find_window_by_title(title_part: str) -> int:
    """Find a window handle by partial title (case-insensitive)"""
    hwnd_result = 0

    def enum_windows_proc(hwnd, lParam):
        nonlocal hwnd_result
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            if title_part.lower() in buff.value.lower():
                # Check if visible
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    hwnd_result = hwnd
                    return False  # Stop enumeration
        return True

    ENUM_WINDOWS_FUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    ctypes.windll.user32.EnumWindows(ENUM_WINDOWS_FUNC(enum_windows_proc), 0)
    return hwnd_result


def focus_window(hwnd: int) -> bool:
    """Bring a window to foreground and focus it"""
    if not hwnd:
        return False

    try:
        # Restore if minimized
        if ctypes.windll.user32.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

        # Bring to foreground
        # This is tricky on Windows 10/11 due to focus stealing prevention
        # We might need to attach thread input

        current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        target_thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)

        ctypes.windll.user32.AttachThreadInput(
            current_thread_id, target_thread_id, True
        )

        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.SetFocus(hwnd)

        ctypes.windll.user32.AttachThreadInput(
            current_thread_id, target_thread_id, False
        )
        return True
    except Exception as e:
        print(f"[WindowUtils] Error focusing window: {e}")
        return False


def focus_game_window() -> bool:
    """Attempt to focus the supported game windows"""
    # Prioritized list of window titles
    game_titles = [
        "Where Winds Meet",
        "Nghịch Thủy Hàn",
        "Justice Online",
        "wwm.exe",
        "yysl",
        "WWM",
        "GameClient",
    ]

    for title in game_titles:
        hwnd = find_window_by_title(title)
        if hwnd:
            print(f"[WindowUtils] Focusing game window: {title}")
            return focus_window(hwnd)

    print("[WindowUtils] Game window not found")
    return False
