"""
Debug script to check trial status
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feature_manager import get_feature_manager
from device_utils import get_device_id, get_local_ipv4
import requests

print("=" * 60)
print("Debug: Trial Status Check")
print("=" * 60)

device_id = get_device_id()
ipv4 = get_local_ipv4()

print(f"Device ID: {device_id}")
print(f"IPv4: {ipv4}")

# Direct API call
print("\n--- Direct API Call ---")
response = requests.post(
    "http://127.0.0.1:8000/trial/check",
    json={"device_id": device_id, "ipv4": ipv4}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Through feature manager
print("\n--- Through Feature Manager ---")
fm = get_feature_manager()
print(f"Trial Active: {fm.trial_active}")
print(f"Trial Remaining: {fm.trial_remaining_seconds}")
print(f"Is Trial Active: {fm.is_trial_active()}")
print(f"Current Package: {fm.get_current_package()}")
