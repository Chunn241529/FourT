"""
Device Fingerprint Module for FourT Helper

Generates and verifies hardware-based device fingerprints.
Used for stronger device binding than simple device_id.
"""

import hashlib
import platform
import os
import socket
import logging
from typing import Optional, Dict, Any, List
import subprocess

logger = logging.getLogger(__name__)


class DeviceFingerprint:
    """
    Device fingerprinting utility
    
    Collects hardware and system information to create
    a unique fingerprint for each device.
    """
    
    @staticmethod
    def get_cpu_id() -> str:
        """Get CPU identifier"""
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(
                    'wmic cpu get processorid',
                    shell=True, 
                    stderr=subprocess.DEVNULL
                ).decode()
                # Parse output to get just the ID
                lines = [l.strip() for l in output.split('\n') if l.strip()]
                if len(lines) > 1:
                    return lines[1]
            elif platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'Serial' in line:
                            return line.split(':')[1].strip()
            elif platform.system() == "Darwin":  # macOS
                output = subprocess.check_output(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                return output
        except Exception as e:
            logger.debug(f"Could not get CPU ID: {e}")
        return "unknown-cpu"
    
    @staticmethod
    def get_machine_id() -> str:
        """Get machine unique ID"""
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(
                    'wmic csproduct get uuid',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode()
                lines = [l.strip() for l in output.split('\n') if l.strip()]
                if len(lines) > 1:
                    return lines[1]
            elif platform.system() == "Linux":
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            elif platform.system() == "Darwin":
                output = subprocess.check_output(
                    ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in output.split('\n'):
                    if 'IOPlatformUUID' in line:
                        return line.split('"')[-2]
        except Exception as e:
            logger.debug(f"Could not get machine ID: {e}")
        return "unknown-machine"
    
    @staticmethod
    def get_mac_address() -> str:
        """Get primary MAC address"""
        try:
            import uuid
            mac = uuid.getnode()
            return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        except Exception as e:
            logger.debug(f"Could not get MAC: {e}")
        return "00:00:00:00:00:00"
    
    @staticmethod
    def get_volume_serial() -> str:
        """Get boot volume serial number"""
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(
                    'vol C:',
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in output.split('\n'):
                    if 'Serial Number' in line or 'Volume Serial Number' in line:
                        return line.split()[-1]
        except Exception as e:
            logger.debug(f"Could not get volume serial: {e}")
        return "unknown-volume"
    
    @staticmethod
    def get_hostname() -> str:
        """Get machine hostname"""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown-host"
    
    @staticmethod
    def get_os_info() -> str:
        """Get OS version information"""
        return f"{platform.system()}-{platform.release()}-{platform.machine()}"
    
    @classmethod
    def generate_fingerprint(cls, components: List[str] = None) -> str:
        """
        Generate device fingerprint from hardware components
        
        Args:
            components: Optional list of component functions to use.
                       If None, uses all available components.
        
        Returns:
            SHA256 hash of combined components
        """
        if components is None:
            components = [
                cls.get_cpu_id(),
                cls.get_machine_id(),
                cls.get_mac_address(),
                cls.get_volume_serial(),
                cls.get_hostname(),
                cls.get_os_info()
            ]
        
        # Combine components with separator
        combined = '|'.join(str(c) for c in components if c)
        
        # Hash the combined string
        fingerprint = hashlib.sha256(combined.encode()).hexdigest()
        
        logger.debug(f"[DeviceFingerprint] Generated: {fingerprint[:16]}...")
        return fingerprint
    
    @classmethod
    def generate_short_fingerprint(cls) -> str:
        """Generate a shorter 16-character fingerprint"""
        full = cls.generate_fingerprint()
        return full[:16]
    
    @classmethod
    def get_device_info(cls) -> Dict[str, Any]:
        """Get all device information as a dictionary"""
        return {
            "cpu_id": cls.get_cpu_id(),
            "machine_id": cls.get_machine_id(),
            "mac_address": cls.get_mac_address(),
            "volume_serial": cls.get_volume_serial(),
            "hostname": cls.get_hostname(),
            "os_info": cls.get_os_info(),
            "fingerprint": cls.generate_fingerprint()
        }


def verify_device_fingerprint(
    stored_fingerprint: str,
    current_fingerprint: str,
    tolerance: int = 0
) -> bool:
    """
    Verify that current fingerprint matches stored fingerprint
    
    Args:
        stored_fingerprint: Previously saved fingerprint
        current_fingerprint: Current device fingerprint
        tolerance: Number of allowed mismatches (not used with hash)
        
    Returns:
        True if fingerprints match
    """
    if not stored_fingerprint or not current_fingerprint:
        return False
    
    # Direct comparison for hashed fingerprints
    return stored_fingerprint == current_fingerprint


def generate_device_id() -> str:
    """Generate a new device ID based on fingerprint"""
    return DeviceFingerprint.generate_short_fingerprint()


# Convenience instance
device_fingerprint = DeviceFingerprint()
