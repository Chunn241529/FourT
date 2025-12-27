import json
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
LICENSES_FILE = os.path.join(DATA_DIR, "licenses.json")
DEVICES_FILE = os.path.join(DATA_DIR, "devices.json")

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_json(filepath, default=None):
    """Load JSON file safely"""
    if default is None:
        default = {}
    
    if not os.path.exists(filepath):
        return default
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return default

def save_json(filepath, data):
    """Save JSON file safely"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")

# Global state
orders = load_json(ORDERS_FILE)
active_licenses = load_json(LICENSES_FILE)
devices = load_json(DEVICES_FILE)

def save_orders():
    """Save orders to disk"""
    save_json(ORDERS_FILE, orders)

def save_licenses():
    """Save licenses to disk"""
    save_json(LICENSES_FILE, active_licenses)

def reload_licenses():
    """Reload licenses from disk (for dynamic updates from Admin UI)"""
    global active_licenses
    try:
        loaded = load_json(LICENSES_FILE)
        active_licenses.clear()
        active_licenses.update(loaded)
        logger.info(f"[DB] Reloaded {len(active_licenses)} licenses from disk")
    except Exception as e:
        logger.error(f"[DB] Error reloading licenses: {e}")
    return active_licenses

def save_devices():
    """Save devices to disk"""
    save_json(DEVICES_FILE, devices)

