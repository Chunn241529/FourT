from abc import ABC, abstractmethod
from typing import List, Union


class InputBackend(ABC):
    """Abstract base class for input simulation backends."""

    @abstractmethod
    def press_key(self, key_code: str):
        """Press a key down."""
        pass

    @abstractmethod
    def release_key(self, key_code: str):
        """Release a key."""
        pass

    @abstractmethod
    def click_mouse(self, button: str, down: bool = True, up: bool = True):
        """Click mouse button."""
        pass

    @abstractmethod
    def scroll(self, dx: int, dy: int):
        """Scroll mouse wheel."""
        pass

    @abstractmethod
    def move_mouse(self, dx: int, dy: int):
        """Move mouse relative."""
        pass
