import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Packages, PACKAGE_FEATURES, FEATURE_LIMITS, Features

def verify_packages():
    print("Verifying Package Configuration...")
    
    # 1. Verify Basic
    print("\n[Basic Package]")
    basic_features = PACKAGE_FEATURES[Packages.BASIC]
    print(f"Features: {basic_features}")
    assert Features.MIDI_PLAYBACK in basic_features
    assert Features.WORLD_MAP not in basic_features
    assert Features.MACRO not in basic_features
    
    basic_limits = FEATURE_LIMITS[Packages.BASIC]
    print(f"Limits: {basic_limits}")
    assert basic_limits["midi_file_limit"] == 5
    print("✅ Basic Package Verified")

    # 2. Verify Pro
    print("\n[Pro Package]")
    pro_features = PACKAGE_FEATURES[Packages.PRO]
    print(f"Features: {pro_features}")
    assert Features.WORLD_MAP in pro_features
    assert Features.MACRO in pro_features
    assert Features.SCRIPT_PREVIEW in pro_features
    
    pro_limits = FEATURE_LIMITS[Packages.PRO]
    print(f"Limits: {pro_limits}")
    assert pro_limits["macro_save_limit"] == 10
    assert pro_limits["macro_infinite_loop"] is False
    print("✅ Pro Package Verified")

    # 3. Verify Premium
    print("\n[Premium Package]")
    premium_features = PACKAGE_FEATURES[Packages.PREMIUM]
    print(f"Features: {premium_features}")
    assert Features.UNLIMITED_SPEED in premium_features
    assert Features.MACRO_UNLIMITED in premium_features
    
    premium_limits = FEATURE_LIMITS[Packages.PREMIUM]
    print(f"Limits: {premium_limits}")
    assert premium_limits["macro_save_limit"] == 999
    assert premium_limits["macro_infinite_loop"] is True
    print("✅ Premium Package Verified")

if __name__ == "__main__":
    try:
        verify_packages()
        print("\n🎉 All package configurations verified successfully!")
    except AssertionError as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
