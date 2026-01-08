"""
Macro Library Management
"""

import json
import os
from typing import List, Dict, Optional


class SequenceLibrary:
    """Manage saved sequences and their keybindings"""

    def __init__(self, sequence_folder="sequences"):
        # Migration: macros -> sequences
        if os.path.exists("macros") and not os.path.exists("sequences"):
            try:
                os.rename("macros", "sequences")
            except Exception as e:
                print(f"Migration error: {e}")

        self.sequence_folder = sequence_folder
        self.keybindings_file = os.path.join(sequence_folder, "keybindings.json")
        self._ensure_folder()
        self.keybindings = self._load_keybindings()

    def _ensure_folder(self):
        """Create sequences folder if it doesn't exist"""
        if not os.path.exists(self.sequence_folder):
            os.makedirs(self.sequence_folder)

    def _load_keybindings(self) -> Dict[str, Dict]:
        """Load keybinding mappings from file with backward compatibility"""
        if os.path.exists(self.keybindings_file):
            try:
                with open(self.keybindings_file, "r") as f:
                    data = json.load(f)
                    # Migrate old format to new format
                    migrated = {}
                    needs_save = False
                    for filename, binding in data.items():
                        if isinstance(binding, str):
                            # Old format: {"macro.json": "f1"}
                            migrated[filename] = {"key": binding, "enabled": True}
                            needs_save = True
                        elif isinstance(binding, dict):
                            # New format: {"macro.json": {"key": "f1", "enabled": true}}
                            migrated[filename] = binding
                        else:
                            # Invalid format, skip
                            continue

                    # Save migrated data if needed
                    if needs_save:
                        self.keybindings = migrated
                        self._save_keybindings()

                    return migrated
            except:
                return {}
        return {}

    def _save_keybindings(self):
        """Save keybinding mappings to file"""
        with open(self.keybindings_file, "w") as f:
            json.dump(self.keybindings, f, indent=2)

    def list_sequences(self) -> List[str]:
        """List all saved sequence files"""
        sequences = []
        for file in os.listdir(self.sequence_folder):
            if file.endswith(".json") and file != "keybindings.json":
                sequences.append(file)
        return sorted(sequences)

    def load_sequence(self, filename: str) -> Optional[Dict]:
        """Load a sequence from file (returns dict with metadata and events)"""
        filepath = os.path.join(self.sequence_folder, filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)

                # Backward compatibility: if data is a list, convert to new format
                if isinstance(data, list):
                    return {
                        "metadata": {
                            "playback_mode": "loop",
                            "loop_count": 1,
                            "speed": 1.0,
                        },
                        "events": data,
                    }
                return data
        return None

    def save_sequence(
        self, filename: str, events: List[Dict], metadata: Optional[Dict] = None
    ):
        """Save a sequence to file with metadata"""
        filepath = os.path.join(self.sequence_folder, filename)

        # Default metadata if not provided
        if metadata is None:
            metadata = {"playback_mode": "loop", "loop_count": 1, "speed": 1.0}

        data = {"metadata": metadata, "events": events}

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def delete_sequence(self, filename: str):
        """Delete a sequence file"""
        filepath = os.path.join(self.sequence_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            # Remove keybinding if exists
            if filename in self.keybindings:
                del self.keybindings[filename]
                self._save_keybindings()

    def get_keybinding(self, filename: str) -> Optional[str]:
        """Get keybinding key for a sequence"""
        binding = self.keybindings.get(filename)
        if binding and isinstance(binding, dict):
            return binding.get("key")
        return None

    def set_keybinding(self, filename: str, key: str, enabled: bool = True):
        """Set keybinding for a sequence"""
        # Remove old binding for this key
        for sequence, binding in list(self.keybindings.items()):
            if isinstance(binding, dict) and binding.get("key") == key:
                del self.keybindings[sequence]

        # Set new binding
        if key:
            self.keybindings[filename] = {"key": key, "enabled": enabled}
        elif filename in self.keybindings:
            del self.keybindings[filename]

        self._save_keybindings()

    def get_sequence_by_key(self, key: str) -> Optional[str]:
        """Get sequence filename for a given key"""
        for filename, binding in self.keybindings.items():
            if isinstance(binding, dict) and binding.get("key") == key:
                return filename
        return None

    def is_keybinding_enabled(self, filename: str) -> bool:
        """Check if a keybinding is enabled"""
        binding = self.keybindings.get(filename)
        if binding and isinstance(binding, dict):
            return binding.get("enabled", True)
        return False

    def set_keybinding_enabled(self, filename: str, enabled: bool):
        """Set whether a keybinding is enabled"""
        if filename in self.keybindings:
            binding = self.keybindings[filename]
            if isinstance(binding, dict):
                binding["enabled"] = enabled
                self._save_keybindings()
