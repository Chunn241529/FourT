"""
Test license activation with device tracking - v2
"""

import sys
sys.path.insert(0, 'c:/project/helper')

from feature_manager import get_feature_manager

print("=" * 60)
print("License Activation Test v2 - Device Tracking")
print("=" * 60)

# Get feature manager  
fm = get_feature_manager()

# Test with a new valid mock license
test_license = "VALID-TEST-PREMIUM-002"

print(f"\nTesting activation with license: {test_license}")
print("-" * 60)

# Activate license
success = fm.activate_license(test_license)

if success:
    print("\n✅ License activated successfully!")
    print(f"\nPackage: {fm.current_package}")
    print(f"\nLicense Data:")
    print(f"  license_key: {fm.license_data.get('license_key')}")
    print(f"  package: {fm.license_data.get('package')}")
    print(f"  device_id: {fm.license_data.get('device_id')}")
    print(f"  ipv4: {fm.license_data.get('ipv4')}")
    print(f"  user_id: {fm.license_data.get('user_id')}")
    print(f"  activated_at: {fm.license_data.get('activated_at')}")
    print(f"  expires_at: {fm.license_data.get('expires_at')}")
else:
    print("\n❌ License activation failed!")

print("\n" + "=" * 60)
