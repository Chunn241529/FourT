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


# Backwards compatibility alias
get_public_ip = get_local_ipv4

