"""
Pre-paid License Key System - Self-contained keys for offline activation

Key Format: 4T-{PACKAGE}-{RANDOM}-{CHECKSUM}
Example: 4T-PRO-A1B2C3D4-XY

The key contains encoded package information that can be decoded offline.
When online, the key is verified with the server for full validation.
"""

import hmac
import hashlib
import secrets
import base64
from typing import Optional, Tuple
from datetime import datetime, timedelta

from core.config import Packages, LICENSE_DURATION_DAYS


# Secret key for HMAC (should match backend)
LICENSE_SECRET = "FourT_License_Secret_2024"

# Package codes (short codes for keys)
PACKAGE_CODES = {
    "B": Packages.BASIC,
    "P": Packages.PRO,
    "M": Packages.PREMIUM,  # M for Maximum/Premium
}

# Reverse mapping
CODE_TO_PACKAGE = {v: k for k, v in PACKAGE_CODES.items()}


def generate_license_key(package: str, duration_days: int = LICENSE_DURATION_DAYS) -> str:
    """
    Generate a self-contained license key.
    
    Key format: 4T-{CODE}{DAYS}-{RANDOM8}-{CHECK2}
    Example: 4T-P30-A1B2C3D4-XY
    
    Args:
        package: Package type (basic, pro, premium)
        duration_days: License duration in days
        
    Returns:
        License key string
    """
    # Get package code
    pkg_code = CODE_TO_PACKAGE.get(package, "B")
    
    # Generate random part (8 chars)
    random_part = secrets.token_hex(4).upper()
    
    # Create payload
    payload = f"{pkg_code}{duration_days}-{random_part}"
    
    # Generate checksum (2 chars from HMAC)
    sig = hmac.new(LICENSE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    checksum = sig[:2].upper()
    
    return f"4T-{payload}-{checksum}"


def decode_license_key(key: str) -> Optional[Tuple[str, int]]:
    """
    Decode a license key offline (no server needed).
    
    Args:
        key: License key string
        
    Returns:
        Tuple of (package, duration_days) or None if invalid
    """
    try:
        # Parse key format: 4T-{CODE}{DAYS}-{RANDOM8}-{CHECK2}
        parts = key.strip().upper().split("-")
        if len(parts) != 4 or parts[0] != "4T":
            return None
        
        code_days = parts[1]  # e.g., "P30"
        random_part = parts[2]  # e.g., "A1B2C3D4"
        checksum = parts[3]  # e.g., "XY"
        
        # Verify checksum
        payload = f"{code_days}-{random_part}"
        sig = hmac.new(LICENSE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        expected_checksum = sig[:2].upper()
        
        if checksum != expected_checksum:
            print(f"[License] Invalid checksum: {checksum} != {expected_checksum}")
            return None
        
        # Extract package code and days
        pkg_code = code_days[0]
        days_str = code_days[1:]
        
        package = PACKAGE_CODES.get(pkg_code)
        if not package:
            print(f"[License] Unknown package code: {pkg_code}")
            return None
        
        try:
            duration_days = int(days_str)
        except ValueError:
            duration_days = LICENSE_DURATION_DAYS
        
        return (package, duration_days)
        
    except Exception as e:
        print(f"[License] Decode error: {e}")
        return None


def is_valid_license_key(key: str) -> bool:
    """Quick check if key format is valid (offline)"""
    return decode_license_key(key) is not None


def get_package_from_key(key: str) -> Optional[str]:
    """Get package type from license key (offline)"""
    result = decode_license_key(key)
    if result:
        return result[0]
    return None


def get_expiry_from_key(key: str, activated_at: datetime = None) -> Optional[datetime]:
    """Calculate expiry date from key (offline)"""
    result = decode_license_key(key)
    if result:
        _, duration_days = result
        start = activated_at or datetime.now()
        return start + timedelta(days=duration_days)
    return None


# For testing
if __name__ == "__main__":
    # Generate sample keys
    for pkg in [Packages.BASIC, Packages.PRO, Packages.PREMIUM]:
        key = generate_license_key(pkg, 30)
        decoded = decode_license_key(key)
        print(f"{pkg}: {key} -> {decoded}")
