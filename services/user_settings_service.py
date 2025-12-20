"""
User Settings Service for WWM Combo
Manages user keybinding preferences stored in data/wwm_user_settings.json
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


# Default keybindings matching skills.json
DEFAULT_KEYBINDINGS = {
    "skill_1": "q",
    "skill_2": "`",
    "light_attack": "lmb",
    "heavy_attack": "r",
    "charge_attack": "r",
    "deflect": "e",
    "defend": "rmb",
    "dodge": "shift",
    "jump": "space",
    "tab": "tab",
    "switch_weapon": "scroll_down",
    # Mystic skills (1-4 normal, 5-8 alt variants)
    "mystic_skill_skill_1": "1",
    "mystic_skill_skill_2": "2",
    "mystic_skill_skill_3": "3",
    "mystic_skill_skill_4": "4",
    "mystic_skill_skill_5": "alt+1",
    "mystic_skill_skill_6": "alt+2",
    "mystic_skill_skill_7": "alt+3",
    "mystic_skill_skill_8": "alt+4",
}


class UserSettingsService:
    """Service to manage user keybinding settings"""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Default to project's data directory
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data"
        else:
            data_dir = Path(data_dir)
            
        self.data_dir = data_dir
        self.settings_file = self.data_dir / "wwm_user_settings.json"
        self.settings: Dict[str, Any] = {}
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Load settings
        self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file, or create defaults if not exists"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"Error loading user settings: {e}")
                self.settings = self._get_default_settings()
        else:
            self.settings = self._get_default_settings()
            
        return self.settings
    
    def save_settings(self) -> bool:
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving user settings: {e}")
            return False
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings structure"""
        return {
            "keybindings": DEFAULT_KEYBINDINGS.copy()
        }
    
    def get_keybind(self, skill_id: str) -> str:
        """Get keybinding for a skill"""
        keybindings = self.settings.get("keybindings", {})
        return keybindings.get(skill_id, DEFAULT_KEYBINDINGS.get(skill_id, ""))
    
    def set_keybind(self, skill_id: str, key: str):
        """Set keybinding for a skill"""
        if "keybindings" not in self.settings:
            self.settings["keybindings"] = {}
        self.settings["keybindings"][skill_id] = key
    
    def get_all_keybindings(self) -> Dict[str, str]:
        """Get all keybindings (merged with defaults)"""
        # Start with defaults, then override with user settings
        result = DEFAULT_KEYBINDINGS.copy()
        result.update(self.settings.get("keybindings", {}))
        return result
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self._get_default_settings()
        self.save_settings()


# Singleton instance
_instance: Optional[UserSettingsService] = None


def get_user_settings_service() -> UserSettingsService:
    """Get singleton instance of UserSettingsService"""
    global _instance
    if _instance is None:
        _instance = UserSettingsService()
    return _instance
