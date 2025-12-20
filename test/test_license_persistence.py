"""
Test license persistence after app restart
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("Testing License Persistence After Restart")
print("=" * 60)

# Clean up any existing cache
if os.path.exists("license_cache.json"):
    os.remove("license_cache.json")
    print("Cleaned up existing cache\n")

# Test 1: Activate a license
print("[Test 1] Activating license...")
from feature_manager import get_feature_manager

fm = get_feature_manager()
print(f"Initial package: {fm.get_current_package()}")

# Try to activate (this requires server to be running)
result = fm.activate_license("VALID-TEST-PRO")
print(f"Activation result: {result}")

if result:
    print(f"Package after activation: {fm.get_current_package()}")
    
    # Check if cache file was created
    if os.path.exists("license_cache.json"):
        print("✓ license_cache.json created")
        import json
        with open("license_cache.json", "r") as f:
            cache_data = json.load(f)
            print(f"  Cache contains: {cache_data}")
    else:
        print("✗ license_cache.json NOT created")
    
    # Test 2: Simulate app restart
    print("\n[Test 2] Simulating app restart...")
    print("Creating new FeatureManager instance...")
    
    # Import FeatureManager class directly to create new instance
    from feature_manager import FeatureManager
    fm2 = FeatureManager()
    
    print(f"Package after restart: {fm2.get_current_package()}")
    print(f"License key: {fm2.license_key}")
    
    if fm2.get_current_package() == "pro":
        print("\n✓ SUCCESS: License persisted after restart!")
        print(f"  Package: {fm2.get_current_package()}")
    else:
        print(f"\n✗ FAILED: License not persisted")
        print(f"  Expected: pro")
        print(f"  Got: {fm2.get_current_package()}")
else:
    print("\n⚠ Could not test persistence - activation failed")
    print("  Make sure server is running: python run_server.py")

print("\n" + "=" * 60)
