"""
Admin Launcher for FourT Helper
Launches the Admin UI with elevated privileges
"""

import sys
import os
import platform


def is_admin():
    """Check if application is running with admin privileges"""
    if platform.system() == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        # On Linux/macOS, check if running as root
        return os.geteuid() == 0


def run_as_admin():
    """Restart application with admin privileges"""
    if platform.system() == "Windows":
        try:
            import ctypes
            if not is_admin():
                # Get path to current script/exe
                script = os.path.abspath(sys.argv[0])
                params = " ".join([script] + sys.argv[1:])
                
                # Request UAC elevation
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, params, None, 1  # SW_SHOWNORMAL
                )
                return True
            return False
        except Exception as e:
            print(f"Error requesting admin privileges: {e}")
            return False
    else:
        # On Linux/macOS, no automatic elevation - just continue without admin
        # User can run with sudo if needed
        if not is_admin():
            print("Note: Running without admin privileges. Some features may be limited.")
            print("Run with 'sudo python3 admin.py' for full privileges.")
        return False


def main():
    """Main entry point"""
    # Check for server mode (used when running as frozen exe)
    if "--run-server" in sys.argv:
        try:
            import run_server
            run_server.run()
            return
        except Exception as e:
            print(f"Error running server: {e}")
            import traceback
            traceback.print_exc()
            return

    # Check and request admin privileges if needed
    if run_as_admin():
        sys.exit()  # Exit current instance, wait for new instance with admin
    
    # Launch Admin UI (using modular backend version)
    try:
        from backend.admin import AdminWindow
        app = AdminWindow()
        app.run()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
