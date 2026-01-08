"""
Playlist Service - Logic layer for playlist management
Handles queue, playback order, shuffle, repeat, and persistence
"""

import os
import json
import random
from typing import List, Dict, Optional, Callable
from datetime import datetime


class PlaylistService:
    """Manages playlist logic - separated from UI"""

    # Repeat modes
    REPEAT_NONE = "none"
    REPEAT_ONE = "one"
    REPEAT_ALL = "all"

    def __init__(self):
        self.songs: List[Dict] = []  # [{path, name, speed}]
        self.current_index: int = -1
        self.shuffle_enabled: bool = False
        self.repeat_mode: str = self.REPEAT_NONE
        self.delay_between_songs: int = 3  # seconds

        # Shuffle tracking
        self._shuffle_order: List[int] = []
        self._shuffle_position: int = 0

        # Callbacks
        self._on_song_change: Optional[Callable] = None
        self._on_playlist_change: Optional[Callable] = None

        # Playlist storage directory
        self._playlists_dir = os.path.join(
            os.getenv("LOCALAPPDATA", ""), "FourT", "playlists"
        )
        self._ensure_playlists_dir()

    def _ensure_playlists_dir(self):
        """Create playlists directory if not exists"""
        if self._playlists_dir and not os.path.exists(self._playlists_dir):
            try:
                os.makedirs(self._playlists_dir, exist_ok=True)
            except Exception:
                pass

    # ==================== Callbacks ====================

    def set_on_song_change(self, callback: Callable):
        """Set callback when current song changes"""
        self._on_song_change = callback

    def set_on_playlist_change(self, callback: Callable):
        """Set callback when playlist is modified"""
        self._on_playlist_change = callback

    def _notify_song_change(self):
        if self._on_song_change:
            self._on_song_change(self.get_current_song())

    def _notify_playlist_change(self):
        if self._on_playlist_change:
            self._on_playlist_change()

    # ==================== Song Management ====================

    def add_song(
        self, path: str, name: Optional[str] = None, speed: float = 1.0
    ) -> int:
        """
        Add a song to the playlist

        Returns:
            Index of added song
        """
        if name is None:
            name = os.path.basename(path)

        # Check limit
        try:
            from feature_manager import get_feature_manager

            fm = get_feature_manager()
            limit = fm.get_feature_limit("playlist_size")
            if isinstance(limit, int) and len(self.songs) >= limit:
                return -1
        except Exception as e:
            print(f"Error checking limit: {e}")

        song = {"path": path, "name": name, "speed": speed}
        self.songs.append(song)

        # Update shuffle order if needed
        if self.shuffle_enabled:
            self._shuffle_order.append(len(self.songs) - 1)

        # Set current to first song if this is the first addition
        if self.current_index < 0:
            self.current_index = 0

        self._notify_playlist_change()
        return len(self.songs) - 1

    def add_songs(self, paths: List[str], speed: float = 1.0) -> int:
        """Add multiple songs at once. Returns count added."""
        for path in paths:
            self.add_song(path, speed=speed)
        return len(paths)

    def remove_song(self, index: int) -> bool:
        """Remove song at index. Returns True if successful."""
        if not 0 <= index < len(self.songs):
            return False

        self.songs.pop(index)

        # Adjust current index
        if index < self.current_index:
            self.current_index -= 1
        elif index == self.current_index:
            # Current song removed, stay at same index (now points to next)
            if self.current_index >= len(self.songs):
                self.current_index = len(self.songs) - 1

        # Rebuild shuffle order
        if self.shuffle_enabled:
            self._rebuild_shuffle_order()

        self._notify_playlist_change()
        return True

    def clear(self):
        """Clear all songs from playlist"""
        self.songs.clear()
        self.current_index = -1
        self._shuffle_order.clear()
        self._shuffle_position = 0
        self._notify_playlist_change()

    def reorder(self, from_idx: int, to_idx: int) -> bool:
        """Move song from one position to another"""
        if not 0 <= from_idx < len(self.songs):
            return False
        if not 0 <= to_idx < len(self.songs):
            return False
        if from_idx == to_idx:
            return True

        song = self.songs.pop(from_idx)
        self.songs.insert(to_idx, song)

        # Adjust current index
        if from_idx == self.current_index:
            self.current_index = to_idx
        elif from_idx < self.current_index <= to_idx:
            self.current_index -= 1
        elif to_idx <= self.current_index < from_idx:
            self.current_index += 1

        self._notify_playlist_change()
        return True

    def move_up(self, index: int) -> bool:
        """Move song up in the list"""
        return self.reorder(index, index - 1) if index > 0 else False

    def move_down(self, index: int) -> bool:
        """Move song down in the list"""
        return self.reorder(index, index + 1) if index < len(self.songs) - 1 else False

    # ==================== Playback Control ====================

    def get_current_song(self) -> Optional[Dict]:
        """Get currently selected song"""
        if not self.songs or self.current_index < 0:
            return None
        if self.current_index >= len(self.songs):
            return None
        return self.songs[self.current_index]

    def get_current_index(self) -> int:
        """Get current song index"""
        return self.current_index

    def set_current_index(self, index: int) -> bool:
        """Set current song by index"""
        if 0 <= index < len(self.songs):
            self.current_index = index
            self._notify_song_change()
            return True
        return False

    def next_song(self) -> Optional[Dict]:
        """
        Move to next song based on repeat/shuffle settings

        Returns:
            Next song dict, or None if playlist ended
        """
        if not self.songs:
            return None

        # Repeat One: stay on current
        if self.repeat_mode == self.REPEAT_ONE:
            self._notify_song_change()
            return self.get_current_song()

        # Shuffle mode
        if self.shuffle_enabled:
            return self._next_shuffle()

        # Normal sequential
        next_idx = self.current_index + 1

        if next_idx >= len(self.songs):
            if self.repeat_mode == self.REPEAT_ALL:
                next_idx = 0
            else:
                return None  # Playlist ended

        self.current_index = next_idx
        self._notify_song_change()
        return self.get_current_song()

    def prev_song(self) -> Optional[Dict]:
        """Move to previous song"""
        if not self.songs:
            return None

        if self.shuffle_enabled:
            return self._prev_shuffle()

        prev_idx = self.current_index - 1
        if prev_idx < 0:
            prev_idx = len(self.songs) - 1 if self.repeat_mode == self.REPEAT_ALL else 0

        self.current_index = prev_idx
        self._notify_song_change()
        return self.get_current_song()

    def has_next(self) -> bool:
        """Check if there's a next song available"""
        if not self.songs:
            return False
        if self.repeat_mode in [self.REPEAT_ONE, self.REPEAT_ALL]:
            return True
        return self.current_index < len(self.songs) - 1

    def has_prev(self) -> bool:
        """Check if there's a previous song"""
        if not self.songs:
            return False
        if self.repeat_mode == self.REPEAT_ALL:
            return True
        return self.current_index > 0

    # ==================== Shuffle ====================

    def set_shuffle(self, enabled: bool):
        """Enable or disable shuffle"""
        self.shuffle_enabled = enabled
        if enabled:
            self._rebuild_shuffle_order()
        self._notify_playlist_change()

    def toggle_shuffle(self) -> bool:
        """Toggle shuffle and return new state"""
        self.set_shuffle(not self.shuffle_enabled)
        return self.shuffle_enabled

    def _rebuild_shuffle_order(self):
        """Rebuild shuffle order starting from current song"""
        if not self.songs:
            self._shuffle_order = []
            self._shuffle_position = 0
            return

        # Create shuffled order, but put current song first
        indices = list(range(len(self.songs)))
        if self.current_index >= 0:
            indices.remove(self.current_index)
        random.shuffle(indices)

        if self.current_index >= 0:
            self._shuffle_order = [self.current_index] + indices
        else:
            self._shuffle_order = indices

        self._shuffle_position = 0

    def _next_shuffle(self) -> Optional[Dict]:
        """Get next song in shuffle order"""
        self._shuffle_position += 1

        if self._shuffle_position >= len(self._shuffle_order):
            if self.repeat_mode == self.REPEAT_ALL:
                self._rebuild_shuffle_order()
                self._shuffle_position = 0
            else:
                return None

        self.current_index = self._shuffle_order[self._shuffle_position]
        self._notify_song_change()
        return self.get_current_song()

    def _prev_shuffle(self) -> Optional[Dict]:
        """Get previous song in shuffle order"""
        if self._shuffle_position > 0:
            self._shuffle_position -= 1

        self.current_index = self._shuffle_order[self._shuffle_position]
        self._notify_song_change()
        return self.get_current_song()

    # ==================== Repeat ====================

    def set_repeat_mode(self, mode: str):
        """Set repeat mode: none, one, all"""
        if mode in [self.REPEAT_NONE, self.REPEAT_ONE, self.REPEAT_ALL]:
            self.repeat_mode = mode
            self._notify_playlist_change()

    def cycle_repeat_mode(self) -> str:
        """Cycle through repeat modes and return new mode"""
        modes = [self.REPEAT_NONE, self.REPEAT_ALL, self.REPEAT_ONE]
        current_idx = modes.index(self.repeat_mode)
        self.repeat_mode = modes[(current_idx + 1) % len(modes)]
        self._notify_playlist_change()
        return self.repeat_mode

    # ==================== Persistence ====================

    def save_playlist(self, name: str) -> bool:
        """Save current playlist to file"""
        if not self.songs:
            return False

        data = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "songs": self.songs,
            "settings": {
                "shuffle": self.shuffle_enabled,
                "repeat_mode": self.repeat_mode,
                "delay_between_songs": self.delay_between_songs,
            },
        }

        filepath = os.path.join(self._playlists_dir, f"{name}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[Playlist] Save error: {e}")
            return False

    def load_playlist(self, name: str) -> bool:
        """Load playlist from file"""
        filepath = os.path.join(self._playlists_dir, f"{name}.json")
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.songs = data.get("songs", [])
            self.current_index = 0 if self.songs else -1

            settings = data.get("settings", {})
            self.shuffle_enabled = settings.get("shuffle", False)
            self.repeat_mode = settings.get("repeat_mode", self.REPEAT_NONE)
            self.delay_between_songs = settings.get("delay_between_songs", 3)

            if self.shuffle_enabled:
                self._rebuild_shuffle_order()

            self._notify_playlist_change()
            return True
        except Exception as e:
            print(f"[Playlist] Load error: {e}")
            return False

    def get_saved_playlists(self) -> List[str]:
        """Get list of saved playlist names"""
        if not os.path.exists(self._playlists_dir):
            return []

        playlists = []
        for f in os.listdir(self._playlists_dir):
            if f.endswith(".json"):
                playlists.append(f[:-5])  # Remove .json extension
        return sorted(playlists)

    def delete_playlist(self, name: str) -> bool:
        """Delete a saved playlist"""
        filepath = os.path.join(self._playlists_dir, f"{name}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except Exception:
            pass
        return False

    # ==================== Utilities ====================

    def get_song_count(self) -> int:
        """Get number of songs in playlist"""
        return len(self.songs)

    def is_empty(self) -> bool:
        """Check if playlist is empty"""
        return len(self.songs) == 0

    def get_all_songs(self) -> List[Dict]:
        """Get all songs in playlist"""
        return self.songs.copy()


# Singleton instance
_playlist_service: Optional[PlaylistService] = None


def get_playlist_service() -> PlaylistService:
    """Get singleton playlist service instance"""
    global _playlist_service
    if _playlist_service is None:
        _playlist_service = PlaylistService()
    return _playlist_service
