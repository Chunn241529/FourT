"""
IP Manager for FourT Helper Backend

Manages IP blacklist and whitelist with database persistence.
Provides utilities for checking, adding, and removing IPs.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from backend import database as db

logger = logging.getLogger(__name__)


class IPManager:
    """
    Manages IP blacklist and whitelist
    
    Features:
    - Add/remove IPs to blacklist/whitelist
    - Check if IP is blocked or allowed
    - Time-based temporary blocks
    - Violation tracking
    - Bulk operations
    """
    
    # Default block duration
    DEFAULT_BLOCK_HOURS = 24
    
    # Permanent block marker
    PERMANENT_BLOCK = "9999-12-31T23:59:59"
    
    def __init__(self):
        self._whitelist_cache: set = {"127.0.0.1", "::1"}  # Default localhost
        self._blacklist_cache: set = set()
        logger.info("[IPManager] Initialized")
    
    # ============== Blacklist Operations ==============
    
    async def is_blacklisted(self, ip: str) -> bool:
        """Check if IP is currently blacklisted"""
        # Check cache first
        if ip in self._blacklist_cache:
            return True
        
        # Check database
        is_blocked = await db.is_ip_blacklisted(ip)
        if is_blocked:
            self._blacklist_cache.add(ip)
        return is_blocked
    
    async def add_to_blacklist(
        self,
        ip: str,
        reason: str = "Manual block",
        hours: int = None,
        permanent: bool = False
    ) -> bool:
        """
        Add IP to blacklist
        
        Args:
            ip: IP address to block
            reason: Reason for blocking
            hours: Block duration in hours (None = use default)
            permanent: If True, block permanently
        """
        if permanent:
            blocked_until = self.PERMANENT_BLOCK
        else:
            duration = hours or self.DEFAULT_BLOCK_HOURS
            blocked_until = (datetime.now() + timedelta(hours=duration)).isoformat()
        
        success = await db.add_to_blacklist(ip, reason, blocked_until)
        
        if success:
            self._blacklist_cache.add(ip)
            logger.info(f"[IPManager] Blacklisted {ip} until {blocked_until}: {reason}")
        
        return success
    
    async def remove_from_blacklist(self, ip: str) -> bool:
        """Remove IP from blacklist"""
        success = await db.remove_from_blacklist(ip)
        
        if success:
            self._blacklist_cache.discard(ip)
            logger.info(f"[IPManager] Removed {ip} from blacklist")
        
        return success
    
    async def get_blacklist(self) -> List[Dict[str, Any]]:
        """Get all blacklisted IPs"""
        async with db.get_db() as conn:
            cursor = await conn.execute(
                """SELECT ip_address, blocked_at, blocked_until, reason, violation_count 
                   FROM ip_blacklist 
                   ORDER BY blocked_at DESC"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def clear_expired_blacklist(self) -> int:
        """Remove expired blacklist entries"""
        async with db.get_db() as conn:
            cursor = await conn.execute(
                """DELETE FROM ip_blacklist 
                   WHERE blocked_until IS NOT NULL 
                   AND blocked_until < datetime('now')
                   AND blocked_until != ?""",
                (self.PERMANENT_BLOCK,)
            )
            await conn.commit()
            count = cursor.rowcount
            
            # Clear cache
            self._blacklist_cache.clear()
            
            logger.info(f"[IPManager] Cleared {count} expired blacklist entries")
            return count
    
    # ============== Whitelist Operations ==============
    
    async def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        # Check in-memory cache first (includes localhost)
        if ip in self._whitelist_cache:
            return True
        
        return await db.is_ip_whitelisted(ip)
    
    async def add_to_whitelist(self, ip: str, description: str = "") -> bool:
        """Add IP to whitelist"""
        success = await db.add_to_whitelist(ip, description)
        
        if success:
            self._whitelist_cache.add(ip)
            logger.info(f"[IPManager] Whitelisted {ip}: {description}")
        
        return success
    
    async def remove_from_whitelist(self, ip: str) -> bool:
        """Remove IP from whitelist"""
        async with db.get_db() as conn:
            await conn.execute(
                "DELETE FROM ip_whitelist WHERE ip_address = ?",
                (ip,)
            )
            await conn.commit()
        
        self._whitelist_cache.discard(ip)
        logger.info(f"[IPManager] Removed {ip} from whitelist")
        return True
    
    async def get_whitelist(self) -> List[Dict[str, Any]]:
        """Get all whitelisted IPs"""
        async with db.get_db() as conn:
            cursor = await conn.execute(
                """SELECT ip_address, description, added_at 
                   FROM ip_whitelist 
                   ORDER BY added_at DESC"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ============== Utility Methods ==============
    
    async def check_ip(self, ip: str) -> Dict[str, Any]:
        """
        Get full status of an IP
        
        Returns dict with:
        - is_blacklisted: bool
        - is_whitelisted: bool
        - blacklist_info: dict or None
        - whitelist_info: dict or None
        """
        result = {
            "ip": ip,
            "is_blacklisted": False,
            "is_whitelisted": False,
            "blacklist_info": None,
            "whitelist_info": None
        }
        
        async with db.get_db() as conn:
            # Check blacklist
            cursor = await conn.execute(
                """SELECT * FROM ip_blacklist 
                   WHERE ip_address = ? 
                   AND (blocked_until IS NULL OR blocked_until > datetime('now'))""",
                (ip,)
            )
            row = await cursor.fetchone()
            if row:
                result["is_blacklisted"] = True
                result["blacklist_info"] = dict(row)
            
            # Check whitelist
            cursor = await conn.execute(
                "SELECT * FROM ip_whitelist WHERE ip_address = ?",
                (ip,)
            )
            row = await cursor.fetchone()
            if row:
                result["is_whitelisted"] = True
                result["whitelist_info"] = dict(row)
        
        return result
    
    async def get_stats(self) -> Dict[str, int]:
        """Get IP management statistics"""
        async with db.get_db() as conn:
            # Count blacklisted
            cursor = await conn.execute(
                """SELECT COUNT(*) as count FROM ip_blacklist 
                   WHERE blocked_until IS NULL OR blocked_until > datetime('now')"""
            )
            blacklist_count = (await cursor.fetchone())['count']
            
            # Count whitelisted
            cursor = await conn.execute("SELECT COUNT(*) as count FROM ip_whitelist")
            whitelist_count = (await cursor.fetchone())['count']
            
            # Count expired (pending cleanup)
            cursor = await conn.execute(
                """SELECT COUNT(*) as count FROM ip_blacklist 
                   WHERE blocked_until IS NOT NULL 
                   AND blocked_until < datetime('now')
                   AND blocked_until != ?""",
                (self.PERMANENT_BLOCK,)
            )
            expired_count = (await cursor.fetchone())['count']
        
        return {
            "blacklisted": blacklist_count,
            "whitelisted": whitelist_count,
            "expired_pending_cleanup": expired_count
        }


# Global instance
ip_manager = IPManager()
