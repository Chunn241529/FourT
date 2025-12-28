"""UI module"""

from .macro_window_old import MacroWindow
from .menu_launcher import MenuLauncher
from .upgrade_window import UpgradeWindow
from .splash_screen import SplashScreen
from .i18n import t, get_language, set_language, get_available_languages

__all__ = [
    "MacroWindow",
    "MenuLauncher",
    "UpgradeWindow",
    "SplashScreen",
    "t",
    "get_language",
    "set_language",
    "get_available_languages",
]
