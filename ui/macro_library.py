"""
Macro Library Management
"""

import json
import os
from typing import List, Dict, Optional

class MacroLibrary:
    """Manage saved macros and their keybindings"""
    
    def __init__(self, macro_folder="macros"):
        self.macro_folder = macro_folder
        self.keybindings_file = os.path.join(macro_folder, "keybindings.json")
        self._ensure_folder()
        self.keybindings = self._load_keybindings()
    
    def _ensure_folder(self):
        """Create macros folder if it doesn't exist"""
        if not os.path.exists(self.macro_folder):
            os.makedirs(self.macro_folder)
    
    def _load_keybindings(self) -> Dict[str, Dict]:
        """Load keybinding mappings from file with backward compatibility"""
        if os.path.exists(self.keybindings_file):
            try:
                with open(self.keybindings_file, 'r') as f:
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
        with open(self.keybindings_file, 'w') as f:
            json.dump(self.keybindings, f, indent=2)
    
    def list_macros(self) -> List[str]:
        """List all saved macro files"""
        macros = []
        for file in os.listdir(self.macro_folder):
            if file.endswith('.json') and file != 'keybindings.json':
                macros.append(file)
        return sorted(macros)
    
    def load_macro(self, filename: str) -> Optional[Dict]:
        """Load a macro from file (returns dict with metadata and events)"""
        filepath = os.path.join(self.macro_folder, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                
                # Backward compatibility: if data is a list, convert to new format
                if isinstance(data, list):
                    return {
                        "metadata": {
                            "playback_mode": "loop",
                            "loop_count": 1,
                            "speed": 1.0
                        },
                        "events": data
                    }
                return data
        return None
    
    def save_macro(self, filename: str, events: List[Dict], metadata: Optional[Dict] = None):
        """Save a macro to file with metadata"""
        filepath = os.path.join(self.macro_folder, filename)
        
        # Default metadata if not provided
        if metadata is None:
            metadata = {
                "playback_mode": "loop",
                "loop_count": 1,
                "speed": 1.0
            }
        
        data = {
            "metadata": metadata,
            "events": events
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def delete_macro(self, filename: str):
        """Delete a macro file"""
        filepath = os.path.join(self.macro_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            # Remove keybinding if exists
            if filename in self.keybindings:
                del self.keybindings[filename]
                self._save_keybindings()
    
    def get_keybinding(self, filename: str) -> Optional[str]:
        """Get keybinding key for a macro"""
        binding = self.keybindings.get(filename)
        if binding and isinstance(binding, dict):
            return binding.get("key")
        return None
    
    def set_keybinding(self, filename: str, key: str, enabled: bool = True):
        """Set keybinding for a macro"""
        # Remove old binding for this key
        for macro, binding in list(self.keybindings.items()):
            if isinstance(binding, dict) and binding.get("key") == key:
                del self.keybindings[macro]
        
        # Set new binding
        if key:
            self.keybindings[filename] = {"key": key, "enabled": enabled}
        elif filename in self.keybindings:
            del self.keybindings[filename]
        
        self._save_keybindings()
    
    def get_macro_by_key(self, key: str) -> Optional[str]:
        """Get macro filename for a given key"""
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
