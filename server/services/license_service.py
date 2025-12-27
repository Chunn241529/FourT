"""
License Service for FourT Helper Admin
Handles all license data operations using SQLite database
"""

import sqlite3
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Database path
DATABASE_PATH = Path("data/fourthelper.db")


class LicenseService:
    """Service for managing user licenses via SQLite"""
    
    def __init__(self, licenses_file: Path = None):
        """
        Initialize LicenseService.
        licenses_file parameter is kept for backward compatibility but ignored.
        """
        self.db_path = DATABASE_PATH
        self.licenses = {}  # Cache for compatibility
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def load_licenses(self) -> dict:
        """Load licenses from SQLite database"""
        self.licenses = {}
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC")
                rows = cursor.fetchall()
                
                for row in rows:
                    license_key = row['license_key']
                    self.licenses[license_key] = dict(row)
                    
        except Exception as e:
            print(f"[LicenseService] Error loading licenses: {e}")
        
        return self.licenses
    
    def save_licenses(self) -> bool:
        """
        Save licenses - for compatibility only.
        Individual operations now save directly to database.
        """
        return True
    
    def get_all_licenses(self) -> dict:
        """Get all licenses"""
        self.load_licenses()  # Refresh from database
        return self.licenses
    
    def get_license(self, license_key: str) -> Optional[dict]:
        """Get a specific license by key"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM licenses WHERE license_key = ?",
                    (license_key,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            print(f"[LicenseService] Error getting license: {e}")
        return None
    
    def generate_license_key(self, package: str) -> str:
        """Generate a unique license key"""
        short_uuid = uuid.uuid4().hex[:8].upper()
        return f"LICENSE-{package.upper()}-{short_uuid}"
    
    def add_license(self, license_key: str, package: str, days: int, notes: str = "") -> bool:
        """Add a new license with expiration"""
        try:
            # Check if exists
            existing = self.get_license(license_key)
            if existing:
                return False  # Already exists
            
            now = datetime.now()
            expires_at = now + timedelta(days=days)
            
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO licenses 
                    (license_key, package, device_id, ipv4, activated_at, 
                     expires_at, created_at, user_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    license_key,
                    package.lower(),
                    None,  # device_id - set when activated
                    None,  # ipv4
                    None,  # activated_at
                    expires_at.isoformat(),
                    now.isoformat(),
                    None,  # user_id
                    notes
                ))
                conn.commit()
            
            # Update cache
            self.licenses[license_key] = {
                "license_key": license_key,
                "package": package.lower(),
                "device_id": None,
                "ipv4": None,
                "activated_at": None,
                "expires_at": expires_at.isoformat(),
                "created_at": now.isoformat(),
                "user_id": None,
                "notes": notes
            }
            return True
            
        except Exception as e:
            print(f"[LicenseService] Error adding license: {e}")
            return False
    
    def update_license(self, license_key: str, package: str = None, days: int = None, notes: str = None) -> bool:
        """Update an existing license"""
        try:
            existing = self.get_license(license_key)
            if not existing:
                return False
            
            updates = []
            values = []
            
            if package is not None:
                updates.append("package = ?")
                values.append(package.lower())
            
            if days is not None:
                expires_at = datetime.now() + timedelta(days=days)
                updates.append("expires_at = ?")
                values.append(expires_at.isoformat())
            
            if notes is not None:
                updates.append("notes = ?")
                values.append(notes)
            
            if not updates:
                return True  # Nothing to update
            
            values.append(license_key)
            
            with self._get_connection() as conn:
                query = f"UPDATE licenses SET {', '.join(updates)} WHERE license_key = ?"
                conn.execute(query, values)
                conn.commit()
            
            # Refresh cache
            self.load_licenses()
            return True
            
        except Exception as e:
            print(f"[LicenseService] Error updating license: {e}")
            return False
    
    def update_package(self, license_key: str, new_package: str) -> bool:
        """Update license package"""
        return self.update_license(license_key, package=new_package)
    
    def delete_license(self, license_key: str) -> bool:
        """Delete a license"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM licenses WHERE license_key = ?",
                    (license_key,)
                )
                conn.commit()
            
            # Update cache
            if license_key in self.licenses:
                del self.licenses[license_key]
            
            return True
            
        except Exception as e:
            print(f"[LicenseService] Error deleting license: {e}")
            return False
    
    def get_license_list(self) -> list:
        """Get licenses as list of tuples for display (key, data)"""
        self.load_licenses()
        return list(self.licenses.items())
