"""
Package Configuration - Server-side source of truth for packages and features
This module provides the full package definitions that can be fetched by clients
"""

from typing import Dict, List, Any

# All available features in the system
ALL_FEATURES = [
    {"id": "midi_playback", "name": "MIDI Playback", "description": "Phát nhạc MIDI tự động"},
    {"id": "loop_mode", "name": "Loop Mode", "description": "Lặp lại bài nhạc"},
    {"id": "script_preview", "name": "Script Preview", "description": "Xem và chỉnh sửa kịch bản"},
    {"id": "mp3_conversion", "name": "MP3 Conversion", "description": "Chuyển đổi MP3 sang MIDI"},
    {"id": "macro", "name": "Macro", "description": "Ghi và phát macro"},
    {"id": "macro_unlimited", "name": "Macro Unlimited", "description": "Macro không giới hạn"},
    {"id": "wwm_combo", "name": "WWM Combo", "description": "WWM Combo Studio"},
    {"id": "quest_video_helper", "name": "Quest Video Helper", "description": "Hỗ trợ tìm video hướng dẫn quest"},
    {"id": "ping_optimizer", "name": "Ping Optimizer", "description": "Tối ưu ping và network"},
]

# Default package definitions (can be overridden by database)
DEFAULT_PACKAGE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "trial": {
        "name": "Trial",
        "description": "Dùng thử tất cả tính năng",
        "price": 0,
        "duration_days": 0,  # Special: uses duration in minutes (30min = 0.02 days)
        "duration_minutes": 30,  # Trial duration in minutes
        "features": ["midi_playback", "loop_mode", "script_preview", "macro", "mp3_conversion", "macro_unlimited", "wwm_combo"],
        "feature_display": [
            "Dùng thử 30 phút",
            "Tất cả tính năng Premium"
        ],
        "limits": {"midi_file_limit": 999, "macro_save_limit": 999, "macro_infinite_loop": True},
        "color": "#e67e22",
        "order": -1  # Before Free
    },
    "free": {
        "name": "Free",
        "description": "Sau khi hết Trial",
        "price": 0,
        "duration_days": 0,
        "features": [],
        "feature_display": ["Không có tính năng", "Vui lòng nâng cấp"],
        "limits": {"midi_file_limit": 0},
        "color": "#95a5a6",
        "order": 0
    },
    "basic": {
        "name": "Basic",
        "description": "Gói cơ bản",
        "price": 20000,
        "duration_days": 30,
        "features": ["midi_playback", "loop_mode"],
        "feature_display": [
            "Phát nhạc MIDI tự động",
            "Chế độ lặp lại"
        ],
        "limits": {"midi_file_limit": 999},
        "color": "#3498db",
        "order": 1
    },
    "plus": {
        "name": "Plus",
        "description": "Gói nâng cao",
        "price": 35000,
        "duration_days": 30,
        "features": ["midi_playback", "loop_mode", "script_preview"],
        "feature_display": [
            "Tất cả tính năng Basic",
            "Chỉnh sửa kịch bản MIDI"
        ],
        "limits": {"midi_file_limit": 999},
        "color": "#2ecc71",
        "order": 2
    },
    "pro": {
        "name": "Pro",
        "description": "Gói chuyên nghiệp",
        "price": 55000,
        "duration_days": 30,
        "features": ["midi_playback", "loop_mode", "script_preview", "macro", "mp3_conversion"],
        "feature_display": [
            "Tất cả tính năng Plus",
            "Chuyển đổi MP3 sang MIDI",
            "Macro (5 files)"
        ],
        "limits": {"midi_file_limit": 999, "macro_save_limit": 5, "macro_infinite_loop": False},
        "color": "#f1c40f",
        "order": 3,
        "recommended": True
    },
    "premium": {
        "name": "Premium",
        "description": "Trải nghiệm đỉnh cao",
        "price": 89000,
        "duration_days": 30,
        "features": ["midi_playback", "loop_mode", "script_preview", "macro", "mp3_conversion", "macro_unlimited", "wwm_combo"],
        "feature_display": [
            "Tất cả tính năng Pro",
            "WWM Combo Studio",
            "Macro không giới hạn",
            "Infinite Loop Mode"
        ],
        "limits": {"midi_file_limit": 999, "macro_save_limit": 999, "macro_infinite_loop": True},
        "color": "#9b59b6",
        "order": 4
    }
}

def get_package_definitions() -> Dict[str, Dict[str, Any]]:
    """Get package definitions (from database or defaults)"""
    # TODO: Load from database if available
    return DEFAULT_PACKAGE_DEFINITIONS

def get_all_features() -> List[Dict[str, str]]:
    """Get all available features"""
    return ALL_FEATURES

def get_package_features(package_id: str) -> List[str]:
    """Get features for a specific package"""
    pkg = get_package_definitions().get(package_id, {})
    return pkg.get("features", [])

def get_package_limits(package_id: str) -> Dict[str, Any]:
    """Get limits for a specific package"""
    pkg = get_package_definitions().get(package_id, {})
    return pkg.get("limits", {})
