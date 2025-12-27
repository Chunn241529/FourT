"""
Attempt Tracker for FourT Helper Backend

Tracks failed authentication attempts and implements lockouts.
Prevents brute-force attacks on license/trial endpoints.
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from backend import database as db

logger = logging.getLogger(__name__)


class AttemptTracker:
    """
    Tracks failed attempts and implements lockout mechanism
    
    Features:
    - Configurable max attempts before lockout
    - Time-based lockout duration
    - Per-identifier tracking (device_id, IP, etc.)
    - Automatic cleanup of old entries
    """
    
    def __init__(
        self,
        max_attempts: int = 5,
        lockout_minutes: int = 30,
        cleanup_interval: int = 300
    ):
        """
        Initialize AttemptTracker
        
        Args:
            max_attempts: Number of failures before lockout
            lockout_minutes: Duration of lockout in minutes
            cleanup_interval: Seconds between cleanup of old entries
        """
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self.cleanup_interval = cleanup_interval
        
        # In-memory tracking
        self._attempts: Dict[str, list] = defaultdict(list)  # id -> [timestamps]
        self._lockouts: Dict[str, float] = {}  # id -> lockout_until_timestamp
        self._last_cleanup = time.time()
        
        logger.info(
            f"[AttemptTracker] Initialized: max={max_attempts}, "
            f"lockout={lockout_minutes}min"
        )
    
    def record_failure(self, identifier: str, ip: str = None) -> Tuple[int, bool]:
        """
        Record a failed attempt
        
        Args:
            identifier: Device ID, license key, or other identifier
            ip: Optional IP address for logging
            
        Returns:
            Tuple of (attempt_count, is_now_locked)
        """
        self._periodic_cleanup()
        
        now = time.time()
        self._attempts[identifier].append(now)
        
        # Count recent attempts (within lockout window)
        window = self.lockout_minutes * 60
        recent = [t for t in self._attempts[identifier] if t > now - window]
        self._attempts[identifier] = recent  # Prune old attempts
        
        attempt_count = len(recent)
        
        # Check if should lockout
        if attempt_count >= self.max_attempts:
            lockout_until = now + (self.lockout_minutes * 60)
            self._lockouts[identifier] = lockout_until
            
            logger.warning(
                f"[AttemptTracker] Locked out {identifier} (IP: {ip}) "
                f"for {self.lockout_minutes} minutes after {attempt_count} failures"
            )
            
            # Log to security events asynchronously
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(db.log_security_event(
                    event_type="LOCKOUT_ACTIVATED",
                    ip_address=ip,
                    device_id=identifier,
                    details={
                        "attempts": attempt_count,
                        "lockout_minutes": self.lockout_minutes
                    }
                ))
            except Exception:
                pass
            
            return attempt_count, True
        
        return attempt_count, False
    
    def record_success(self, identifier: str):
        """Clear failed attempts on successful authentication"""
        if identifier in self._attempts:
            del self._attempts[identifier]
        if identifier in self._lockouts:
            del self._lockouts[identifier]
        logger.debug(f"[AttemptTracker] Cleared attempts for {identifier}")
    
    def is_locked_out(self, identifier: str) -> bool:
        """Check if identifier is currently locked out"""
        if identifier not in self._lockouts:
            return False
        
        lockout_until = self._lockouts[identifier]
        if time.time() >= lockout_until:
            # Lockout expired
            del self._lockouts[identifier]
            return False
        
        return True
    
    def get_lockout_remaining(self, identifier: str) -> Optional[int]:
        """Get remaining lockout time in seconds"""
        if not self.is_locked_out(identifier):
            return None
        
        remaining = int(self._lockouts[identifier] - time.time())
        return max(0, remaining)
    
    def get_attempt_count(self, identifier: str) -> int:
        """Get current attempt count for identifier"""
        if identifier not in self._attempts:
            return 0
        return len(self._attempts[identifier])
    
    def clear_identifier(self, identifier: str):
        """Manually clear all data for an identifier (admin)"""
        if identifier in self._attempts:
            del self._attempts[identifier]
        if identifier in self._lockouts:
            del self._lockouts[identifier]
    
    def _periodic_cleanup(self):
        """Cleanup old entries periodically"""
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return
        
        self._last_cleanup = now
        window = self.lockout_minutes * 60
        
        # Clean expired lockouts
        expired_lockouts = [
            k for k, v in self._lockouts.items()
            if now >= v
        ]
        for k in expired_lockouts:
            del self._lockouts[k]
        
        # Clean old attempts
        empty_keys = []
        for k, attempts in self._attempts.items():
            recent = [t for t in attempts if t > now - window]
            if recent:
                self._attempts[k] = recent
            else:
                empty_keys.append(k)
        
        for k in empty_keys:
            del self._attempts[k]
        
        if expired_lockouts or empty_keys:
            logger.debug(
                f"[AttemptTracker] Cleanup: {len(expired_lockouts)} lockouts, "
                f"{len(empty_keys)} attempt records"
            )
    
    def get_stats(self) -> Dict:
        """Get current tracker statistics"""
        return {
            "active_lockouts": len(self._lockouts),
            "tracked_identifiers": len(self._attempts),
            "max_attempts": self.max_attempts,
            "lockout_minutes": self.lockout_minutes
        }


# Global instances for different use cases
license_attempt_tracker = AttemptTracker(max_attempts=5, lockout_minutes=30)
trial_attempt_tracker = AttemptTracker(max_attempts=3, lockout_minutes=60)
