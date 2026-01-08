"""
Local Trial Manager - Quản lý thời gian dùng thử khi offline
Sử dụng file mã hóa + Registry để chống bypass đơn giản
"""

import os
import time
import json
import winreg
from typing import Optional, Dict, Any
from datetime import datetime

from device_utils import get_device_id
from services.secure_license_cache import SecureLicenseCache


# Default trial duration: 30 minutes
DEFAULT_TRIAL_DURATION_MINUTES = 30


class LocalTrialManager:
    """
    Quản lý trial offline với:
    1. File mã hóa trong AppData (dùng SecureLicenseCache)
    2. Registry backup để chống xóa file đơn giản
    3. Check "last seen" timestamp để phát hiện chỉnh giờ lùi
    """

    REGISTRY_PATH = r"Software\FourT"
    REGISTRY_KEY = "TrialData"

    def __init__(self):
        # Setup AppData directory
        appdata_dir = os.path.join(os.getenv("LOCALAPPDATA", ""), "FourT")
        if not os.path.exists(appdata_dir):
            os.makedirs(appdata_dir, exist_ok=True)

        self.trial_cache_file = os.path.join(appdata_dir, ".trial.dat")
        self.secure_cache = SecureLicenseCache(self.trial_cache_file)
        self.device_id = get_device_id()

        # Trial duration in seconds
        self.trial_duration_seconds = DEFAULT_TRIAL_DURATION_MINUTES * 60

    def set_trial_duration(self, minutes: int) -> None:
        """Set trial duration (called from server config if available)"""
        self.trial_duration_seconds = minutes * 60

    def start_trial(self) -> bool:
        """
        Bắt đầu trial mới. Chỉ gọi khi chưa có trial nào.

        Returns:
            True nếu bắt đầu thành công
        """
        # Kiểm tra xem đã có trial chưa
        existing = self._load_trial_data()
        if existing:
            print("[LocalTrial] Trial already exists, not starting new one")
            return False

        now = time.time()
        trial_data = {
            "started_at": now,
            "expires_at": now + self.trial_duration_seconds,
            "last_seen": now,
            "device_id": self.device_id,
        }

        # Lưu vào file mã hóa
        if not self.secure_cache.save(trial_data):
            print("[LocalTrial] Failed to save trial to file")
            return False

        # Backup vào Registry
        self._save_to_registry(trial_data)

        print(f"[LocalTrial] Trial started, expires in {self.trial_duration_seconds}s")
        return True

    def check_trial(self) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái trial.

        Returns:
            {
                "active": bool,
                "remaining_seconds": int,
                "message": str
            }
        """
        trial_data = self._load_trial_data()

        if not trial_data:
            # Không có trial data -> có thể start trial mới
            return {
                "active": False,
                "remaining_seconds": 0,
                "message": "no_trial",
                "can_start": True,
            }

        now = time.time()
        expires_at = trial_data.get("expires_at", 0)
        last_seen = trial_data.get("last_seen", now)

        # Check chỉnh giờ lùi: nếu giờ hiện tại < last_seen, đáng ngờ
        if now < last_seen - 60:  # Cho phép sai lệch 1 phút
            print("[LocalTrial] Clock rollback detected!")
            # Invalidate trial
            self._remove_trial()
            return {
                "active": False,
                "remaining_seconds": 0,
                "message": "clock_tamper",
                "can_start": False,
            }

        # Update last_seen
        trial_data["last_seen"] = now
        self.secure_cache.save(trial_data)
        self._save_to_registry(trial_data)

        # Check hết hạn
        if now >= expires_at:
            print("[LocalTrial] Trial expired")
            return {
                "active": False,
                "remaining_seconds": 0,
                "message": "expired",
                "can_start": False,
            }

        remaining = int(expires_at - now)
        print(f"[LocalTrial] Trial active, {remaining}s remaining")
        return {
            "active": True,
            "remaining_seconds": remaining,
            "message": "active",
            "can_start": False,
        }

    def get_remaining_time(self) -> int:
        """Trả về số giây còn lại của trial"""
        result = self.check_trial()
        return result.get("remaining_seconds", 0)

    def is_active(self) -> bool:
        """Kiểm tra trial có đang active không"""
        result = self.check_trial()
        return result.get("active", False)

    def _load_trial_data(self) -> Optional[Dict[str, Any]]:
        """Load trial data từ file hoặc registry"""
        # Try file first
        data = self.secure_cache.load()
        if data:
            return data

        # Fallback to registry
        reg_data = self._load_from_registry()
        if reg_data:
            # Restore file from registry
            print("[LocalTrial] Restoring trial from registry")
            self.secure_cache.save(reg_data)
            return reg_data

        return None

    def _save_to_registry(self, trial_data: Dict[str, Any]) -> bool:
        """Backup trial data vào Windows Registry"""
        try:
            # Mã hóa đơn giản bằng base64 + json
            import base64

            json_str = json.dumps(trial_data)
            encoded = base64.b64encode(json_str.encode()).decode()

            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH, 0, winreg.KEY_WRITE
            )
            winreg.SetValueEx(key, self.REGISTRY_KEY, 0, winreg.REG_SZ, encoded)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[LocalTrial] Registry save error: {e}")
            return False

    def _load_from_registry(self) -> Optional[Dict[str, Any]]:
        """Load trial data từ Windows Registry"""
        try:
            import base64

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH, 0, winreg.KEY_READ
            )
            encoded, _ = winreg.QueryValueEx(key, self.REGISTRY_KEY)
            winreg.CloseKey(key)

            json_str = base64.b64decode(encoded).decode()
            data = json.loads(json_str)

            # Verify device binding
            if data.get("device_id") != self.device_id:
                print("[LocalTrial] Registry data from different device")
                return None

            return data
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"[LocalTrial] Registry load error: {e}")
            return None

    def _remove_trial(self) -> None:
        """Xóa trial data (khi phát hiện gian lận)"""
        # Remove file
        try:
            if os.path.exists(self.trial_cache_file):
                os.remove(self.trial_cache_file)
        except Exception:
            pass

        # Remove registry
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH, 0, winreg.KEY_WRITE
            )
            winreg.DeleteValue(key, self.REGISTRY_KEY)
            winreg.CloseKey(key)
        except Exception:
            pass


# Singleton
_local_trial_manager: Optional[LocalTrialManager] = None


def get_local_trial_manager() -> LocalTrialManager:
    """Get LocalTrialManager singleton"""
    global _local_trial_manager
    if _local_trial_manager is None:
        _local_trial_manager = LocalTrialManager()
    return _local_trial_manager
