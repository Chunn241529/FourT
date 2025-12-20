"""
Admin Launcher for FourT Helper
Launches the Admin UI with elevated privileges
"""

import sys
import os


def is_admin():
    """Check if application is running with admin privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Restart application with admin privileges"""
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
