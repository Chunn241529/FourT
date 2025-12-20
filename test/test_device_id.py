"""
Test script to verify device ID and IPv4 detection
"""

import sys
sys.path.insert(0, 'c:/project/helper')

from device_utils import get_device_id, get_local_ipv4

print("=" * 50)
print("Device Identification Test")
print("=" * 50)

device_id = get_device_id()
ipv4 = get_local_ipv4()

print(f"\nDevice ID: {device_id}")
print(f"IPv4 Address: {ipv4}")
print("\n" + "=" * 50)
print("Test completed successfully!")
print("=" * 50)
