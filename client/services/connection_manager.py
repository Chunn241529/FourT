"""
Connection Manager - Single point for internet connectivity
Checks npoint.io (config service) to verify internet access
"""

import urllib.request
import urllib.error
import threading
from typing import Optional

from core.config import SERVER_CONFIG_URL


class ConnectionManager:
    """
    Manages internet connection status.
    Pings npoint.io (config service) once at startup, cached for session.
    """
    
    _instance: Optional['ConnectionManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._is_online: Optional[bool] = None
        self._check_timeout = 2  # Very short timeout for quick check
    
    @classmethod
    def get_instance(cls) -> 'ConnectionManager':
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def check_connection(self, force: bool = False) -> bool:
        """
        Check if internet is available by pinging npoint.io.
        Only checks once per session unless force=True.
        
        Args:
            force: Force re-check even if already checked
            
        Returns:
            True if internet is available
        """
        if self._is_online is not None and not force:
            return self._is_online
        
        self._is_online = self._ping_internet()
        return self._is_online
    
    def _ping_internet(self) -> bool:
        """Quick ping to npoint.io to check internet availability"""
        try:
            # Ping npoint.io (our config service) to check internet
            req = urllib.request.Request(SERVER_CONFIG_URL, method='HEAD')
            req.add_header('Connection', 'close')
            req.add_header('User-Agent', 'FourT-Helper/1.0')
            
            with urllib.request.urlopen(req, timeout=self._check_timeout) as response:
                is_online = response.status < 500
                print(f"[ConnectionManager] Internet: {'OK' if is_online else 'FAIL'}")
                return is_online
                
        except urllib.error.URLError as e:
            print(f"[ConnectionManager] Internet unreachable: {e.reason}")
            return False
        except Exception as e:
            print(f"[ConnectionManager] Ping error: {e}")
            return False
    
    def is_online(self) -> bool:
        """
        Get cached online status.
        Must call check_connection() first at startup.
        
        Returns:
            True if internet is available (returns False if not checked yet)
        """
        if self._is_online is None:
            return False  # Not checked yet, assume offline
        return self._is_online
    
    def is_offline(self) -> bool:
        """Convenience method for offline check"""
        return not self.is_online()


# Convenience functions
def get_connection_manager() -> ConnectionManager:
    """Get the singleton ConnectionManager instance"""
    return ConnectionManager.get_instance()


def is_server_online() -> bool:
    """Quick check if internet is online (uses cached value)"""
    return get_connection_manager().is_online()


def is_server_offline() -> bool:
    """Quick check if internet is offline (uses cached value)"""
    return get_connection_manager().is_offline()

