"""
Test license activation with device tracking
"""

import sys
sys.path.insert(0, 'c:/project/helper')

from feature_manager import get_feature_manager

print("=" * 60)
print("License Activation Test - Device Tracking")
print("=" * 60)

# Get feature manager
fm = get_feature_manager()

# Test with a valid mock license
test_license = "VALID-TEST-PRO-001"

print(f"\nTesting activation with license: {test_license}")
print("-" * 60)

# Activate license
success = fm.activate_license(test_license)

if success:
    print("\n✅ License activated successfully!")
    print(f"\nPackage: {fm.current_package}")
    print(f"\nLicense Data:")
    for key, value in fm.license_data.items():
        print(f"  {key}: {value}")
else:
    print("\n❌ License activation failed!")

print("\n" + "=" * 60)
print("Please check data/licenses.json to verify device tracking")
print("=" * 60)
