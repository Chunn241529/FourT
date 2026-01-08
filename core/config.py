"""
Configuration constants for FourT MIDI Auto-Player
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ------------------- Keyboard Configuration -------------------
# 7 phím mỗi octave (C, D, E, F, G, A, B - các nốt tự nhiên)
# Shift + phím = nốt thăng (#), Ctrl + phím = nốt giáng (♭)
LOW_KEYS = "zxcvbnm"  # 7 low keys (octave thấp)
MED_KEYS = "asdfghj"  # 7 middle keys (octave giữa)
HIGH_KEYS = "qwertyu"  # 7 high keys (octave cao)

ALL_KEYS = LOW_KEYS + MED_KEYS + HIGH_KEYS

# ------------------- Auto-Update Configuration -------------------
# ------------------- Auto-Update Configuration -------------------
# UPDATE_SERVER_URL will be defined after LICENSE_SERVER_URL
VERSION_FILE = "version.ini"

# ------------------- UI Configuration -------------------
WINDOW_WIDTH = 350
WINDOW_HEIGHT = 310
WINDOW_TITLE = ""

# colors
COLOR_BG = "#121212"
COLOR_BG_LIGHT = "#1f1f1f"
COLOR_PRIMARY = "#3498db"
COLOR_SUCCESS = "#2ecc71"
COLOR_WARNING = "#f1c40f"
COLOR_ERROR = "#e74c3c"
COLOR_TEXT = "#bdc3c7"
COLOR_TEXT_DIM = "#7f8c8d"

# ------------------- Donate Link -------------------
DONATE_URL = "https://drive.google.com/file/d/1BcrA_KVpOu0MTuL_xa1JPOj_9bDkCZmb/view?usp=drive_link"


# ------------------- Playback Configuration -------------------
DEFAULT_PLAYBACK_SPEED = 1.0
MIN_PLAYBACK_SPEED = 0.25
MAX_PLAYBACK_SPEED = 2.0
COUNTDOWN_SECONDS = 5

# ------------------- MIDI Configuration -------------------
MIDI_FOLDER = "midi_files"

# Map pitch class (0-11) to key index (0-11)
# 0=C, 1=C#, 2=D, 3=D#, 4=E, 5=F, 6=F#, 7=G, 8=G#, 9=A, 10=A#, 11=B
PITCH_MAPPING = {
    0: 0,  # C
    1: 1,  # C#
    2: 2,  # D
    3: 3,  # D#
    4: 4,  # E
    5: 5,  # F
    6: 6,  # F#
    7: 7,  # G
    8: 8,  # G#
    9: 9,  # A
    10: 10,  # A#
    11: 11,  # B
}


# ------------------- Feature Management -------------------
# Định nghĩa các tính năng thực tế
class Features:
    """Danh sách các tính năng trong ứng dụng"""

    MIDI_PLAYBACK = "midi_playback"
    SEQUENCE = "sequence"
    LOOP_MODE = "loop_mode"  # Cho phép lặp lại
    SCRIPT_PREVIEW = "script_preview"  # Xem trước kịch bản
    MP3_CONVERSION = "mp3_conversion"  # Chuyển đổi MP3 sang MIDI
    SEQUENCE_UNLIMITED = (
        "sequence_unlimited"  # Sequence không giới hạn (infinite loop, save limit)
    )
    WWM_COMBO = "wwm_combo"  # WWM Combo Studio
    QUEST_VIDEO_HELPER = "quest_video_helper"  # OCR + YouTube video helper
    PING_OPTIMIZER = "ping_optimizer"  # Tối ưu ping và network
    SCREEN_TRANSLATOR = "screen_translator"  # Screen OCR + Translation
    MIDI_SMART_BASS = "midi_smart_bass"
    MIDI_PLAYLIST_UNLIMITED = "midi_playlist_unlimited"
    MIDI_LIBRARY_SEARCH = "midi_library_search"
    INPUT_HUMANIZED_PRO = "input_humanized_pro"


# Định nghĩa các gói (packages/tiers)
class Packages:
    """Các gói/tier sử dụng"""

    FREE = "free"
    BASIC = "basic"
    PLUS = "plus"  # NEW: Gói trung gian
    PRO = "pro"
    PREMIUM = "premium"


# Map các tính năng theo từng gói
PACKAGE_FEATURES = {
    Packages.FREE: [
        # Free: No features after trial (30 mins)
    ],
    Packages.BASIC: [
        Features.MIDI_PLAYBACK,
        Features.LOOP_MODE,
        # Basic: MIDI Playback + Loop only
    ],
    Packages.PLUS: [
        Features.MIDI_PLAYBACK,
        Features.LOOP_MODE,
        Features.SCRIPT_PREVIEW,
        Features.QUEST_VIDEO_HELPER,
        Features.SCREEN_TRANSLATOR,
        # Plus: Basic + Script Preview + Quest Video Helper + Screen Translator
    ],
    Packages.PRO: [
        Features.MIDI_PLAYBACK,
        Features.LOOP_MODE,
        Features.SCRIPT_PREVIEW,
        Features.SCRIPT_PREVIEW,
        Features.SEQUENCE,
        Features.MP3_CONVERSION,
        Features.QUEST_VIDEO_HELPER,
        Features.PING_OPTIMIZER,
        Features.SCREEN_TRANSLATOR,
        # Pro: Plus + Sequence + MP3 Conversion + Ping Optimizer
    ],
    Packages.PREMIUM: [
        Features.MIDI_PLAYBACK,
        Features.LOOP_MODE,
        Features.SCRIPT_PREVIEW,
        Features.SEQUENCE,
        Features.MP3_CONVERSION,
        Features.SEQUENCE_UNLIMITED,
        Features.WWM_COMBO,
        Features.QUEST_VIDEO_HELPER,
        Features.PING_OPTIMIZER,
        Features.SCREEN_TRANSLATOR,
        # Premium: Pro + Unlimited Sequence + WWM Combo
    ],
}

# ------------------- License Server Configuration -------------------
# Server endpoints để quản lý license và features
LICENSE_DURATION_DAYS = 30  # Monthly subscription

# URL Discovery - Fetch current server URLs from npoint.io
# Supports multiple tunnel providers with priority fallback:
# 1. Cloudflare Tunnel (preferred - free, unlimited bandwidth)
# 2. ngrok (fallback - 1GB/month free)
# 3. bore.pub (fallback - free but less stable)
# npoint.io endpoint: https://www.npoint.io/docs/c6878ec0e82ad63a767f
SERVER_CONFIG_URL = "https://api.npoint.io/c6878ec0e82ad63a767f"
SERVER_URL_CACHE_FILE = os.path.join(
    os.path.expandvars("%LOCALAPPDATA%"), "FourT", "server_url_cache.json"
)


def _get_cached_server_url() -> str:
    """
    Get server URL from cache (no network call, instant).
    Used for offline-first startup.
    """
    import json

    # Method 1: Use cached URL (instant)
    try:
        if os.path.exists(SERVER_URL_CACHE_FILE):
            with open(SERVER_URL_CACHE_FILE, "r") as f:
                data = json.load(f)
                server_url = data.get("server_url")
                if server_url:
                    print(f"[Config] Using cached server URL: {server_url}")
                    return server_url
    except Exception as e:
        print(f"[Config] Could not read cached URL: {e}")

    # Method 2: Use environment variable
    env_url = os.getenv("LICENSE_SERVER_URL")
    if env_url:
        print(f"[Config] Using environment server URL: {env_url}")
        return env_url

    # Method 3: Fall back to localhost (useful for development)
    print("[Config] Using localhost fallback")
    return "http://127.0.0.1:8000"


def _test_server_url(url: str, timeout: float = 3) -> bool:
    """Test if a server URL is accessible"""
    import urllib.request

    try:
        req = urllib.request.Request(
            f"{url}/health",  # Assume server has /health endpoint
            headers={"User-Agent": "FourT-Helper/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except:
        # Try root endpoint as fallback
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "FourT-Helper/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status in [200, 307, 308]  # Allow redirects
        except:
            return False


def _fetch_and_cache_server_url() -> str:
    """
    Fetch server URLs from npoint.io and find the first working one.
    Priority: cloudflare_url > ngrok_url > bore_url > server_url (legacy)
    Only call this when online (after connection check).
    """
    import urllib.request
    import json

    # Ensure cache directory exists
    cache_dir = os.path.dirname(SERVER_URL_CACHE_FILE)
    if cache_dir and not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except:
            pass

    try:
        req = urllib.request.Request(
            SERVER_CONFIG_URL, headers={"User-Agent": "FourT-Helper/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

            # Add production domain as hardcoded candidate (highest priority)
            if "fourt_url" not in data:
                data["fourt_url"] = "https://fourt.io.vn"

            # Add npapi.io as a hardcoded candidate (fallback)
            if "npapi_url" not in data:
                data["npapi_url"] = "https://npapi.io"

            # Try URLs in priority order (fourt.io.vn first, then fallbacks)
            url_keys = [
                ("fourt_url", "FourT Production"),  # NEW: Primary domain
                ("npapi_url", "NPAPI Production"),
                ("cloudflare_url", "Cloudflare Tunnel"),
                ("ngrok_url", "ngrok"),
                ("bore_url", "bore.pub"),
                ("server_url", "legacy"),  # Backwards compatibility
            ]

            for key, name in url_keys:
                url = data.get(key)
                if url:
                    print(f"[Config] Testing {name}: {url}")
                    if _test_server_url(url):
                        print(f"[Config] ✅ Using {name}: {url}")
                        # Cache the working URL
                        try:
                            with open(SERVER_URL_CACHE_FILE, "w") as f:
                                json.dump(
                                    {
                                        "server_url": url,
                                        "source": name,
                                        "all_urls": {
                                            k: data.get(k)
                                            for k, _ in url_keys
                                            if data.get(k)
                                        },
                                    },
                                    f,
                                )
                        except:
                            pass
                        return url
                    else:
                        print(f"[Config] ❌ {name} not responding")

            # If no URL works, use the first available one (might be temporarily down)
            for key, name in url_keys:
                url = data.get(key)
                if url:
                    print(f"[Config] ⚠️ Using {name} (untested): {url}")
                    try:
                        with open(SERVER_URL_CACHE_FILE, "w") as f:
                            json.dump(
                                {"server_url": url, "source": f"{name} (untested)"}, f
                            )
                    except:
                        pass
                    return url

    except Exception as e:
        print(f"[Config] Could not fetch server URL: {e}")

    # Return current cached value
    return _get_cached_server_url()


# Get the server URL (cached after first call for performance)
_cached_license_server_url = None


def get_license_server_url() -> str:
    """Get the current license server URL (cache-first, no network on startup)"""
    global _cached_license_server_url
    if _cached_license_server_url is None:
        _cached_license_server_url = _get_cached_server_url()
    return _cached_license_server_url


def refresh_server_url() -> str:
    """Force refresh the server URL (fetch from network and update cache)"""
    global _cached_license_server_url
    _cached_license_server_url = _fetch_and_cache_server_url()
    return _cached_license_server_url


# For backwards compatibility - use cache-first (instant, no network)
LICENSE_SERVER_URL = get_license_server_url()


def get_license_endpoints() -> dict:
    """Get license endpoints using current server URL (always up-to-date)"""
    base_url = get_license_server_url()
    return {
        "verify": f"{base_url}/license/verify",
        "activate": f"{base_url}/license/activate",
        "deactivate": f"{base_url}/license/deactivate",
        "check_features": f"{base_url}/features/check",
        "sync": f"{base_url}/user/sync",
        "create_payment": f"{base_url}/payment/create",
        "check_payment": f"{base_url}/payment/status",
        "trial_check": f"{base_url}/trial/check",
        # PayPal Endpoints
        "create_paypal": f"{base_url}/paypal/create",
        "check_paypal": f"{base_url}/paypal/check",
    }


# For backwards compatibility (static snapshot at import time)
# PREFER using get_license_endpoints() for dynamic URLs
LICENSE_ENDPOINTS = get_license_endpoints()

# ------------------- Auto-Update Configuration (Dependent on LICENSE_SERVER_URL) -------------------
# Use the backend endpoint for updates
UPDATE_SERVER_URL = f"{LICENSE_SERVER_URL}/update/info"


# ------------------- Community -------------------
def get_community_url() -> str:
    """Get the MIDI Community URL based on current server"""
    return f"{get_license_server_url()}/community"


# SECURITY: Demo key is now server-side only (via environment variable)
# Client should never have access to this key
DEMO_LICENSE_KEY = os.getenv("DEMO_LICENSE_KEY", "")

# ------------------- Payment Configuration (VietQR) -------------------
BANK_INFO = {
    "BANK_ID": os.getenv("BANK_ID"),
    "ACCOUNT_NO": os.getenv("BANK_ACCOUNT"),
    "ACCOUNT_NAME": os.getenv("BANK_NAME"),
    "TEMPLATE": "compact2",
}


def get_int_env(key, default=0):
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


PACKAGE_PRICES = {
    Packages.BASIC: get_int_env("BASIC_PRICE", 20000),
    Packages.PLUS: get_int_env("PLUS_PRICE", 35000),
    Packages.PRO: get_int_env("PRO_PRICE", 55000),
    Packages.PREMIUM: get_int_env("PREMIUM_PRICE", 89000),
}

PACKAGE_DETAILS = {
    Packages.BASIC: {
        "name": "Basic",
        "price": get_int_env("BASIC_PRICE", 20000),
        "description": "Gói cơ bản (1 tháng)",
        "features": [
            "Auto Music không giới hạn",
            "Loop Mode",
        ],
        "recommended": False,
        "color": "#3498db",  # Blue
    },
    Packages.PLUS: {
        "name": "Plus",
        "price": get_int_env("PLUS_PRICE", 35000),
        "description": "Gói nâng cao (1 tháng)",
        "features": [
            "Tất cả tính năng Basic",
            "Chỉnh sửa kịch bản midi",
        ],
        "recommended": False,
        "color": "#2ecc71",  # Green
    },
    Packages.PRO: {
        "name": "Pro",
        "price": get_int_env("PRO_PRICE", 55000),
        "description": "Gói chuyên nghiệp (1 tháng)",
        "features": [
            "Tất cả tính năng Plus",
            "Tất cả tính năng Plus",
            "Sequence Recording & Playback",
            "Lưu tối đa 5 Sequence",
        ],
        "recommended": True,
        "color": "#f1c40f",  # Yellow/Gold
    },
    Packages.PREMIUM: {
        "name": "Premium",
        "price": get_int_env("PREMIUM_PRICE", 89000),
        "description": "Trải nghiệm đỉnh cao (1 tháng)",
        "features": [
            "Tất cả tính năng Pro",
            "WWM Combo Studio",
            "Sequence không giới hạn",
            "Infinite Loop Mode",
        ],
        "recommended": False,
        "color": "#9b59b6",  # Purple
    },
}

# ------------------- Sepay Configuration -------------------
# Sepay.vn - Automatic bank transaction verification (Free for individuals)
SEPAY_ACCOUNT_NUMBER = os.getenv("SEPAY_ACCOUNT_NUMBER", "")
SEPAY_API_KEY = os.getenv("SEPAY_API_KEY", "")
SEPAY_ENABLED = bool(SEPAY_ACCOUNT_NUMBER and SEPAY_API_KEY)


# ------------------- User Settings -------------------
class UserSettings:
    """Cài đặt người dùng (sẽ được lưu local và sync với server)"""

    DEFAULT_PACKAGE = Packages.FREE  # Gói mặc định khi chưa kích hoạt
    # LICENSE_FILE = "license.dat"  # DEPRECATED: No longer using local file storage
    # LICENSE_CACHE_FILE - Now in %LOCALAPPDATA%\FourT\.lic.dat (set dynamically in FeatureManager)
    USER_PREFS_FILE = "user_prefs.json"  # File lưu preferences
    CACHE_DURATION = 3600  # Thời gian cache feature check (giây)
    OFFLINE_MODE = True  # Cho phép hoạt động offline với gói đã kích hoạt (24h cache)


# ------------------- Feature Limits -------------------
# Giới hạn cho từng feature theo gói
FEATURE_LIMITS = {
    Packages.FREE: {
        "midi_file_limit": 0,
        "playlist_size": 1,
    },
    Packages.BASIC: {
        "midi_file_limit": 999,
        "playlist_size": 5,
    },
    Packages.PLUS: {
        "midi_file_limit": 999,
        "playlist_size": 10,
    },
    Packages.PRO: {
        "midi_file_limit": 999,
        "sequence_save_limit": 5,
        "sequence_infinite_loop": False,
        "playlist_size": 999,
    },
    Packages.PREMIUM: {
        "midi_file_limit": 999,
        "sequence_save_limit": 999,
        "sequence_infinite_loop": True,
        "playlist_size": 999,
    },
}
