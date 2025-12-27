"""
Trial Protection Module for FourT Helper Backend

Prevents trial abuse through IP tracking, fingerprint detection,
and cooldown periods.
"""

import logging
from typing import Optional, Dict, Any, NamedTuple
from datetime import datetime, timedelta
from backend import database as db

logger = logging.getLogger(__name__)


class AbuseCheckResult(NamedTuple):
    """Result of abuse check"""
    is_abused: bool
    message: str
    abuse_type: Optional[str] = None


class TrialProtection:
    """
    Trial abuse detection and prevention
    
    Features:
    - Track IP to device mappings
    - Detect multiple devices from same IP
    - Cooldown period after trial expiration
    - Device fingerprint change detection
    """
    
    # Limits
    MAX_DEVICES_PER_IP = 2  # Max devices starting trial from same IP
    MAX_IPS_PER_DEVICE = 5  # Max IPs a device can use
    TRIAL_COOLDOWN_DAYS = 30  # Days before another trial allowed
    
    def __init__(self):
        logger.info("[TrialProtection] Initialized")
    
    async def check_abuse(
        self,
        device_id: str,
        ip_address: str,
        fingerprint: str = None
    ) -> AbuseCheckResult:
        """
        Check for trial abuse
        
        Args:
            device_id: Device identifier
            ip_address: Client IP
            fingerprint: Optional device fingerprint
            
        Returns:
            AbuseCheckResult with abuse status and message
        """
        
        # 1. Check if device already had a trial
        device = await db.get_device(device_id)
        if device:
            trial_expires = device.get("trial_expires_at")
            if trial_expires:
                expires_dt = datetime.fromisoformat(trial_expires)
                
                # Check if trial is still active
                if datetime.now() < expires_dt:
                    # Trial still active - not abuse
                    return AbuseCheckResult(False, "Trial active")
                
                # Trial expired - check cooldown
                cooldown_end = expires_dt + timedelta(days=self.TRIAL_COOLDOWN_DAYS)
                if datetime.now() < cooldown_end:
                    remaining = (cooldown_end - datetime.now()).days
                    return AbuseCheckResult(
                        is_abused=True,
                        message=f"Trial already used. Wait {remaining} days for new trial.",
                        abuse_type="COOLDOWN"
                    )
        
        # 2. Check IP reputation
        ip_abuse = await self._check_ip_abuse(ip_address, device_id)
        if ip_abuse.is_abused:
            return ip_abuse
        
        # 3. Check fingerprint if provided
        if fingerprint:
            fp_abuse = await self._check_fingerprint_abuse(fingerprint, device_id)
            if fp_abuse.is_abused:
                return fp_abuse
        
        # All checks passed
        return AbuseCheckResult(False, "OK")
    
    async def _check_ip_abuse(
        self,
        ip_address: str,
        device_id: str
    ) -> AbuseCheckResult:
        """Check for IP-based abuse"""
        
        # Get all devices that used this IP
        devices_with_ip = await self._get_devices_by_ip(ip_address)
        
        # Filter out current device
        other_devices = [d for d in devices_with_ip if d != device_id]
        
        if len(other_devices) >= self.MAX_DEVICES_PER_IP:
            await db.log_security_event(
                event_type="TRIAL_IP_ABUSE",
                ip_address=ip_address,
                device_id=device_id,
                details={
                    "devices_count": len(other_devices) + 1,
                    "limit": self.MAX_DEVICES_PER_IP
                }
            )
            
            return AbuseCheckResult(
                is_abused=True,
                message="Too many trial activations from this network",
                abuse_type="IP_ABUSE"
            )
        
        return AbuseCheckResult(False, "OK")
    
    async def _check_fingerprint_abuse(
        self,
        fingerprint: str,
        device_id: str
    ) -> AbuseCheckResult:
        """Check for fingerprint-based abuse"""
        
        # Look for other devices with same fingerprint
        async with db.get_db() as conn:
            cursor = await conn.execute(
                """SELECT device_id FROM devices 
                   WHERE device_fingerprint = ? 
                   AND device_id != ?
                   AND trial_expires_at IS NOT NULL""",
                (fingerprint, device_id)
            )
            other_devices = await cursor.fetchall()
        
        if other_devices:
            await db.log_security_event(
                event_type="TRIAL_FINGERPRINT_ABUSE",
                device_id=device_id,
                details={
                    "fingerprint_prefix": fingerprint[:8],
                    "matching_devices": len(other_devices)
                }
            )
            
            return AbuseCheckResult(
                is_abused=True,
                message="Device fingerprint already used for trial",
                abuse_type="FINGERPRINT_ABUSE"
            )
        
        return AbuseCheckResult(False, "OK")
    
    async def _get_devices_by_ip(self, ip_address: str) -> list:
        """Get all device IDs that have used this IP"""
        async with db.get_db() as conn:
            cursor = await conn.execute(
                """SELECT device_id, ip_addresses FROM devices 
                   WHERE trial_started_at IS NOT NULL"""
            )
            rows = await cursor.fetchall()
        
        import json
        devices = []
        for row in rows:
            ip_list = json.loads(row['ip_addresses'] or '[]')
            if ip_address in ip_list:
                devices.append(row['device_id'])
        
        return devices
    
    async def record_trial_start(
        self,
        device_id: str,
        ip_address: str,
        fingerprint: str = None
    ):
        """Record trial start for tracking"""
        
        # Update device with fingerprint if provided
        if fingerprint:
            await db.update_device(device_id, {"device_fingerprint": fingerprint})
        
        logger.info(f"[TrialProtection] Recorded trial start for {device_id}")


# Global instance
trial_protection = TrialProtection()
