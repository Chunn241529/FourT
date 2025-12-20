"""
Test license cache in new AppData location
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feature_manager import get_feature_manager

print("=" * 60)
print("Testing License Cache in AppData Location")
print("=" * 60)

fm = get_feature_manager()

print(f"\nLicense cache file location:")
print(f"  {fm.license_cache_file}")

expected_path = os.path.join(os.getenv('LOCALAPPDATA'), 'FourT', '.lic.dat')
print(f"\nExpected path:")
print(f"  {expected_path}")

if fm.license_cache_file == expected_path:
    print("\n✓ Path is correct!")
else:
    print(f"\n✗ Path mismatch!")

# Check if directory exists
appdata_dir = os.path.dirname(fm.license_cache_file)
if os.path.exists(appdata_dir):
    print(f"\n✓ AppData directory exists: {appdata_dir}")
else:
    print(f"\n✗ AppData directory missing!")

# Check if any old cache exists in app directory
old_cache = "license_cache.json"
if os.path.exists(old_cache):
    print(f"\n⚠ Old cache file still exists: {old_cache}")
    print("  You may want to delete it manually")
else:
    print(f"\n✓ No old cache file in app directory")

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
