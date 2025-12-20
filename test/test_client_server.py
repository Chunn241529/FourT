"""
Test Client-Server Interaction
"""
import sys
import os
import time

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feature_manager import get_feature_manager
from core.config import Features, Packages, DEMO_LICENSE_KEY

def test_interaction():
    print("=" * 60)
    print("TEST CLIENT-SERVER INTERACTION")
    print("=" * 60)
    
    fm = get_feature_manager()
    
    # 1. Initial State
    print(f"\n1. Initial Package: {fm.get_current_package()}")
    
    # 2. Activate Demo License
    print(f"\n2. Activating Demo License ({DEMO_LICENSE_KEY})...")
    success = fm.activate_license(DEMO_LICENSE_KEY)
    
    if success:
        print("   ✓ Activation Successful!")
        print(f"   New Package: {fm.get_current_package()}")
    else:
        print("   ✗ Activation Failed!")
        return

    # 3. Verify License
    print("\n3. Verifying License with Server...")
    is_valid = fm.verify_license()
    if is_valid:
        print("   ✓ License is valid")
    else:
        print("   ✗ License is invalid")
        
    # 4. Check Features
    print("\n4. Checking Features...")
    if fm.has_feature(Features.EXPORT_AUDIO):
        print("   ✓ Has EXPORT_AUDIO feature")
    else:
        print("   ✗ Missing EXPORT_AUDIO feature")
        
    # 5. Deactivate
    print("\n5. Deactivating License...")
    success = fm.deactivate_license()
    if success:
        print("   ✓ Deactivation Successful")
        print(f"   Current Package: {fm.get_current_package()}")
    else:
        print("   ✗ Deactivation Failed")

if __name__ == "__main__":
    test_interaction()
