"""
Feature Manager - Quản lý các tính năng và gói sử dụng
Hỗ trợ kiểm tra license local và sync với server
Offline-first: Client hoạt động bình thường khi server tắt (grace period 7 ngày)
"""

import json
import os
import time
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from core.config import (
    Features,
    Packages,
    PACKAGE_FEATURES,
    FEATURE_LIMITS,
    get_license_endpoints,
    UserSettings,
)
from device_utils import get_device_id, get_public_ip
from services.secure_license_cache import SecureLicenseCache

# Grace period: Allow offline usage for 7 days after last successful verification
GRACE_PERIOD_SECONDS = 604800  # 7 days


class FeatureManager:
    """Quản lý features và license - Offline-first architecture"""

    def __init__(self, skip_network: bool = False):
        """
        Initialize Feature Manager

        Args:
            skip_network: If True, skip all server calls (use cached data only)
        """
        self.skip_network = skip_network
        self.current_package = UserSettings.DEFAULT_PACKAGE
        self.license_key: Optional[str] = None
        self.license_data: Dict[str, Any] = {}
        self.feature_cache: Dict[str, bool] = {}
        self.cache_timestamp: Optional[float] = None
        # Server-side trial tracking
        self.trial_active: bool = False
        self.trial_remaining_seconds: int = 0
        self.trial_cache_timestamp: Optional[float] = None
        # License verification cache
        self.license_cache_timestamp: Optional[float] = None
        # Server dynamic package features (from /features/config API)
        self.server_package_features: Dict[str, List[str]] = {}

        # Setup AppData directory for user data
        appdata_dir = os.path.join(os.getenv("LOCALAPPDATA"), "FourT")
        if not os.path.exists(appdata_dir):
            os.makedirs(appdata_dir)

        # Use secure encrypted cache
        self.license_cache_file = os.path.join(appdata_dir, ".lic.dat")
        self.secure_cache = SecureLicenseCache(self.license_cache_file)

        # Load cached license (verify with server only if skip_network=False)
        self._load_and_verify_license_cache()

        # Check trial only if online
        if not skip_network:
            self._check_trial_status()

    def _load_and_verify_license_cache(self) -> None:
        """Load encrypted license cache. Verify with server only if skip_network=False."""
        # Load from secure encrypted cache
        cache_data = self.secure_cache.load()

        if not cache_data:
            return

        cached_key = cache_data.get("license_key")
        if not cached_key:
            return

        self.license_key = cached_key

        # If skip_network, just restore from cache (no server call)
        if self.skip_network:
            if self._is_within_grace_period(cache_data):
                self._restore_from_cache(cache_data)
                print(
                    f"[FeatureManager] Offline: using cached license ({self.current_package})"
                )
            else:
                print(f"[FeatureManager] Offline: grace period expired")
                self.license_key = None
                self.secure_cache._remove_cache()
            return

        # Online: verify with server
        print(f"[FeatureManager] Found cached license, verifying...")
        if self.verify_license():
            print(f"[FeatureManager] License verified: {self.current_package}")
        else:
            if not self._is_within_grace_period(cache_data):
                print(f"[FeatureManager] License invalid, grace period expired")
                self.license_key = None
                self.current_package = UserSettings.DEFAULT_PACKAGE
                self.secure_cache._remove_cache()
            else:
                self._restore_from_cache(cache_data)
                print(f"[FeatureManager] Grace period active: {self.current_package}")

    def _is_within_grace_period(self, cache_data: Dict) -> bool:
        """Check if we're within the grace period for offline usage"""
        last_verified = cache_data.get("last_verified_at")
        if not last_verified:
            return False

        try:
            elapsed = time.time() - last_verified
            within_grace = elapsed < GRACE_PERIOD_SECONDS
            if within_grace:
                days_remaining = (GRACE_PERIOD_SECONDS - elapsed) / 86400
                print(
                    f"[FeatureManager] Grace period: {days_remaining:.1f} days remaining"
                )
            return within_grace
        except:
            return False

    def _restore_from_cache(self, cache_data: Dict) -> None:
        """Restore license state from cache data"""
        self.current_package = cache_data.get("package", Packages.FREE)
        self.license_data = {
            "license_key": cache_data.get("license_key"),
            "package": self.current_package,
            "expires_at": cache_data.get("expires_at"),
        }
        self.license_cache_timestamp = cache_data.get("last_verified_at")

    def _safe_remove_cache_file(self) -> None:
        """Safely remove the cache file"""
        self.secure_cache._remove_cache()

    def _save_license_cache(self) -> None:
        """Save encrypted license cache with grace period data"""
        cache_data = {
            "license_key": self.license_key,
            "package": self.current_package,
            "expires_at": self.license_data.get("expires_at"),
            "last_verified_at": time.time(),
        }

        if self.secure_cache.save(cache_data):
            print(f"[FeatureManager] ✅ Secure license cache saved")
        else:
            print(f"[FeatureManager] ❌ Failed to save license cache")

    def activate_license(self, license_key: str) -> bool:
        """
        Kích hoạt license key

        Args:
            license_key: License key để kích hoạt

        Returns:
            True nếu kích hoạt thành công
        """
        # Check if this is a self-contained key (can activate offline)
        from services.license_key_utils import decode_license_key, get_expiry_from_key

        # Try online activation first
        try:
            from services.connection_manager import is_server_offline

            if not is_server_offline():
                import requests

                device_id = get_device_id()
                ipv4 = get_public_ip()

                print(f"[Client] Activating online: {license_key[:10]}...")

                response = requests.post(
                    get_license_endpoints()["activate"],
                    json={
                        "license_key": license_key,
                        "device_id": device_id,
                        "ipv4": ipv4,
                    },
                    timeout=5,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self.license_key = license_key
                        self.current_package = data.get("package", Packages.FREE)
                        self.license_data = data.get("license_data", {})
                        if not self.license_data:
                            self.license_data = {
                                "license_key": license_key,
                                "package": self.current_package,
                                "expires_at": data.get("expires_at"),
                            }
                        else:
                            if "package" not in self.license_data:
                                self.license_data["package"] = self.current_package
                            if "license_key" not in self.license_data:
                                self.license_data["license_key"] = license_key

                        self.license_cache_timestamp = time.time()
                        self._save_license_cache()
                        self._clear_cache()
                        print(
                            f"[FeatureManager] ✅ License activated (online): {self.current_package}"
                        )
                        return True

                print(f"[FeatureManager] Online activation failed: {response.text}")
        except Exception as e:
            print(f"[FeatureManager] Online activation error: {e}")

        # Offline activation: Try to decode self-contained key (4T- format)
        decoded = decode_license_key(license_key)
        if decoded:
            package, duration_days = decoded
            expires_at = get_expiry_from_key(license_key)

            self.license_key = license_key
            self.current_package = package
            self.license_data = {
                "license_key": license_key,
                "package": package,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "activated_offline": True,
            }
            self.license_cache_timestamp = time.time()
            self._save_license_cache()
            self._clear_cache()
            print(f"[FeatureManager] ✅ License activated (offline): {package}")
            return True

        print("[FeatureManager] ❌ Activation failed - invalid key or no connection")
        return False

    def deactivate_license(self) -> bool:
        """
        Hủy kích hoạt license

        Returns:
            True nếu hủy thành công
        """
        try:
            if self.license_key:
                import requests

                requests.post(
                    get_license_endpoints()["deactivate"],
                    json={"license_key": self.license_key},
                )
        except Exception as e:
            print(f"Lỗi khi deactivate trên server: {e}")

        self.license_key = None
        self.current_package = UserSettings.DEFAULT_PACKAGE
        self.license_data = {}
        self.license_cache_timestamp = None
        # Remove license cache file safely
        self._safe_remove_cache_file()
        self._clear_cache()
        return True

    def verify_license(self) -> bool:
        """
        Verify license với server

        Returns:
            True nếu license còn hợp lệ
        """
        if not self.license_key:
            return False

        try:
            import requests

            # Get device ID for verification
            device_id = get_device_id()

            print(
                f"[Client] Sending POST request to: {get_license_endpoints()['verify']}"
            )
            response = requests.post(
                get_license_endpoints()["verify"],
                json={"license_key": self.license_key, "device_id": device_id},
                timeout=5,  # Short timeout for verification
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Update local data if changed
                    if data.get("package") != self.current_package:
                        self.current_package = data.get("package")
                        self.license_data["package"] = self.current_package
                        self._clear_cache()

                    # Update license_data with latest info from server
                    if "expires_at" in data:
                        self.license_data["expires_at"] = data["expires_at"]

                    # Cache the successful verification
                    self.license_cache_timestamp = time.time()
                    return True
                else:
                    # License invalid on server
                    return False

        except Exception as e:
            print(f"Lỗi kết nối khi verify: {e}")
            # Fallback to offline check with cached data
            pass

        # Offline mode: check cached license data
        if UserSettings.OFFLINE_MODE and self.license_cache_timestamp:
            # Allow offline use if we have a recent successful verification (within 24 hours)
            cache_age = time.time() - self.license_cache_timestamp
            if cache_age < 86400:  # 24 hours
                if "expires_at" in self.license_data:
                    try:
                        expires_at = datetime.fromisoformat(
                            self.license_data["expires_at"]
                        )
                        if datetime.now() < expires_at:
                            print(
                                f"[FeatureManager] Using cached license (offline mode), expires: {expires_at}"
                            )
                            return True
                    except Exception:
                        pass

        return False  # No valid license

    def _check_trial_status(self) -> None:
        """Check trial status from server and cache the result"""
        # Skip if offline
        from services.connection_manager import is_server_offline

        if is_server_offline() or self.skip_network:
            return  # Use cached/default value

        # Check cache first (refresh every 5 minutes)
        if (
            self.trial_cache_timestamp
            and (time.time() - self.trial_cache_timestamp) < 300
        ):
            return  # Use cached value

        try:
            import requests

            device_id = get_device_id()
            ipv4 = get_public_ip()

            response = requests.post(
                get_license_endpoints()["trial_check"],
                json={"device_id": device_id, "ipv4": ipv4},
                timeout=3,  # Shorter timeout since we know server is online
            )

            if response.status_code == 200:
                data = response.json()
                self.trial_active = data.get("trial_active", False)
                self.trial_remaining_seconds = data.get("trial_remaining_seconds", 0)
                self.trial_cache_timestamp = time.time()
                print(
                    f"[FeatureManager] Trial: active={self.trial_active}, remaining={self.trial_remaining_seconds}s"
                )
            else:
                print(f"[FeatureManager] Trial check failed: {response.status_code}")
        except Exception as e:
            print(f"[FeatureManager] Trial check error: {e}")
            # On error, don't change current trial state

    def is_trial_active(self) -> bool:
        """Kiểm tra xem có đang trong thời gian dùng thử không (server-side)"""
        self._check_trial_status()  # Refresh if needed
        return self.trial_active

    def get_trial_remaining_time(self) -> int:
        """Lấy thời gian dùng thử còn lại (giây) từ server"""
        self._check_trial_status()  # Refresh if needed
        return self.trial_remaining_seconds

    def has_feature(self, feature: str) -> bool:
        """
        Kiểm tra xem có quyền sử dụng feature không

        Args:
            feature: Tên feature (từ Features class)

        Returns:
            True nếu có quyền sử dụng
        """
        # Check cache
        if self._is_cache_valid() and feature in self.feature_cache:
            return self.feature_cache[feature]

        # Check trial mode (Full access)
        if self.current_package == Packages.FREE and self.is_trial_active():
            # Update cache
            self.feature_cache[feature] = True
            self.cache_timestamp = time.time()
            return True

        # Priority: Use server dynamic features if available
        if (
            self.server_package_features
            and self.current_package in self.server_package_features
        ):
            package_features = self.server_package_features[self.current_package]
        else:
            # Fallback to static config
            package_features = PACKAGE_FEATURES.get(self.current_package, [])

        has_access = feature in package_features

        # Update cache
        self.feature_cache[feature] = has_access
        self.cache_timestamp = time.time()

        return has_access

    def set_server_package_features(
        self, features_by_package: Dict[str, List[str]]
    ) -> None:
        """Set server dynamic package features (from /features/config API)"""
        self.server_package_features = features_by_package
        self._clear_cache()  # Clear cache to apply new features

    def get_feature_limit(self, limit_key: str) -> Any:
        """
        Lấy giới hạn của một feature

        Args:
            limit_key: Key của limit (vd: "max_midi_files")

        Returns:
            Giá trị limit hoặc None nếu không có
        """
        package_limits = FEATURE_LIMITS.get(self.current_package, {})
        return package_limits.get(limit_key)

    def get_current_package(self) -> str:
        """Lấy gói hiện tại"""
        return self.current_package

    def get_enabled_features(self) -> List[str]:
        """Lấy danh sách các feature được bật"""
        return PACKAGE_FEATURES.get(self.current_package, [])

    def upgrade_to_package(self, package: str) -> bool:
        """
        Nâng cấp lên gói khác

        Args:
            package: Gói muốn nâng cấp (từ Packages class)

        Returns:
            True nếu nâng cấp thành công
        """
        # TODO: Gọi API server để xử lý thanh toán/nâng cấp
        # Hiện tại chưa implement endpoint này trên server
        print("Tính năng nâng cấp chưa được implement trên server")
        return False

    def sync_with_server(self) -> bool:
        """
        Sync trạng thái với server

        Returns:
            True nếu sync thành công
        """
        return self.verify_license()

    def _is_cache_valid(self) -> bool:
        """Kiểm tra cache còn hợp lệ không"""
        if self.cache_timestamp is None:
            return False
        return (time.time() - self.cache_timestamp) < UserSettings.CACHE_DURATION

    def _clear_cache(self) -> None:
        """Xóa cache"""
        self.feature_cache = {}
        self.cache_timestamp = None

    def get_package_info(self, package: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy thông tin về một gói

        Args:
            package: Tên gói (mặc định là gói hiện tại)

        Returns:
            Dictionary chứa thông tin gói
        """
        pkg = package or self.current_package
        return {
            "package": pkg,
            "features": PACKAGE_FEATURES.get(pkg, []),
            "limits": FEATURE_LIMITS.get(pkg, {}),
        }

    def create_payment_order(self, package: str, amount: int = 0) -> Dict[str, Any]:
        """
        Tạo đơn hàng thanh toán

        Args:
            package: Gói muốn mua
            amount: Số tiền (từ server config) - nếu 0 sẽ dùng giá mặc định

        Returns:
            Dict chứa thông tin thanh toán (qr_url, amount, content, order_id)
            Có thêm 'created_offline' = True nếu tạo offline
        """
        from services.connection_manager import is_server_offline

        # Try online first
        if not is_server_offline():
            try:
                import requests

                print(f"[Client] Creating payment order online for {package}")
                payload = {"package": package}
                if amount > 0:
                    payload["amount"] = amount  # Send amount from client config

                response = requests.post(
                    get_license_endpoints()["create_payment"], json=payload, timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    data["created_offline"] = False
                    return data
                else:
                    print(f"[Payment] Online creation failed: {response.text}")

            except Exception as e:
                print(f"[Payment] Online creation error: {e}")

        # Fallback to offline payment
        print(f"[Payment] Using offline mode for {package}")
        from services.offline_payment_service import get_offline_payment_service

        offline_service = get_offline_payment_service()
        order = offline_service.create_offline_order(package, amount=amount)

        if order:
            return order

        return {}

    def check_payment_status(self, order_id: str) -> Dict[str, Any]:
        """Check status đơn hàng"""
        try:
            import requests

            response = requests.get(
                f"{get_license_endpoints()['check_payment']}/{order_id}"
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {"status": "unknown"}

    def mock_payment_success(self, order_id: str) -> Dict[str, Any]:
        """Giả lập thanh toán thành công (cho testing)"""
        try:
            import requests

            # URL này phải hardcode tạm vì chưa có trong config LICENSE_ENDPOINTS
            # Nhưng tốt nhất là thêm vào config.
            # Fallback: construct url manually
            base_url = get_license_endpoints()["create_payment"].replace(
                "/payment/create", ""
            )
            url = f"{base_url}/payment/mock-success/{order_id}"

            response = requests.post(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Mock payment error: {e}")
        return {}


# Singleton instance
_feature_manager: Optional[FeatureManager] = None


def get_feature_manager(skip_network: bool = False) -> FeatureManager:
    """
    Get feature manager instance (singleton)

    Args:
        skip_network: If True and creating new instance, skip all server calls
    """
    global _feature_manager
    if _feature_manager is None:
        _feature_manager = FeatureManager(skip_network=skip_network)
    return _feature_manager
