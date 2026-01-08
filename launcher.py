"""
FourT Suite - Application Launcher
"""

import sys
import os
import multiprocessing


def is_admin():
    """Check if application is running with admin privileges"""
    try:
        if os.name == "nt":
            import ctypes

            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.geteuid() == 0
    except:
        return False


def run_as_admin():
    """Restart application with admin privileges if not already admin"""
    try:
        # Already admin, no need to restart
        if is_admin():
            print("[Launcher] Already running as admin")
            return False

        print("[Launcher] Not admin, requesting elevation...")

        if os.name == "nt":
            import ctypes

            # Get path to current script/exe
            if getattr(sys, "frozen", False):
                # Running as compiled exe
                exe_path = sys.executable
                params = " ".join(sys.argv[1:])
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", exe_path, params, None, 1
                )
            else:
                # Running as Python script
                script = os.path.abspath(sys.argv[0])
                params = f'"{script}" ' + " ".join(sys.argv[1:])
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, params, None, 1
                )

            print(f"[Launcher] ShellExecute result: {result}")
            # If result > 32, it succeeded
            if result > 32:
                return True
            else:
                print(f"[Launcher] Failed to elevate, continuing without admin")
                return False
        else:
            # Linux/Unix elevation
            print("Requesting sudo privileges...")
            # Re-run with sudo
            args = ["sudo", sys.executable] + sys.argv
            if not getattr(sys, "frozen", False):
                args = ["sudo", sys.executable] + sys.argv
            else:
                args = ["sudo", sys.executable] + sys.argv[
                    1:
                ]  # if frozen, executable is the app

            # Simple execvp for script
            if not getattr(sys, "frozen", False):
                os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
            else:
                # Frozen
                os.execvp("sudo", ["sudo"] + [sys.executable] + sys.argv[1:])
            return True

    except Exception as e:
        print(f"[Launcher] Error requesting admin privileges: {e}")
        return False


def launch_main_app():
    """Launch the main application after splash completes"""
    try:
        from ui import MenuLauncher

        app = MenuLauncher()
        app.run()
    except Exception as e:
        import traceback

        traceback.print_exc()
        input("Press Enter to exit...")


def main():
    """Main entry point"""
    print(f"[Launcher] Starting... is_admin={is_admin()}")

    # Required for multiprocessing in frozen builds
    multiprocessing.freeze_support()

    # DEBUG: Skip admin check if DEBUG_NO_ADMIN env var is set
    skip_admin = os.environ.get("DEBUG_NO_ADMIN", "0") == "1"

    # Check and request admin privileges if needed
    if not skip_admin and run_as_admin():
        print("[Launcher] Exiting non-admin instance...")
        # Force exit - don't continue with splash
        os._exit(0)

    print("[Launcher] Continuing to splash screen...")

    # Show splash screen with optimization and update check
    from ui.splash_screen import SplashScreen

    splash = SplashScreen(on_complete=launch_main_app)
    splash.run()


if __name__ == "__main__":
    main()
