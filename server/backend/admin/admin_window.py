"""
Admin UI for FourT Helper (Backend Version)
Modern UI with sidebar tabs, custom title bar, hidden scroll, and animations.
Runs in system tray.
"""

import tkinter as tk
from tkinter import ttk
import sys
import threading
import platform
from pathlib import Path

try:
    import pystray
    from PIL import Image

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from ui.theme import COLORS, FONTS, ModernButton
from ui.components.frameless_window import FramelessWindow
from ui.animations import hex_to_rgb, rgb_to_hex
from services.skills_service import SkillsService
from services.license_service import LicenseService
from services.server_service import ServerService

# Tab modules will be imported lazily in _get_tab_class()


class SidebarItem(tk.Frame):
    """Animated sidebar item with icon and text"""

    def __init__(self, parent, icon, text, command=None, **kwargs):
        super().__init__(parent, bg=COLORS["sidebar"], cursor="hand2", **kwargs)

        self.command = command
        self.is_active = False
        self._animation_id = None
        self._current_bg = COLORS["sidebar"]

        # Layout
        self.configure(height=44)
        self.pack_propagate(False)

        # Icon
        self.icon_label = tk.Label(
            self,
            text=icon,
            font=("Segoe UI Emoji", 14),
            bg=COLORS["sidebar"],
            fg=COLORS["fg_dim"],
            width=3,
        )
        self.icon_label.pack(side="left", padx=(12, 0))

        # Text
        self.text_label = tk.Label(
            self,
            text=text,
            font=FONTS["body"],
            bg=COLORS["sidebar"],
            fg=COLORS["fg_dim"],
            anchor="w",
        )
        self.text_label.pack(side="left", fill="x", expand=True, padx=(4, 10))

        # Active indicator (left bar)
        self.indicator = tk.Frame(self, bg=COLORS["sidebar"], width=3)
        self.indicator.place(x=0, y=4, height=36)

        # Bindings
        for widget in [self, self.icon_label, self.text_label]:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def set_active(self, active):
        """Set active state"""
        self.is_active = active
        if active:
            self._set_colors(COLORS["sidebar_active"], COLORS["fg"], COLORS["accent"])
        else:
            self._set_colors(COLORS["sidebar"], COLORS["fg_dim"], COLORS["sidebar"])

    def _set_colors(self, bg, fg, indicator_color):
        """Apply colors to all widgets"""
        self._current_bg = bg
        self.configure(bg=bg)
        self.icon_label.configure(
            bg=bg, fg=fg if not self.is_active else COLORS["accent"]
        )
        self.text_label.configure(bg=bg, fg=fg)
        self.indicator.configure(bg=indicator_color)

    def _animate_bg(self, target_bg, steps=4):
        """Animate background color transition"""
        if self._animation_id:
            self.after_cancel(self._animation_id)

        r1, g1, b1 = hex_to_rgb(self._current_bg)
        r2, g2, b2 = hex_to_rgb(target_bg)

        def step(current):
            if current >= steps:
                self._set_colors(
                    target_bg,
                    (
                        COLORS["fg"]
                        if self.is_active or target_bg != COLORS["sidebar"]
                        else COLORS["fg_dim"]
                    ),
                    COLORS["accent"] if self.is_active else COLORS["sidebar"],
                )
                return

            t = current / steps
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            color = rgb_to_hex(r, g, b)

            try:
                self._current_bg = color
                self.configure(bg=color)
                self.icon_label.configure(bg=color)
                self.text_label.configure(bg=color)
                self._animation_id = self.after(12, lambda: step(current + 1))
            except tk.TclError:
                pass

        step(0)

    def _on_enter(self, event):
        if not self.is_active:
            self._animate_bg(COLORS["sidebar_hover"])
            self.text_label.configure(fg=COLORS["fg"])

    def _on_leave(self, event):
        if not self.is_active:
            self._animate_bg(COLORS["sidebar"])
            self.text_label.configure(fg=COLORS["fg_dim"])

    def _on_click(self, event):
        if self.command:
            self.command()


class ScrollableFrame(tk.Frame):
    """Scrollable frame with hidden scrollbar"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)

        # Canvas for scrolling
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Inner frame
        self.inner = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.inner_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )

        # Bind events
        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.inner_id, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        # Check if content is taller than canvas
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")


class AdminWindow:
    """Main Admin UI Window - Modern Sidebar Version with System Tray"""

    def __init__(self):
        # Create hidden root
        self.hidden_root = tk.Tk()
        self.hidden_root.withdraw()
        # Prevent hidden root from showing in taskbar (Windows only)
        if platform.system() == "Windows":
            self.hidden_root.wm_attributes("-toolwindow", True)

        # Create frameless window
        self.root = FramelessWindow(
            self.hidden_root, title="admin FourT", icon_path="icon"
        )
        self.root.geometry("800x580")

        # Note: FramelessWindow already handles taskbar visibility via GWL_EXSTYLE
        # No need for -toolwindow here as it conflicts with FramelessWindow's approach

        # Expose root for tabs
        self.tk_root = self.root

        # Server process reference
        self.server_process = None
        self.server_running = False

        # Tray icon
        self.tray_icon = None
        self.tray_thread = None

        # Paths - handle both script and exe modes
        if getattr(sys, "frozen", False):
            self.backend_dir = Path(sys.executable).parent
        else:
            self.backend_dir = Path(__file__).parent.parent.parent

        self.data_dir = self.backend_dir / "data"

        # Client directory (for build operations)
        self.client_dir = self.backend_dir.parent / "client"

        self.licenses_file = self.data_dir / "licenses.json"
        self.devices_file = self.data_dir / "devices.json"
        self.orders_file = self.data_dir / "orders.json"

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

        # Initialize services - skills.json is in client/data
        self.skills_service = SkillsService(self.client_dir / "data" / "skills.json")
        self.license_service = LicenseService(self.licenses_file)
        self.server_service = ServerService(self.backend_dir)

        # Tab management
        self.current_tab = None
        self.tab_frames = {}
        self.tab_components = {}
        self.sidebar_items = {}

        self._setup_ui()
        self._setup_tray()

        # Override FramelessWindow close button behavior:
        # - Close button (X) → minimize to tray instead of closing
        # Need to rebind the close button since it was already bound during __init__
        # Find the close button (third button in controls_frame) and rebind it
        try:
            controls = self.root.controls_frame.winfo_children()
            if len(controls) >= 3:
                close_btn = controls[2]  # X button is the 3rd button
                close_btn.unbind("<Button-1>")
                close_btn.bind("<Button-1>", lambda e: self._minimize_to_tray())
        except Exception as e:
            print(f"[AdminWindow] Could not rebind close button: {e}")

    def _setup_ui(self):
        """Setup the main UI layout"""
        content = self.root.content_frame

        # Main container
        main_container = tk.Frame(content, bg=COLORS["bg"])
        main_container.pack(fill="both", expand=True)

        # === Sidebar ===
        self.sidebar = tk.Frame(main_container, bg=COLORS["sidebar"], width=160)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar header
        header = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        header.pack(fill="x", pady=(12, 8))

        tk.Label(
            header,
            text="Admin Panel",
            font=FONTS["h2"],
            bg=COLORS["sidebar"],
            fg=COLORS["fg"],
        ).pack(padx=15, anchor="w")

        # Separator
        tk.Frame(self.sidebar, bg=COLORS["border"], height=1).pack(
            fill="x", padx=10, pady=8
        )

        # Spacer frame to push Run Launcher button to bottom
        nav_area = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        nav_area.pack(fill="both", expand=True)

        # Tab definitions (using string names for lazy import)
        tabs = [
            ("server", "🖥️", "Server"),
            ("permissions", "👥", "Permissions"),
            ("packages", "📦", "Packages"),
            ("releases", "📥", "Releases"),
            ("skills", "🎮", "Skills"),
            ("midi_review", "🎵", "MIDI Review"),
            ("bug_reports", "🐞", "Bug Reports"),
            ("build", "🔨", "Build"),
        ]

        # Create sidebar items (inside nav_area)
        for tab_id, icon, text in tabs:
            item = SidebarItem(
                nav_area,
                icon=icon,
                text=text,
                command=lambda tid=tab_id: self._switch_tab(tid),
            )
            item.pack(fill="x", pady=1)
            self.sidebar_items[tab_id] = item

        # Bottom section of sidebar - Run Launcher button
        bottom_section = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        bottom_section.pack(fill="x", side="bottom", pady=10)

        tk.Frame(bottom_section, bg=COLORS["border"], height=1).pack(
            fill="x", padx=10, pady=(0, 10)
        )

        # Run Launcher button
        launch_btn = SidebarItem(
            bottom_section, icon="🚀", text="Run Launcher", command=self._run_launcher
        )
        launch_btn.pack(fill="x", pady=1)

        # === Content Area ===
        self.content_area = tk.Frame(main_container, bg=COLORS["bg"])
        self.content_area.pack(side="left", fill="both", expand=True)

        # Config for lazy loading
        self.tabs_with_own_scroll = {"packages", "skills"}

        # Show first tab (will lazy-load it)
        self._switch_tab("server")

    def _get_tab_class(self, tab_id):
        """Lazy import and return tab class"""
        if tab_id == "server":
            from backend.admin.tabs.server_tab import ServerTab

            return ServerTab
        elif tab_id == "permissions":
            from backend.admin.tabs.permissions_tab import PermissionsTab

            return PermissionsTab
        elif tab_id == "packages":
            from backend.admin.tabs.packages_tab import PackagesTab

            return PackagesTab
        elif tab_id == "skills":
            from backend.admin.tabs.skills_tab import SkillsTab

            return SkillsTab
        elif tab_id == "bug_reports":
            from backend.admin.tabs.bug_reports_tab import BugReportsTab

            return BugReportsTab
        elif tab_id == "build":
            from backend.admin.tabs.build_tab import BuildTab

            return BuildTab
        elif tab_id == "releases":
            from backend.admin.tabs.releases_tab import ReleasesTab

            return ReleasesTab
        elif tab_id == "midi_review":
            from backend.admin.tabs.midi_review_tab import MidiReviewTab

            return MidiReviewTab
        return None

    def _run_launcher(self):
        """Launch the main app (launcher.py) in a new process"""
        import subprocess
        import os

        try:
            if getattr(sys, "frozen", False):
                # Running as compiled exe - find launcher.exe in client directory
                launcher_path = self.client_dir / "dist" / "FourT" / "FourT.exe"
                if launcher_path.exists():
                    subprocess.Popen(
                        [str(launcher_path)], cwd=str(launcher_path.parent)
                    )
                    print(f"[Admin] Launched: {launcher_path}")
                else:
                    from tkinter import messagebox

                    messagebox.showerror(
                        "Error", f"Launcher not found: {launcher_path}"
                    )
            else:
                # Running as script - run launcher.py from client directory
                launcher_path = self.client_dir / "launcher.py"
                if launcher_path.exists():
                    # Find venv python in parent directory (root project)
                    root_dir = self.backend_dir.parent
                    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"

                    if venv_python.exists():
                        python_exe = str(venv_python)
                    else:
                        python_exe = sys.executable

                    # Set PYTHONPATH to client directory
                    env = os.environ.copy()
                    env["PYTHONPATH"] = str(self.client_dir)

                    subprocess.Popen(
                        [python_exe, str(launcher_path)],
                        cwd=str(self.client_dir),
                        env=env,
                    )
                    print(f"[Admin] Launched: {python_exe} {launcher_path}")
                else:
                    from tkinter import messagebox

                    messagebox.showerror(
                        "Error", f"Launcher not found: {launcher_path}"
                    )
        except Exception as e:
            from tkinter import messagebox

            messagebox.showerror("Error", f"Failed to launch: {e}")

    def _switch_tab(self, tab_id):
        """Switch to a different tab (lazy loading)"""
        if self.current_tab == tab_id:
            return

        # Hide current tab
        if self.current_tab and self.current_tab in self.tab_frames:
            self.tab_frames[self.current_tab].pack_forget()
            self.sidebar_items[self.current_tab].set_active(False)

        # Lazy-load tab if not created yet
        if tab_id not in self.tab_frames:
            tab_class = self._get_tab_class(tab_id)
            if tab_id in self.tabs_with_own_scroll:
                # Use regular frame for tabs with PanedWindow/own scroll
                tab_frame = tk.Frame(self.content_area, bg=COLORS["bg"])
                self.tab_frames[tab_id] = tab_frame
                self.tab_components[tab_id] = tab_class(tab_frame, self)
            else:
                # Use scrollable frame for simpler tabs
                scroll_frame = ScrollableFrame(self.content_area)
                self.tab_frames[tab_id] = scroll_frame
                self.tab_components[tab_id] = tab_class(scroll_frame.inner, self)

        self.current_tab = tab_id
        self.tab_frames[tab_id].pack(fill="both", expand=True)
        self.sidebar_items[tab_id].set_active(True)

    def run(self):
        """Run the admin UI"""
        # Handle window close - minimize to tray instead
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)

        self.hidden_root.mainloop()

    def _setup_tray(self):
        """Setup system tray icon"""
        if not TRAY_AVAILABLE:
            print("[Admin] pystray not available, tray icon disabled")
            return

        # Load icon
        icon_path = self.backend_dir / "favicon.ico"
        if not icon_path.exists():
            icon_path = self.backend_dir / "icon.ico"

        if icon_path.exists():
            try:
                image = Image.open(icon_path)
            except Exception:
                # Fallback - create simple icon
                image = Image.new("RGB", (64, 64), color="#7c3aed")
        else:
            image = Image.new("RGB", (64, 64), color="#7c3aed")

        # Create tray menu
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._show_window, default=True),
            pystray.MenuItem("Exit", self._exit_app),
        )

        # Create tray icon
        self.tray_icon = pystray.Icon("Admin FourT", image, "Admin FourT", menu)

        # Run tray icon in separate thread
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def _minimize_to_tray(self):
        """Minimize window to system tray"""
        # Hide window completely (both from screen and taskbar)
        self.root.withdraw()
        # Also hide from taskbar using toolwindow attribute (Windows only)
        try:
            self.root.attributes("-alpha", 0)  # Make invisible first
            if platform.system() == "Windows":
                self.root.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass

    def _show_window(self, icon=None, item=None):
        """Show window from tray"""
        self.root.after(0, self._do_show_window)

    def _do_show_window(self):
        """Actually show window (must be called from main thread)"""
        try:
            # Remove toolwindow attribute to show in taskbar again (Windows only)
            if platform.system() == "Windows":
                self.root.wm_attributes("-toolwindow", False)
            self.root.attributes("-alpha", 1)  # Make fully visible
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            # Window may have been destroyed
            pass

    def _exit_app(self, icon=None, item=None):
        """Exit application completely"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self._do_exit)

    def _do_exit(self):
        """Actually exit (must be called from main thread)"""
        if self.server_running:
            self._stop_server()
        self.root.destroy()
        self.hidden_root.destroy()

    def _stop_server(self):
        """Stop the server on exit"""
        if hasattr(self, "tab_components") and "server" in self.tab_components:
            self.tab_components["server"]._stop_server()


def main():
    """Main entry point"""
    app = AdminWindow()
    app.run()


if __name__ == "__main__":
    main()
