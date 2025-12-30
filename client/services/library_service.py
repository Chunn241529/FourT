"""
Local MIDI library service - Offline-first
MIDI files are bundled with the application, no need for server download
"""

import os
import glob

from core.config import MIDI_FOLDER
from utils import get_app_directory


class LibraryService:
    """Manages local MIDI library (offline-first)"""

    def __init__(self):
        self.midi_folder = os.path.join(get_app_directory(), MIDI_FOLDER)
        self._ensure_midi_folder()

    def _ensure_midi_folder(self):
        """Create MIDI folder if it doesn't exist"""
        if not os.path.exists(self.midi_folder):
            os.makedirs(self.midi_folder)

    def get_local_midi_files(self):
        """
        Get list of available MIDI files from local folder

        Returns:
            list: Sorted list of MIDI filenames
        """
        print(f"[Library] Scanning for MIDI files in: {self.midi_folder}")
        midi_files = glob.glob(os.path.join(self.midi_folder, "*.mid")) + glob.glob(
            os.path.join(self.midi_folder, "*.midi")
        )
        found = sorted([os.path.basename(f) for f in midi_files])
        print(f"[Library] Found {len(found)} files: {found}")
        return found

    def get_midi_path(self, filename):
        """
        Get full path to a MIDI file

        Args:
            filename: Name of MIDI file

        Returns:
            str: Full path to MIDI file
        """
        return os.path.join(self.midi_folder, filename)

    def file_exists(self, filename):
        """
        Check if MIDI file exists locally

        Args:
            filename: Name of MIDI file

        Returns:
            bool: True if file exists
        """
        return os.path.exists(self.get_midi_path(filename))

    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitize filename for safe filesystem use

        Args:
            filename: Original filename

        Returns:
            str: Sanitized filename
        """
        # Add .mid extension if not present
        if not filename.lower().endswith(".mid") and not filename.lower().endswith(
            ".midi"
        ):
            filename += ".mid"

        # Remove invalid characters
        filename = "".join(
            [c for c in filename if c.isalpha() or c.isdigit() or c in " .-_()"]
        )
        return filename.strip()
