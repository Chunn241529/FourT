"""
Database Module for FourT Helper Backend
SQLite3 with async support using aiosqlite

This module replaces the old db.py JSON file storage with proper database.
"""

import sqlite3
import aiosqlite
import json
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file path
DATA_DIR = Path("data")
DATABASE_PATH = DATA_DIR / "fourthelper.db"


def init_database():
    """Initialize database with all tables"""
    DATA_DIR.mkdir(exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.executescript(
            """
            -- Licenses table
            CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                package TEXT NOT NULL,
                device_id TEXT,
                device_fingerprint TEXT,
                ipv4 TEXT,
                activated_at DATETIME,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                notes TEXT,
                transaction_id TEXT,
                transaction_date TEXT,
                gateway TEXT
            );
            
            -- Devices table (for trial tracking)
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_fingerprint TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                trial_started_at DATETIME,
                trial_expires_at DATETIME,
                ip_addresses TEXT DEFAULT '[]',
                failed_attempts INTEGER DEFAULT 0,
                locked_until DATETIME
            );
            
            -- Orders table
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                package TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                device_id TEXT,
                payment_verified INTEGER DEFAULT 0,
                license_key TEXT,
                verified_at DATETIME,
                transaction_id TEXT,
                gateway TEXT,
                created_offline INTEGER DEFAULT 0,
                synced_at DATETIME
            );
            
            -- Security events log
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                ip_address TEXT,
                device_id TEXT,
                endpoint TEXT,
                details TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_security_events_type 
                ON security_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_security_events_timestamp 
                ON security_events(timestamp);
            
            -- Rate limiting tracking
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                request_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_rate_limits_ip_time 
                ON rate_limits(ip_address, request_time);
            
            -- IP Blacklist
            CREATE TABLE IF NOT EXISTS ip_blacklist (
                ip_address TEXT PRIMARY KEY,
                blocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                blocked_until DATETIME,
                reason TEXT,
                violation_count INTEGER DEFAULT 1
            );
            
            -- IP Whitelist
            CREATE TABLE IF NOT EXISTS ip_whitelist (
                ip_address TEXT PRIMARY KEY,
                description TEXT,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Releases table (quản lý versions)
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                name TEXT,
                published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                prerelease INTEGER DEFAULT 0,
                changelog TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_releases_version ON releases(version);
            
            -- Release assets table (files của mỗi version)
            CREATE TABLE IF NOT EXISTS release_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                release_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                size INTEGER DEFAULT 0,
                download_count INTEGER DEFAULT 0,
                download_url TEXT,
                last_download DATETIME,
                FOREIGN KEY (release_id) REFERENCES releases(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_release_assets_release ON release_assets(release_id);
            
            -- Download stats table (tổng downloads)
            CREATE TABLE IF NOT EXISTS download_stats (
                id INTEGER PRIMARY KEY DEFAULT 1,
                total_downloads INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Initialize download_stats with single row if not exists
            INSERT OR IGNORE INTO download_stats (id, total_downloads) VALUES (1, 0);
            
            -- ============== Community Auth Tables ==============
            
            -- Community users table
            CREATE TABLE IF NOT EXISTS community_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                points INTEGER DEFAULT 5,
                total_points_earned INTEGER DEFAULT 5,
                rank VARCHAR(20) DEFAULT 'newcomer',
                avatar_url VARCHAR(255),
                bio TEXT,
                is_verified INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                last_login DATETIME,
                last_checkin DATETIME,
                checkin_streak INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_community_users_email ON community_users(email);
            CREATE INDEX IF NOT EXISTS idx_community_users_username ON community_users(username);
            
            -- Refresh tokens for JWT auth
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash VARCHAR(255) NOT NULL,
                expires_at DATETIME NOT NULL,
                revoked INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES community_users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
            
            -- User devices linking
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id VARCHAR(255) NOT NULL,
                device_name VARCHAR(100),
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES community_users(id) ON DELETE CASCADE,
                UNIQUE(user_id, device_id)
            );
            
            -- ============== Community MIDI Tables ==============
            
            -- MIDI files uploaded by community
            CREATE TABLE IF NOT EXISTS midi_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                uploader_id INTEGER NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                file_size INTEGER DEFAULT 0,
                duration_seconds FLOAT,
                midi_type VARCHAR(20) DEFAULT 'normal',
                download_count INTEGER DEFAULT 0,
                avg_rating FLOAT DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                tags VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME,
                FOREIGN KEY (uploader_id) REFERENCES community_users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_midi_files_uploader ON midi_files(uploader_id);
            CREATE INDEX IF NOT EXISTS idx_midi_files_status ON midi_files(status);
            
            -- Ratings for MIDI files
            CREATE TABLE IF NOT EXISTS midi_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                midi_id INTEGER NOT NULL,
                stars INTEGER CHECK (stars BETWEEN 1 AND 5),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES community_users(id) ON DELETE CASCADE,
                FOREIGN KEY (midi_id) REFERENCES midi_files(id) ON DELETE CASCADE,
                UNIQUE(user_id, midi_id)
            );
            
            -- Comments on MIDI files
            CREATE TABLE IF NOT EXISTS midi_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                midi_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                likes INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES community_users(id) ON DELETE CASCADE,
                FOREIGN KEY (midi_id) REFERENCES midi_files(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_midi_comments_midi ON midi_comments(midi_id);
            
            -- MIDI download tracking
            CREATE TABLE IF NOT EXISTS midi_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                midi_id INTEGER NOT NULL,
                points_spent INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES community_users(id) ON DELETE CASCADE,
                FOREIGN KEY (midi_id) REFERENCES midi_files(id) ON DELETE CASCADE
            );
            
            -- Point transactions log
            CREATE TABLE IF NOT EXISTS point_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason VARCHAR(50) NOT NULL,
                reference_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES community_users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_point_transactions_user ON point_transactions(user_id);
        """
        )
        logger.info("[Database] Initialized successfully")


@asynccontextmanager
async def get_db():
    """Async context manager for database connections"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


def get_db_sync():
    """Synchronous database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============== License Operations ==============


async def get_license(license_key: str) -> Optional[Dict[str, Any]]:
    """Get license by key"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM licenses WHERE license_key = ?", (license_key,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def create_license(license_data: Dict[str, Any]) -> bool:
    """Create a new license"""
    async with get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO licenses 
                (license_key, package, device_id, device_fingerprint, ipv4, 
                 activated_at, expires_at, created_at, user_id, notes,
                 transaction_id, transaction_date, gateway)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    license_data.get("license_key"),
                    license_data.get("package"),
                    license_data.get("device_id"),
                    license_data.get("device_fingerprint"),
                    license_data.get("ipv4"),
                    license_data.get("activated_at"),
                    license_data.get("expires_at"),
                    license_data.get("created_at", datetime.now().isoformat()),
                    license_data.get("user_id"),
                    license_data.get("notes"),
                    license_data.get("transaction_id"),
                    license_data.get("transaction_date"),
                    license_data.get("gateway"),
                ),
            )
            await db.commit()
            logger.info(
                f"[Database] Created license: {license_data.get('license_key')}"
            )
            return True
        except Exception as e:
            logger.error(f"[Database] Error creating license: {e}")
            return False


async def update_license(license_key: str, updates: Dict[str, Any]) -> bool:
    """Update license data"""
    async with get_db() as db:
        try:
            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            values.append(license_key)

            query = (
                f"UPDATE licenses SET {', '.join(set_clauses)} WHERE license_key = ?"
            )
            await db.execute(query, values)
            await db.commit()
            logger.info(f"[Database] Updated license: {license_key}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error updating license: {e}")
            return False


async def delete_license(license_key: str) -> bool:
    """Delete a license"""
    async with get_db() as db:
        try:
            await db.execute(
                "DELETE FROM licenses WHERE license_key = ?", (license_key,)
            )
            await db.commit()
            logger.info(f"[Database] Deleted license: {license_key}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error deleting license: {e}")
            return False


async def get_all_licenses() -> List[Dict[str, Any]]:
    """Get all licenses"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM licenses ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============== Device Operations ==============


async def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    """Get device by ID"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        )
        row = await cursor.fetchone()
        if row:
            result = dict(row)
            # Parse ip_addresses JSON
            result["ip_addresses"] = json.loads(result.get("ip_addresses", "[]"))
            return result
        return None


async def create_device(device_data: Dict[str, Any]) -> bool:
    """Create a new device record"""
    async with get_db() as db:
        try:
            ip_addresses = device_data.get("ip_addresses", [])
            if isinstance(ip_addresses, list):
                ip_addresses = json.dumps(ip_addresses)

            await db.execute(
                """
                INSERT INTO devices 
                (device_id, device_fingerprint, first_seen, last_seen,
                 trial_started_at, trial_expires_at, ip_addresses,
                 failed_attempts, locked_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    device_data.get("device_id"),
                    device_data.get("device_fingerprint"),
                    device_data.get("first_seen", datetime.now().isoformat()),
                    device_data.get("last_seen", datetime.now().isoformat()),
                    device_data.get("trial_started_at"),
                    device_data.get("trial_expires_at"),
                    ip_addresses,
                    device_data.get("failed_attempts", 0),
                    device_data.get("locked_until"),
                ),
            )
            await db.commit()
            logger.info(f"[Database] Created device: {device_data.get('device_id')}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error creating device: {e}")
            return False


async def update_device(device_id: str, updates: Dict[str, Any]) -> bool:
    """Update device data"""
    async with get_db() as db:
        try:
            # Handle ip_addresses JSON
            if "ip_addresses" in updates and isinstance(updates["ip_addresses"], list):
                updates["ip_addresses"] = json.dumps(updates["ip_addresses"])

            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            values.append(device_id)

            query = f"UPDATE devices SET {', '.join(set_clauses)} WHERE device_id = ?"
            await db.execute(query, values)
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Database] Error updating device: {e}")
            return False


async def get_all_devices() -> List[Dict[str, Any]]:
    """Get all devices"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices ORDER BY last_seen DESC")
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            device = dict(row)
            device["ip_addresses"] = json.loads(device.get("ip_addresses", "[]"))
            result.append(device)
        return result


# ============== Order Operations ==============


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Get order by ID"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        )
        row = await cursor.fetchone()
        if row:
            result = dict(row)
            # Convert SQLite integer to boolean
            result["payment_verified"] = bool(result.get("payment_verified", 0))
            result["created_offline"] = bool(result.get("created_offline", 0))
            return result
        return None


async def create_order(order_data: Dict[str, Any]) -> bool:
    """Create a new order"""
    async with get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO orders 
                (order_id, package, amount, status, created_at, user_id, device_id,
                 payment_verified, license_key, verified_at, transaction_id, gateway,
                 created_offline, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    order_data.get("order_id"),
                    order_data.get("package"),
                    order_data.get("amount"),
                    order_data.get("status", "pending"),
                    order_data.get("created_at", datetime.now().isoformat()),
                    order_data.get("user_id"),
                    order_data.get("device_id"),
                    1 if order_data.get("payment_verified") else 0,
                    order_data.get("license_key"),
                    order_data.get("verified_at"),
                    order_data.get("transaction_id"),
                    order_data.get("gateway"),
                    1 if order_data.get("created_offline") else 0,
                    order_data.get("synced_at"),
                ),
            )
            await db.commit()
            logger.info(f"[Database] Created order: {order_data.get('order_id')}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error creating order: {e}")
            return False


async def update_order(order_id: str, updates: Dict[str, Any]) -> bool:
    """Update order data"""
    async with get_db() as db:
        try:
            # Convert boolean to integer for SQLite
            if "payment_verified" in updates:
                updates["payment_verified"] = 1 if updates["payment_verified"] else 0
            if "created_offline" in updates:
                updates["created_offline"] = 1 if updates["created_offline"] else 0

            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            values.append(order_id)

            query = f"UPDATE orders SET {', '.join(set_clauses)} WHERE order_id = ?"
            await db.execute(query, values)
            await db.commit()
            logger.info(f"[Database] Updated order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error updating order: {e}")
            return False


async def get_all_orders() -> List[Dict[str, Any]]:
    """Get all orders"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM orders ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            order = dict(row)
            order["payment_verified"] = bool(order.get("payment_verified", 0))
            order["created_offline"] = bool(order.get("created_offline", 0))
            result.append(order)
        return result


# ============== Security Event Operations ==============


async def log_security_event(
    event_type: str,
    ip_address: str = None,
    device_id: str = None,
    endpoint: str = None,
    details: Dict = None,
) -> bool:
    """Log a security event"""
    async with get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO security_events 
                (event_type, ip_address, device_id, endpoint, details)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    event_type,
                    ip_address,
                    device_id,
                    endpoint,
                    json.dumps(details) if details else None,
                ),
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Database] Error logging security event: {e}")
            return False


async def get_security_events(
    event_type: str = None, limit: int = 100
) -> List[Dict[str, Any]]:
    """Get security events with optional filtering"""
    async with get_db() as db:
        if event_type:
            cursor = await db.execute(
                "SELECT * FROM security_events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            event = dict(row)
            if event.get("details"):
                event["details"] = json.loads(event["details"])
            result.append(event)
        return result


# ============== IP Blacklist/Whitelist Operations ==============


async def is_ip_blacklisted(ip_address: str) -> bool:
    """Check if IP is blacklisted"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM ip_blacklist 
               WHERE ip_address = ? 
               AND (blocked_until IS NULL OR blocked_until > datetime('now'))""",
            (ip_address,),
        )
        row = await cursor.fetchone()
        return row is not None


async def add_to_blacklist(
    ip_address: str, reason: str = None, blocked_until: str = None
) -> bool:
    """Add IP to blacklist"""
    async with get_db() as db:
        try:
            # Check if already exists
            cursor = await db.execute(
                "SELECT violation_count FROM ip_blacklist WHERE ip_address = ?",
                (ip_address,),
            )
            existing = await cursor.fetchone()

            if existing:
                # Update violation count
                await db.execute(
                    """UPDATE ip_blacklist 
                       SET violation_count = violation_count + 1, 
                           reason = COALESCE(?, reason),
                           blocked_until = COALESCE(?, blocked_until)
                       WHERE ip_address = ?""",
                    (reason, blocked_until, ip_address),
                )
            else:
                await db.execute(
                    """INSERT INTO ip_blacklist 
                       (ip_address, reason, blocked_until, violation_count)
                       VALUES (?, ?, ?, 1)""",
                    (ip_address, reason, blocked_until),
                )
            await db.commit()
            logger.info(f"[Database] Added/updated IP blacklist: {ip_address}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error adding to blacklist: {e}")
            return False


async def remove_from_blacklist(ip_address: str) -> bool:
    """Remove IP from blacklist"""
    async with get_db() as db:
        try:
            await db.execute(
                "DELETE FROM ip_blacklist WHERE ip_address = ?", (ip_address,)
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Database] Error removing from blacklist: {e}")
            return False


async def is_ip_whitelisted(ip_address: str) -> bool:
    """Check if IP is whitelisted"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM ip_whitelist WHERE ip_address = ?", (ip_address,)
        )
        row = await cursor.fetchone()
        return row is not None


async def add_to_whitelist(ip_address: str, description: str = None) -> bool:
    """Add IP to whitelist"""
    async with get_db() as db:
        try:
            await db.execute(
                """INSERT OR REPLACE INTO ip_whitelist 
                   (ip_address, description)
                   VALUES (?, ?)""",
                (ip_address, description),
            )
            await db.commit()
            logger.info(f"[Database] Added IP to whitelist: {ip_address}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error adding to whitelist: {e}")
            return False


# ============== Rate Limiting Operations ==============


async def record_request(ip_address: str, endpoint: str) -> bool:
    """Record a request for rate limiting"""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO rate_limits (ip_address, endpoint) VALUES (?, ?)",
                (ip_address, endpoint),
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Database] Error recording request: {e}")
            return False


async def get_request_count(ip_address: str, endpoint: str, window_seconds: int) -> int:
    """Get request count for IP within time window"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT COUNT(*) as count FROM rate_limits 
               WHERE ip_address = ? 
               AND endpoint = ?
               AND request_time > datetime('now', ?)""",
            (ip_address, endpoint, f"-{window_seconds} seconds"),
        )
        row = await cursor.fetchone()
        return row["count"] if row else 0


async def cleanup_old_rate_limits(older_than_seconds: int = 3600) -> int:
    """Clean up old rate limit records"""
    async with get_db() as db:
        cursor = await db.execute(
            """DELETE FROM rate_limits 
               WHERE request_time < datetime('now', ?)""",
            (f"-{older_than_seconds} seconds",),
        )
        await db.commit()
        return cursor.rowcount


# ============== Release Operations ==============


async def get_all_releases() -> List[Dict[str, Any]]:
    """Get all releases with their assets"""
    async with get_db() as db:
        # Get all releases
        cursor = await db.execute("SELECT * FROM releases ORDER BY published_at DESC")
        releases_rows = await cursor.fetchall()

        releases = []
        for release_row in releases_rows:
            release = dict(release_row)
            release["prerelease"] = bool(release.get("prerelease", 0))

            # Get assets for this release
            assets_cursor = await db.execute(
                "SELECT * FROM release_assets WHERE release_id = ?", (release["id"],)
            )
            assets_rows = await assets_cursor.fetchall()
            release["assets"] = [dict(asset) for asset in assets_rows]

            releases.append(release)

        return releases


async def get_release_by_version(version: str) -> Optional[Dict[str, Any]]:
    """Get release by version"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM releases WHERE version = ?", (version,)
        )
        row = await cursor.fetchone()
        if row:
            release = dict(row)
            release["prerelease"] = bool(release.get("prerelease", 0))

            # Get assets
            assets_cursor = await db.execute(
                "SELECT * FROM release_assets WHERE release_id = ?", (release["id"],)
            )
            assets_rows = await assets_cursor.fetchall()
            release["assets"] = [dict(asset) for asset in assets_rows]

            return release
        return None


async def create_release(
    version: str,
    name: str = None,
    prerelease: bool = False,
    changelog: str = None,
    published_at: str = None,
) -> Optional[int]:
    """Create a new release, returns release id. Returns existing id if already exists."""
    async with get_db() as db:
        try:
            # First check if exists
            cursor = await db.execute(
                "SELECT id FROM releases WHERE version = ?", (version,)
            )
            existing = await cursor.fetchone()
            if existing:
                return existing[0]  # Return existing id

            await db.execute(
                """
                INSERT INTO releases (version, name, prerelease, changelog, published_at)
                VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            """,
                (
                    version,
                    name or f"FourT v{version}",
                    1 if prerelease else 0,
                    changelog,
                    published_at,
                ),
            )
            await db.commit()

            # Get the inserted id
            cursor = await db.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            release_id = row[0] if row else None

            logger.info(f"[Database] Created release: {version}")
            return release_id
        except Exception as e:
            logger.error(f"[Database] Error creating release: {e}")
            return None


async def update_release(version: str, updates: Dict[str, Any]) -> bool:
    """Update release data"""
    async with get_db() as db:
        try:
            if "prerelease" in updates:
                updates["prerelease"] = 1 if updates["prerelease"] else 0

            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            values.append(version)

            query = f"UPDATE releases SET {', '.join(set_clauses)} WHERE version = ?"
            await db.execute(query, values)
            await db.commit()
            logger.info(f"[Database] Updated release: {version}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error updating release: {e}")
            return False


async def delete_release(version: str) -> bool:
    """Delete a release and its assets"""
    async with get_db() as db:
        try:
            await db.execute("DELETE FROM releases WHERE version = ?", (version,))
            await db.commit()
            logger.info(f"[Database] Deleted release: {version}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error deleting release: {e}")
            return False


async def create_release_asset(
    release_id: int,
    filename: str,
    size: int = 0,
    download_url: str = None,
    download_count: int = 0,
) -> bool:
    """Create a new asset for a release"""
    async with get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO release_assets (release_id, filename, size, download_url, download_count)
                VALUES (?, ?, ?, ?, ?)
            """,
                (release_id, filename, size, download_url, download_count),
            )
            await db.commit()
            logger.info(
                f"[Database] Created asset: {filename} for release {release_id} (count: {download_count})"
            )
            return True
        except Exception as e:
            logger.error(f"[Database] Error creating asset: {e}")
            return False


async def update_release_asset(
    release_id: int, filename: str, updates: Dict[str, Any]
) -> bool:
    """Update asset data"""
    async with get_db() as db:
        try:
            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            values.extend([release_id, filename])

            query = f"UPDATE release_assets SET {', '.join(set_clauses)} WHERE release_id = ? AND filename = ?"
            await db.execute(query, values)
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Database] Error updating asset: {e}")
            return False


async def increment_download_count(version: str, filename: str) -> Dict[str, int]:
    """Increment download count for an asset (total is derived from SUM of assets)"""
    async with get_db() as db:
        try:
            # Get release id
            cursor = await db.execute(
                "SELECT id FROM releases WHERE version = ?", (version,)
            )
            row = await cursor.fetchone()
            if not row:
                logger.warning(
                    f"[Database] increment_download_count: Release {version} not found"
                )
                return {"success": False, "error": "Release not found"}

            release_id = row[0]

            # Increment asset download count
            await db.execute(
                """
                UPDATE release_assets 
                SET download_count = download_count + 1,
                    last_download = CURRENT_TIMESTAMP
                WHERE release_id = ? AND filename = ?
            """,
                (release_id, filename),
            )

            await db.commit()

            logger.info(
                f"[Database] Incremented download count for {filename} v{version}"
            )

            # Get updated counts
            asset_cursor = await db.execute(
                "SELECT download_count FROM release_assets WHERE release_id = ? AND filename = ?",
                (release_id, filename),
            )
            asset_row = await asset_cursor.fetchone()
            asset_count = asset_row[0] if asset_row else 0

            total_cursor = await db.execute(
                "SELECT total_downloads FROM download_stats WHERE id = 1"
            )
            total_row = await total_cursor.fetchone()
            total_count = total_row[0] if total_row else 0

            return {
                "success": True,
                "asset_count": asset_count,
                "total_downloads": total_count,
            }
        except Exception as e:
            logger.error(f"[Database] Error incrementing download: {e}")
            return {"success": False, "error": str(e)}


async def get_download_stats() -> Dict[str, int]:
    """Get total download statistics (SUM of all asset downloads)"""
    async with get_db() as db:
        cursor = await db.execute("SELECT SUM(download_count) FROM release_assets")
        row = await cursor.fetchone()
        total = row[0] if row and row[0] is not None else 0
        return {"total_downloads": total}


async def set_total_downloads(total: int) -> bool:
    """Set total download count"""
    async with get_db() as db:
        try:
            await db.execute(
                "UPDATE download_stats SET total_downloads = ?, last_updated = CURRENT_TIMESTAMP WHERE id = 1",
                (total,),
            )
            await db.commit()
            logger.info(f"[Database] Set total downloads: {total}")
            return True
        except Exception as e:
            logger.error(f"[Database] Error setting total downloads: {e}")
            return False


async def set_asset_download_count(version: str, filename: str, count: int) -> bool:
    """Set download count for a specific asset"""
    async with get_db() as db:
        try:
            cursor = await db.execute(
                "SELECT id FROM releases WHERE version = ?", (version,)
            )
            row = await cursor.fetchone()
            if not row:
                return False
            release_id = row[0]

            # Update asset count
            cursor = await db.execute(
                """
                UPDATE release_assets 
                SET download_count = ?
                WHERE release_id = ? AND filename = ?
            """,
                (count, release_id, filename),
            )

            # If asset not found, create it
            if cursor.rowcount == 0:
                await db.execute(
                    """
                    INSERT INTO release_assets (release_id, filename, download_count)
                    VALUES (?, ?, ?)
                """,
                    (release_id, filename, count),
                )

            await db.commit()
            logger.info(
                f"[Database] Set download count for {filename} v{version}: {count}"
            )
            return True
        except Exception as e:
            logger.error(f"[Database] Error setting asset download count: {e}")
            return False


async def delete_release_asset(release_id: int, filename: str) -> bool:
    """Delete an asset from a release"""
    async with get_db() as db:
        try:
            await db.execute(
                "DELETE FROM release_assets WHERE release_id = ? AND filename = ?",
                (release_id, filename),
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Database] Error deleting asset: {e}")
            return False


# Initialize database on module load
init_database()
