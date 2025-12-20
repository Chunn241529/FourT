import requests
import time
import sys
import subprocess
import os

def test_backend():
    base_url = "http://localhost:8000"
    
    print("Waiting for server to start...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/")
            if response.status_code == 200:
                print("Server is up!")
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("Server failed to start")
        return False

    # Test 1: Verify License (Invalid)
    print("\nTest 1: Verify Invalid License")
    resp = requests.post(f"{base_url}/license/verify", json={"license_key": "INVALID"})
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    assert resp.json()["success"] == False

    # Test 2: Verify License (Demo)
    print("\nTest 2: Verify Demo License")
    resp = requests.post(f"{base_url}/license/verify", json={"license_key": "DEMO-LICENSE-KEY-12345"})
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    assert resp.json()["success"] == True
    assert resp.json()["package"] == "premium"

    # Test 3: Check Features (Pro)
    print("\nTest 3: Check Features (Pro)")
    resp = requests.get(f"{base_url}/features/check/pro")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Features count: {len(data['features'])}")
    assert data["package"] == "pro"
    assert "midi_playback" in data["features"]

    print("\nAll tests passed!")
    return True

if __name__ == "__main__":
    # Start server in background
    print("Starting server...")
    server_process = subprocess.Popen(
        [sys.executable, "run_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        if test_backend():
            print("\nBackend verification successful")
        else:
            print("\nBackend verification failed")
            sys.exit(1)
    finally:
        print("Stopping server...")
        server_process.terminate()
        server_process.wait()
