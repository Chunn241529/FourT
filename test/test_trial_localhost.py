"""
Test trial tracking with localhost backend (override ngrok)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override LICENSE_SERVER_URL before importing
os.environ["NGROK_DOMAIN"] = ""
os.environ["LICENSE_SERVER_URL"] = "http://127.0.0.1:8000"

from feature_manager import FeatureManager
from core.config import Features, LICENSE_ENDPOINTS
import time

print("=" * 60)
print("Testing Feature Manager with Server-Side Trial (Localhost)")
print("=" * 60)
print(f"Using server: {LICENSE_ENDPOINTS['trial_check']}\n")

# Get feature manager (should auto-check trial on init)
fm = FeatureManager()

print(f"Current Package: {fm.get_current_package()}")
print(f"Trial Active: {fm.is_trial_active()}")
print(f"Trial Remaining: {fm.get_trial_remaining_time()} seconds")

# Test feature access during trial
print("\n" + "=" * 60)
print("Testing Feature Access During Trial")
print("=" * 60)

features_to_test = [
    Features.MIDI_PLAYBACK,
    Features.MACRO,
    Features.WORLD_MAP,
    Features.SPEED_CONTROL,
]

for feature in features_to_test:
    has_access = fm.has_feature(feature)
    print(f"{feature}: {'✓ ALLOWED' if has_access else '✗ DENIED'}")

# Verify trial is active and features are accessible
assert fm.is_trial_active(), "Trial should be active for new device"
assert fm.has_feature(Features.MIDI_PLAYBACK), "Should have MIDI playback during trial"
assert fm.has_feature(Features.MACRO), "Should have Macro during trial"
assert fm.has_feature(Features.WORLD_MAP), "Should have World Map during trial"

print("\n✓ All features accessible during trial period!")

print("\n" + "=" * 60)
print("Testing Trial Persistence (Server-Side)")
print("=" * 60)
print("Note: Trial is now server-side tracked, no local files can reset it")

time.sleep(1)  # Wait 1 second

# Create new feature manager instance (simulating app restart)
fm2 = FeatureManager()

print(f"\nAfter creating new instance (simulating restart):")
print(f"Trial Active: {fm2.is_trial_active()}")
print(f"Trial Remaining: {fm2.get_trial_remaining_time()} seconds")

# Trial should still be active with similar time remaining
assert fm2.is_trial_active(), "Trial should STILL be active (not reset)"
remaining = fm2.get_trial_remaining_time()
assert remaining < 1800, f"Trial should not be reset to 30 mins, got {remaining}s"
# Allow for significant time elapsed during testing (up to 5 minutes)
assert remaining > 0, f"Trial should still be active, got {remaining}s"

print("\n✓ Trial persists across restarts - Server-side tracking working!")

print("\n" + "=" * 60)
print("ALL INTEGRATION TESTS PASSED! ✓")
print("=" * 60)
