"""
Utility functions for device identification and network information
Offline-first: No external API calls for device identification
"""

import uuid
import socket


def get_device_id() -> str:
    """
    Generate a unique device ID based on MAC address.

    Returns:
        String representation of the device ID (based on MAC address)
    """
    mac = uuid.getnode()
    return str(mac)


def get_local_ipv4() -> str:
    """
    Get local IP address (no external API call).

    Returns:
        Local IP address or 'local' if unable to determine
    """
    try:
        # Get local IP by connecting to a non-existent address (no actual connection made)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "local"


def get_public_ip() -> str:
    """
    Get public IP address from external API.
    Tries multiple providers for reliability.

    Returns:
        Public IP address or 'unknown' if unable to determine
    """
    import requests

    # List of public IP APIs (ordered by reliability/speed)
    apis = [
        ("https://api.ipify.org", lambda r: r.text.strip()),
        (
            "https://httpbin.org/ip",
            lambda r: r.json().get("origin", "").split(",")[0].strip(),
        ),
        ("https://icanhazip.com", lambda r: r.text.strip()),
        ("https://ifconfig.me/ip", lambda r: r.text.strip()),
    ]

    for url, parser in apis:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                ip = parser(response)
                if ip and _is_valid_ip(ip):
                    return ip
        except Exception:
            continue

    # Fallback to local IP if all APIs fail
    return get_local_ipv4()


def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format"""
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False
