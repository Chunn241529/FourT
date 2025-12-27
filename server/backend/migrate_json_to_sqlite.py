"""
Migration Script: JSON -> SQLite3
Run once to migrate existing data from JSON files to SQLite database

Usage:
    python -m backend.migrate_json_to_sqlite
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import DATABASE_PATH, init_database


def migrate():
    """Migrate all JSON data to SQLite database"""
    print("[Migration] Starting JSON to SQLite migration...")
    print(f"[Migration] Database path: {DATABASE_PATH}")
    
    # Initialize database first
    init_database()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    data_dir = Path("data")
    migrated_count = {
        "licenses": 0,
        "devices": 0,
        "orders": 0
    }
    
    # Migrate licenses.json
    licenses_file = data_dir / "licenses.json"
    if licenses_file.exists():
        print(f"[Migration] Found {licenses_file}")
        try:
            with open(licenses_file, encoding="utf-8") as f:
                licenses = json.load(f)
            
            for key, data in licenses.items():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO licenses 
                        (license_key, package, device_id, device_fingerprint, ipv4, 
                         activated_at, expires_at, created_at, user_id, notes,
                         transaction_id, transaction_date, gateway)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.get("license_key", key),
                        data.get("package"),
                        data.get("device_id"),
                        data.get("device_fingerprint"),
                        data.get("ipv4"),
                        data.get("activated_at"),
                        data.get("expires_at"),
                        data.get("created_at"),
                        data.get("user_id"),
                        data.get("notes"),
                        data.get("transaction_id"),
                        data.get("transaction_date"),
                        data.get("gateway")
                    ))
                    migrated_count["licenses"] += 1
                except Exception as e:
                    print(f"[Migration] Error migrating license {key}: {e}")
                    
            print(f"[Migration] ✅ Migrated {migrated_count['licenses']} licenses")
        except Exception as e:
            print(f"[Migration] ❌ Error reading licenses.json: {e}")
    else:
        print(f"[Migration] ⚠️ {licenses_file} not found - skipping")
    
    # Migrate devices.json
    devices_file = data_dir / "devices.json"
    if devices_file.exists():
        print(f"[Migration] Found {devices_file}")
        try:
            with open(devices_file, encoding="utf-8") as f:
                devices = json.load(f)
            
            for device_id, data in devices.items():
                try:
                    ip_addresses = data.get("ip_addresses", [])
                    if isinstance(ip_addresses, list):
                        ip_addresses = json.dumps(ip_addresses)
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO devices
                        (device_id, device_fingerprint, first_seen, last_seen, 
                         trial_started_at, trial_expires_at, ip_addresses,
                         failed_attempts, locked_until)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        device_id,
                        data.get("device_fingerprint"),
                        data.get("first_seen"),
                        data.get("last_seen"),
                        data.get("trial_started_at"),
                        data.get("trial_expires_at"),
                        ip_addresses,
                        data.get("failed_attempts", 0),
                        data.get("locked_until")
                    ))
                    migrated_count["devices"] += 1
                except Exception as e:
                    print(f"[Migration] Error migrating device {device_id}: {e}")
                    
            print(f"[Migration] ✅ Migrated {migrated_count['devices']} devices")
        except Exception as e:
            print(f"[Migration] ❌ Error reading devices.json: {e}")
    else:
        print(f"[Migration] ⚠️ {devices_file} not found - skipping")
    
    # Migrate orders.json
    orders_file = data_dir / "orders.json"
    if orders_file.exists():
        print(f"[Migration] Found {orders_file}")
        try:
            with open(orders_file, encoding="utf-8") as f:
                orders = json.load(f)
            
            for order_id, data in orders.items():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO orders
                        (order_id, package, amount, status, created_at, user_id, device_id,
                         payment_verified, license_key, verified_at, transaction_id, gateway,
                         created_offline, synced_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        order_id,
                        data.get("package"),
                        data.get("amount"),
                        data.get("status", "pending"),
                        data.get("created_at"),
                        data.get("user_id"),
                        data.get("device_id"),
                        1 if data.get("payment_verified") else 0,
                        data.get("license_key"),
                        data.get("verified_at"),
                        data.get("transaction_id"),
                        data.get("gateway"),
                        1 if data.get("created_offline") else 0,
                        data.get("synced_at")
                    ))
                    migrated_count["orders"] += 1
                except Exception as e:
                    print(f"[Migration] Error migrating order {order_id}: {e}")
                    
            print(f"[Migration] ✅ Migrated {migrated_count['orders']} orders")
        except Exception as e:
            print(f"[Migration] ❌ Error reading orders.json: {e}")
    else:
        print(f"[Migration] ⚠️ {orders_file} not found - skipping")
    
    # Commit all changes
    conn.commit()
    conn.close()
    
    # Print summary
    print("\n" + "=" * 50)
    print("[Migration] COMPLETE!")
    print("=" * 50)
    print(f"  Licenses: {migrated_count['licenses']}")
    print(f"  Devices:  {migrated_count['devices']}")
    print(f"  Orders:   {migrated_count['orders']}")
    print("=" * 50)
    print(f"\nDatabase file: {DATABASE_PATH.absolute()}")
    print("\n⚠️  Note: JSON files are preserved as backup.")
    print("   You can delete them after verifying the migration.")
    
    return migrated_count


def verify_migration():
    """Verify migration by counting records in database"""
    print("\n[Verification] Checking database...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    tables = ["licenses", "devices", "orders"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} records")
    
    conn.close()
    print("[Verification] Done.")


if __name__ == "__main__":
    migrate()
    verify_migration()
