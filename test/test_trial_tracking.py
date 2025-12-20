"""
Test script to verify trial tracking system
"""
import requests
import json

# Test 1: New device should get 30 minutes trial
print("=" * 60)
print("Test 1: New Device Registration")
print("=" * 60)

device_id = "test_device_12345"
response = requests.post(
    "http://127.0.0.1:8000/trial/check",
    json={"device_id": device_id, "ipv4": "192.168.1.100"}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

data = response.json()
assert data["trial_active"] == True, "Trial should be active for new device"
assert data["trial_remaining_seconds"] == 1800, f"Should have 1800 seconds (30 mins), got {data['trial_remaining_seconds']}"
print("✓ Test 1 PASSED: New device gets 30 minutes trial\n")

# Test 2: Same device should get same trial (not reset)
print("=" * 60)
print("Test 2: Same Device - Trial Not Reset")
print("=" * 60)

import time
time.sleep(2)  # Wait 2 seconds

response2 = requests.post(
    "http://127.0.0.1:8000/trial/check",
    json={"device_id": device_id, "ipv4": "192.168.1.100"}
)

print(f"Status Code: {response2.status_code}")
print(f"Response: {json.dumps(response2.json(), indent=2)}")

data2 = response2.json()
assert data2["trial_active"] == True, "Trial should still be active"
assert data2["trial_remaining_seconds"] < 1800, f"Time should have decreased, got {data2['trial_remaining_seconds']}"
assert data2["trial_remaining_seconds"] >= 1796, f"Should be around 1798s (2s elapsed), got {data2['trial_remaining_seconds']}"
print("✓ Test 2 PASSED: Trial continues, not reset\n")

# Test 3: Different device gets new trial
print("=" * 60)
print("Test 3: Different Device Gets New Trial")
print("=" * 60)

device_id_2 = "test_device_67890"
response3 = requests.post(
    "http://127.0.0.1:8000/trial/check",
    json={"device_id": device_id_2, "ipv4": "192.168.1.101"}
)

print(f"Status Code: {response3.status_code}")
print(f"Response: {json.dumps(response3.json(), indent=2)}")

data3 = response3.json()
assert data3["trial_active"] == True, "Trial should be active for new device"
assert data3["trial_remaining_seconds"] == 1800, f"Should have 1800 seconds, got {data3['trial_remaining_seconds']}"
print("✓ Test 3 PASSED: Different device gets separate trial\n")

print("=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
