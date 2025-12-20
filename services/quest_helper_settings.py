"""
Quest Video Helper Settings Service
Manages configuration for the Quest Video Helper feature
"""

import json
import os
from typing import Any, Dict

class QuestHelperSettings:
    """Manage Quest Video Helper settings"""
    
    CONFIG_FILE = "data/quest_helper_config.json"
    
    DEFAULTS = {
        "hotkey": "ctrl+shift+q",
        "search_prefix": "Where Winds Meet",
        "search_suffix": "guide",
        "language": "en",  # Search language: en, vi
        "video_width": 480,
        "video_height": 360,
        "auto_play": True,
        "ocr_engine": "windows",  # windows or tesseract
    }
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._load()
    
    def _get_config_path(self) -> str:
        """Get absolute path to config file"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, self.CONFIG_FILE)
    
    def _load(self) -> None:
        """Load settings from file"""
        config_path = self._get_config_path()
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[QuestHelperSettings] Error loading config: {e}")
                self._config = {}
        else:
            self._config = {}
        
        # Fill in any missing defaults
        for key, value in self.DEFAULTS.items():
            if key not in self._config:
                self._config[key] = value
    
    def save(self) -> bool:
        """Save settings to file"""
        config_path = self._get_config_path()
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[QuestHelperSettings] Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self._config.get(key, default if default is not None else self.DEFAULTS.get(key))
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._config.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults"""
        self._config = self.DEFAULTS.copy()
        self.save()
    
    def get_search_query(self, quest_name: str) -> str:
        """Build search query from quest name"""
        prefix = self.get("search_prefix", "")
        suffix = self.get("search_suffix", "")
        
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(quest_name)
        if suffix:
            parts.append(suffix)
        
        return " ".join(parts)
