"""
Quick test to verify version.ini is properly bundled and readable
"""
import sys
import os

# Add parent to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.version import get_current_version, get_resource_path, is_frozen

print("=" * 50)
print("Version Check Test")
print("=" * 50)
print(f"Running as .exe: {is_frozen()}")
print(f"Resource path: {get_resource_path()}")
print(f"Current version: {get_current_version()}")
print("=" * 50)

# Check if version.ini exists in resource path
version_file = os.path.join(get_resource_path(), "version.ini")
if os.path.exists(version_file):
    print(f"✓ version.ini found at: {version_file}")
    with open(version_file, 'r') as f:
        content = f.read().strip()
        print(f"  Content: '{content}'")
else:
    print(f"✗ version.ini NOT found at: {version_file}")

print("=" * 50)
input("Press Enter to exit...")
