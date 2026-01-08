"""
Version utility functions
"""

import os
import sys

# from core.config import VERSION_FILE
VERSION_FILE = "version.ini"


def get_app_directory():
    """Get the application directory (handles both .py and .exe)"""
    if getattr(sys, "frozen", False):
        # When running as .exe, PyInstaller extracts bundled files to sys._MEIPASS
        # This returns the directory where .exe is located (for file operations)
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(__file__))


def get_resource_path():
    """Get the path to bundled resources (handles PyInstaller's extraction folder)"""
    if getattr(sys, "frozen", False):
        # When frozen, bundled data files are in sys._MEIPASS (temp extraction folder)
        return sys._MEIPASS
    else:
        # When running as .py, resources are in the project root
        return os.path.dirname(os.path.dirname(__file__))


def get_current_version():
    """
    Get current version from version file

    Returns:
        str: Version string (e.g., "1.2.6")
    """
    try:
        # Use get_resource_path() to find bundled version.ini in PyInstaller's extraction folder
        resource_dir = get_resource_path()
        version_path = os.path.join(resource_dir, VERSION_FILE)

        print(f"[Version] Reading from: {version_path}")

        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                # Read first line only (ignore any extra lines)
                version = f.readline().strip()
                print(f"[Version] Current version: {version}")
                return version
        print(f"[Version] File not found, using default")
        return "1.2.6"  # Default version
    except Exception as e:
        print(f"Error reading version: {e}")
        return "1.2.6"


def compare_versions(v1, v2):
    """
    Compare two version strings (format: x.y.z)

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        int: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    try:
        v1_parts = [int(x) for x in v1.split(".")]
        v2_parts = [int(x) for x in v2.split(".")]

        for i in range(max(len(v1_parts), len(v2_parts))):
            part1 = v1_parts[i] if i < len(v1_parts) else 0
            part2 = v2_parts[i] if i < len(v2_parts) else 0

            if part1 < part2:
                return -1
            elif part1 > part2:
                return 1
        return 0
    except Exception as e:
        print(f"Error comparing versions: {e}")
        return 0


def is_frozen():
    """Check if running as compiled executable (PyInstaller or Nuitka)"""
    return getattr(sys, "frozen", False) or "__compiled__" in globals()
