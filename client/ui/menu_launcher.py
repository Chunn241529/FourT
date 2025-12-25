"""
FourT Suite - Menu Launcher
A compact floating icon that shows a modern custom menu on click
"""

import tkinter as tk
from tkinter import Canvas, messagebox
import math
import time
import os
from .theme import colors, FONTS
from .i18n import t
from feature_manager import get_feature_manager
from core.config import Features, PACKAGE_FEATURES, Packages

from .modern_menu import ModernMenu


def _get_icon_path():
    """Get path to favicon.ico"""
    # Try relative to this file first
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_dir, "favicon.ico")
    if os.path.exists(icon_path):
        return icon_path
    # Fallback to cwd
    if os.path.exists("favicon.ico"):
        return os.path.abspath("favicon.ico")
    return None


class MenuLauncher:
    """Compact floating icon with modern popup menu"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("")

        # Compact mode: 50x50 square
        self.compact_size = 56  # Slightly larger for better touch/click
        self.root.geometry(f"{self.compact_size}x{self.compact_size}")

        # Remove window decorations
        self.root.overrideredirect(True)

        # Make it always on top
        self.root.attributes("-topmost", True)

        # Set transparency key color
        self.root.configure(bg="black")
        self.root.attributes("-transparentcolor", "black")

        # Position at bottom-right corner
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_pos = screen_width - self.compact_size - 30
        y_pos = screen_height - self.compact_size - 80
        self.root.geometry(f"+{x_pos}+{y_pos}")

        # State
        self.dragging = False
        self.drag_x = 0
        self.drag_y = 0

        # Open windows tracking
        self.midi_window = None
        self.macro_window = None
        self.wwm_window = None
        self.quest_helper_window = None
        self.ping_optimizer_window = None
        self.screen_translator_window = None
        self.upgrade_window = None
        self.active_menu = None  # Track currently open menu
        self.last_menu_close_time = 0

        # Initialize Feature Manager (already initialized by splash screen)
        self.feature_manager = None
        self._get_feature_manager()

        self.setup_ui()

    def _get_feature_manager(self):
        """Get Feature Manager reference (already initialized by splash screen)"""
        from feature_manager import get_feature_manager

        self.feature_manager = get_feature_manager()

    def setup_ui(self):
        """Create the compact floating button"""
        # Main canvas for the button
        self.canvas = Canvas(
            self.root,
            width=self.compact_size,
            height=self.compact_size,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        # Draw circular button
        self.draw_button()

        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)

    def draw_button(self, hover=False, scale=1.0):
        """Draw the 4T button with modern styling and gradient effect"""
        self.canvas.delete("all")

        size = self.compact_size
        center = size / 2
        base_radius = (size / 2 - 4) * scale

        # Gradient colors for depth
        if hover:
            # Glowing hover state
            glow_colors = ["#ff6b6b", "#e94560", "#c73e54"]
            fill_color = "#2a2a3d"
            outline_color = colors["accent"]
            text_color = "white"
        else:
            # Normal state with subtle gradient
            glow_colors = None
            fill_color = "#1a1a2e"
            outline_color = "#3a3a5a"
            text_color = "#b8b8d0"

        # === Soft outer glow (when hovering) ===
        if hover and glow_colors:
            for i, glow in enumerate(glow_colors):
                offset = (len(glow_colors) - i) * 2
                self.canvas.create_oval(
                    center - base_radius - offset,
                    center - base_radius - offset,
                    center + base_radius + offset,
                    center + base_radius + offset,
                    fill="",
                    outline=glow,
                    width=2,
                    stipple="gray50" if i > 0 else "",
                )

        # === Drop shadow (subtle, offset) ===
        shadow_offset = 3
        self.canvas.create_oval(
            center - base_radius + shadow_offset,
            center - base_radius + shadow_offset,
            center + base_radius + shadow_offset,
            center + base_radius + shadow_offset,
            fill="#0a0a0a",
            outline="",
        )

        # === Outer ring (creates depth) ===
        self.canvas.create_oval(
            center - base_radius - 1,
            center - base_radius - 1,
            center + base_radius + 1,
            center + base_radius + 1,
            fill="#252540",
            outline="",
        )

        # === Main circular button ===
        self.canvas.create_oval(
            center - base_radius,
            center - base_radius,
            center + base_radius,
            center + base_radius,
            fill=fill_color,
            outline=outline_color,
            width=2,
            tags="button",
        )

        # === Inner highlight (top-left shine) ===
        highlight_radius = base_radius * 0.7
        highlight_offset = base_radius * 0.15
        self.canvas.create_arc(
            center - highlight_radius - highlight_offset,
            center - highlight_radius - highlight_offset,
            center + highlight_radius - highlight_offset,
            center + highlight_radius - highlight_offset,
            start=45,
            extent=90,
            fill="",
            outline="#ffffff" if hover else "#404060",
            width=1,
            style="arc",
        )

        # === 4T Text with shadow ===
        font_size = int(14 * scale)
        # Text shadow
        self.canvas.create_text(
            center + 1,
            center + 1,
            text="4T",
            font=("Segoe UI", font_size, "bold"),
            fill="#000000",
            tags="text_shadow",
        )
        # Main text
        self.canvas.create_text(
            center,
            center,
            text="4T",
            font=("Segoe UI", font_size, "bold"),
            fill=text_color,
            tags="text",
        )

        # === Accent dot (optional notification indicator) ===
        # Uncomment to show a notification dot
        # if self.has_notification:
        #     dot_radius = 5
        #     self.canvas.create_oval(
        #         size - 18, 6, size - 8, 16,
        #         fill='#00d9a0', outline='#1a1a2e', width=2
        #     )

    def on_enter(self, event):
        """Hover effect"""
        self.draw_button(hover=True)
        self.canvas.config(cursor="hand2")

    def on_leave(self, event):
        """Remove hover effect"""
        if not self.dragging:
            self.draw_button(hover=False)
            self.canvas.config(cursor="")

    def on_click(self, event):
        """Handle button click"""
        self.drag_x = event.x
        self.drag_y = event.y
        self.dragging = False

    def on_drag(self, event):
        """Handle dragging"""
        # Calculate distance moved
        distance = math.sqrt(
            (event.x - self.drag_x) ** 2 + (event.y - self.drag_y) ** 2
        )

        if distance > 5:  # Only consider it dragging if moved more than 5 pixels
            self.dragging = True
            x = self.root.winfo_x() + event.x - self.drag_x
            y = self.root.winfo_y() + event.y - self.drag_y
            self.root.geometry(f"+{x}+{y}")

    def on_release(self, event):
        """Handle button release"""
        if not self.dragging:
            # Toggle menu: if menu is open, close it; otherwise open it
            if self.active_menu and self.active_menu.winfo_exists():
                self.active_menu._close()
                self.active_menu = None
                return
            # Show menu
            self.show_menu(event)
        self.dragging = False

    def show_menu(self, event):
        """Show custom popup menu"""
        # Check features availability
        has_macro = (
            self.feature_manager.has_feature(Features.MACRO)
            if self.feature_manager
            else False
        )

        # Prepare menu items
        menu_items = []

        # Trial Status (use cached values - already loaded at splash screen)
        if (
            self.feature_manager.current_package == "free"
            and self.feature_manager.trial_active
        ):
            remaining = self.feature_manager.trial_remaining_seconds
            minutes = remaining // 60
            menu_items.append(
                {
                    "label": t("trial_remaining", minutes=minutes),
                    "command": None,
                    "icon": "⏱",
                    "fg": "#fab387",
                }
            )
            menu_items.append({"type": "separator"})

        # MIDI Auto Player
        if self.feature_manager.has_feature(Features.MIDI_PLAYBACK):
            menu_items.append(
                {
                    "label": t("auto_play_midi"),
                    "command": self.open_midi_player,
                    "icon": "🎹",
                    "fg": "#a6e3a1",
                }
            )
        else:
            menu_items.append(
                {
                    "label": t("auto_play_midi_expired"),
                    "command": self.show_midi_restriction,
                    "icon": "🔒",
                    "fg": "#6c7086",
                }
            )

        # Quest Video Helper (PLUS+)
        if self.feature_manager.has_feature(Features.QUEST_VIDEO_HELPER):
            menu_items.append(
                {
                    "label": t("quest_video_helper"),
                    "command": self.open_quest_video_helper,
                    "icon": "🎯",
                    "fg": "#89dceb",
                }
            )
        else:
            menu_items.append(
                {
                    "label": t("quest_video_helper_plus"),
                    "command": self.show_quest_helper_restriction,
                    "icon": "🔒",
                    "fg": "#6c7086",
                }
            )

        # Screen Translator (PLUS+)
        # if self.feature_manager.has_feature(Features.SCREEN_TRANSLATOR):
        #     menu_items.append(
        #         {
        #             "label": t("screen_translator"),
        #             "command": self.open_screen_translator,
        #             "icon": "🌐",
        #             "fg": "#94e2d5",
        #         }
        #     )
        # else:
        #     menu_items.append(
        #         {
        #             "label": t("screen_translator_plus"),
        #             "command": self.show_screen_translator_restriction,
        #             "icon": "🔒",
        #             "fg": "#6c7086",
        #         }
        #     )

        # # Ping Optimizer (Feature-gated)
        # if self.feature_manager.has_feature(Features.PING_OPTIMIZER):
        #     menu_items.append(
        #         {
        #             "label": t("ping_optimizer"),
        #             "command": self.open_ping_optimizer,
        #             "icon": "⚡",
        #             "fg": "#cba6f7",
        #         }
        #     )
        # else:
        #     menu_items.append(
        #         {
        #             "label": t("ping_optimizer_pro"),
        #             "command": self.show_ping_optimizer_restriction,
        #             "icon": "🔒",
        #             "fg": "#6c7086",
        #         }
        #     )

        # Macro Recorder
        if has_macro:
            menu_items.append(
                {
                    "label": t("macro_recorder"),
                    "command": self.open_macro_recorder,
                    "icon": "⏺",
                    "fg": "#a6e3a1",
                }
            )
        else:
            menu_items.append(
                {
                    "label": t("macro_recorder_pro"),
                    "command": self.show_macro_restriction,
                    "icon": "🔒",
                    "fg": "#6c7086",
                }
            )

        # WWM Combo (PRO feature - same as Macro)
        if has_macro:
            menu_items.append(
                {
                    "label": t("macro_combo"),
                    "command": self.open_wwm_combo,
                    "icon": "⚔",
                    "fg": "#c6a0f6",
                }
            )
        else:
            menu_items.append(
                {
                    "label": t("macro_combo_pro"),
                    "command": self.show_wwm_restriction,
                    "icon": "🔒",
                    "fg": "#6c7086",
                }
            )

        menu_items.append({"type": "separator"})

        # Upgrade
        menu_items.append(
            {
                "label": t("upgrade_premium"),
                "command": self.open_upgrade,
                "icon": "👑",
                "fg": "#f9e2af",
            }
        )

        # Sync Server (icon only style - short label)
        menu_items.append(
            {
                "label": t("sync_server"),
                "command": self.sync_server,
                "icon": "🔄",
                "fg": "#89b4fa",
            }
        )

        menu_items.append({"type": "separator"})

        # Exit
        menu_items.append(
            {
                "label": t("exit"),
                "command": self.confirm_exit,
                "icon": "❌",
                "fg": "#f38ba8",
            }
        )

        # Calculate position
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        menu_width = 220
        menu_height = len(menu_items) * 45  # Approximate

        # Determine horizontal position (Left or Right of the icon)
        if root_x > screen_width / 2:
            # Icon is on the right side, show menu to the left
            x = root_x - menu_width - 10
        else:
            # Icon is on the left side, show menu to the right
            x = root_x + self.compact_size + 10

        # Determine vertical position (Up or Down)
        # Default to showing below the icon, unless it's too close to the bottom
        if root_y + menu_height > screen_height - 20:
            # Too close to bottom, align bottom of menu with bottom of icon
            y = root_y + self.compact_size - menu_height
        else:
            # Show aligned with top of icon
            y = root_y

        # Ensure x is within screen bounds
        if x < 10:
            x = 10
        if x + menu_width > screen_width - 10:
            x = screen_width - menu_width - 10

        # Ensure y is within screen bounds
        if y < 10:
            y = 10
        if y + menu_height > screen_height - 10:
            y = screen_height - menu_height - 10

        # Create and show menu
        self.active_menu = ModernMenu(
            self.root,
            x,
            y,
            menu_items,
            on_close=self.on_menu_close,
            on_bug_report=self.open_bug_report,
        )

    def on_menu_close(self):
        """Callback when menu is closed"""
        self.active_menu = None
        self.last_menu_close_time = time.time()

    def open_bug_report(self):
        """Open bug report dialog"""
        from .bug_report_dialog import show_bug_report_dialog

        show_bug_report_dialog(self.root)

    def open_midi_player(self):
        """Open MIDI Auto Player window"""
        if self.midi_window and tk.Toplevel.winfo_exists(self.midi_window):
            self.midi_window.lift()
            self.midi_window.focus_force()
        else:
            from .components import FramelessWindow

            icon_path = _get_icon_path()
            self.midi_window = FramelessWindow(
                self.root, title="MIDI Auto Player", icon_path=icon_path
            )
            self.midi_window.geometry("420x480")
            # FramelessWindow sets bg

            # Icon handled by FramelessWindow

            from .theme import apply_theme

            apply_theme(self.midi_window)

            from .midi_player_frame import MidiPlayerFrame
            from core import KeyboardController, PlaybackEngine
            from services import UpdateService, LibraryService

            keyboard_controller = KeyboardController()
            playback_engine = PlaybackEngine(keyboard_controller)
            library_service = LibraryService()
            update_service = UpdateService()

            frame = MidiPlayerFrame(
                self.midi_window.content_frame,
                playback_engine,
                library_service,
                update_service,
            )
            frame.pack(fill="both", expand=True)

    def _get_min_package_for_feature(self, feature: str) -> str:
        """
        Find the minimum package that includes a feature (dynamic from server config)
        Returns package name or 'Premium' as fallback
        """
        # Try to get packages from server (cached in feature_manager)
        packages_data = self._get_server_packages()

        if packages_data:
            # Sort by order
            sorted_packages = sorted(
                packages_data.items(), key=lambda x: x[1].get("order", 99)
            )

            for pkg_id, pkg_data in sorted_packages:
                if pkg_id in ["free", "trial"]:
                    continue  # Skip free/trial
                features = pkg_data.get("features", [])
                if feature in features:
                    return pkg_data.get("name", pkg_id.capitalize())

        # Fallback to local hardcoded config
        package_order = [
            (Packages.FREE, "Free"),
            (Packages.BASIC, "Basic"),
            (Packages.PLUS, "Plus"),
            (Packages.PRO, "Pro"),
            (Packages.PREMIUM, "Premium"),
        ]

        for pkg_id, pkg_name in package_order:
            features = PACKAGE_FEATURES.get(pkg_id, [])
            if feature in features:
                return pkg_name

        return "Premium"  # Fallback

    def _get_server_packages(self):
        """Get packages from server (with caching from splash screen)"""
        # Check if we have cached data locally
        if hasattr(self, "_packages_cache") and self._packages_cache:
            return self._packages_cache

        # Check if feature_manager has cached data (from splash screen preload)
        if self.feature_manager and hasattr(self.feature_manager, "_packages_cache"):
            if self.feature_manager._packages_cache:
                self._packages_cache = self.feature_manager._packages_cache
                return self._packages_cache

        # Fallback: fetch from server (should rarely happen if splash preloaded)
        try:
            import requests
            from core.config import get_license_server_url

            url = f"{get_license_server_url()}/features/config"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                self._packages_cache = data.get("packages", {})
                return self._packages_cache
        except:
            pass

        return None

    def show_feature_restriction(
        self, feature: str, feature_name: str, description: str = ""
    ):
        """
        Show dynamic restriction message based on admin config

        Args:
            feature: Feature ID (from Features class)
            feature_name: Display name of the feature
            description: Optional description of what the feature does
        """
        min_package = self._get_min_package_for_feature(feature)

        msg = t("feature_of_package", feature_name=feature_name, package=min_package)
        if description:
            msg += f"\n\n{description}"
        msg += f"\n\n{t('want_to_upgrade')}"

        response = messagebox.askyesno(
            t("feature_title", feature_name=feature_name), msg, icon="info"
        )
        if response:
            self.open_upgrade()

    def show_macro_restriction(self):
        """Show message when free user tries to access macro"""
        self.show_feature_restriction(
            Features.MACRO,
            "Macro Recorder",
            t("macro_helps"),
        )

    def show_wwm_restriction(self):
        """Show message when free user tries to access WWM Combo"""
        self.show_feature_restriction(
            Features.WWM_COMBO,
            "WWM Combo Studio",
            t("wwm_helps"),
        )

    def show_midi_restriction(self):
        """Show message when free user tries to access midi player after trial"""
        self.show_feature_restriction(
            Features.MIDI_PLAYBACK, "Auto Music", t("trial_ended")
        )

    def show_quest_helper_restriction(self):
        """Show message when user tries to access Quest Video Helper without permission"""
        self.show_feature_restriction(
            Features.QUEST_VIDEO_HELPER,
            "Quest Video Helper",
            t("quest_helps"),
        )

    def show_ping_optimizer_restriction(self):
        """Show message when user tries to access Ping Optimizer without permission"""
        self.show_feature_restriction(
            Features.PING_OPTIMIZER,
            "Ping Optimizer",
            t("ping_helps"),
        )

    def show_screen_translator_restriction(self):
        """Show message when user tries to access Screen Translator without permission"""
        self.show_feature_restriction(
            Features.SCREEN_TRANSLATOR,
            "Dịch Màn Hình",
            t("screen_translator_helps"),
        )

    def open_macro_recorder(self):
        """Open Macro Recorder window"""
        if not self.feature_manager.has_feature(Features.MACRO):
            self.show_macro_restriction()
            return

        if self.macro_window and tk.Toplevel.winfo_exists(self.macro_window):
            self.macro_window.lift()
            self.macro_window.focus_force()
        else:
            from .components import FramelessWindow

            icon_path = _get_icon_path()
            self.macro_window = FramelessWindow(
                self.root, title="Macro Recorder", icon_path=icon_path
            )
            self.macro_window.geometry("800x650")
            # FramelessWindow sets bg

            # Icon handled by FramelessWindow

            from .theme import apply_theme

            apply_theme(self.macro_window)

            container = tk.Frame(self.macro_window.content_frame, bg=colors["bg"])
            container.pack(fill="both", expand=True, padx=15, pady=10)

            from .macro_window import MacroRecorderFrame

            frame = MacroRecorderFrame(container)
            frame.pack(fill="both", expand=True)

    def open_wwm_combo(self):
        """Open WWM Combo Generator"""
        if self.wwm_window and tk.Toplevel.winfo_exists(self.wwm_window):
            self.wwm_window.lift()
            self.wwm_window.focus_force()
        else:
            from .components import FramelessWindow

            icon_path = _get_icon_path()
            self.wwm_window = FramelessWindow(
                self.root, title="WWM Combo Studio", icon_path=icon_path
            )
            self.wwm_window.geometry("1250x700")
            # FramelessWindow sets bg

            # Icon handled by FramelessWindow

            from .theme import apply_theme

            apply_theme(self.wwm_window)

            from .wwm_combo.wwm_combo_frame import WWMComboFrame

            frame = WWMComboFrame(self.wwm_window.content_frame)
            frame.pack(fill="both", expand=True)

            # Set launcher root for countdown overlay (so it works even when WWM UI is closed)
            from services.wwm_combo_runtime import get_wwm_combo_runtime

            runtime = get_wwm_combo_runtime()
            runtime.tk_root = self.root

    def open_quest_video_helper(self):
        """Open Quest Video Helper window"""
        if self.quest_helper_window:
            try:
                if self.quest_helper_window.root and tk.Toplevel.winfo_exists(
                    self.quest_helper_window.root
                ):
                    self.quest_helper_window.show()
                    return
            except:
                pass

        from .quest_video_helper_window import QuestVideoHelperWindow

        self.quest_helper_window = QuestVideoHelperWindow(self.root)

    def open_ping_optimizer(self):
        """Open Ping Optimizer window"""
        if self.ping_optimizer_window and tk.Toplevel.winfo_exists(
            self.ping_optimizer_window
        ):
            self.ping_optimizer_window.lift()
            self.ping_optimizer_window.focus_force()
        else:
            from .components import FramelessWindow

            icon_path = _get_icon_path()
            self.ping_optimizer_window = FramelessWindow(
                self.root, title="Ping Optimizer", icon_path=icon_path
            )
            self.ping_optimizer_window.geometry("380x450")

            from .theme import apply_theme

            apply_theme(self.ping_optimizer_window)

            from .ping_optimizer_frame import PingOptimizerFrame

            frame = PingOptimizerFrame(self.ping_optimizer_window.content_frame)
            frame.pack(fill="both", expand=True)

    def open_screen_translator(self):
        """Open Screen Translator window"""
        # Check permission first
        if not self.feature_manager.has_feature(Features.SCREEN_TRANSLATOR):
            from tkinter import messagebox

            messagebox.showwarning(
                "Tính năng không khả dụng",
                "Dịch Màn Hình yêu cầu gói Plus trở lên.\nVui lòng nâng cấp gói để sử dụng tính năng này.",
            )
            return

        if self.screen_translator_window:
            try:
                if self.screen_translator_window.root and tk.Toplevel.winfo_exists(
                    self.screen_translator_window.root
                ):
                    self.screen_translator_window.show()
                    return
            except:
                pass

        from .screen_translator_window import ScreenTranslatorWindow

        self.screen_translator_window = ScreenTranslatorWindow(self.root)

    def sync_server(self):
        """Full sync: license, skills, templates, MIDI, version check with progress UI"""
        from ui.sync_progress_dialog import show_sync_progress
        from services.update_service import UpdateService
        from ui.update_complete_dialog import show_update_complete
        import threading

        def on_complete():
            """Sync completed, no update available"""
            print("[Sync] Completed, no update needed")

        def on_update_available(dialog, update_info):
            """Update found - download using same dialog"""
            print(f"[Sync] Update available: {update_info.get('version', '')}")

            # Create update service - use dialog for progress
            def on_status(status, color=None):
                dialog.update_progress(status, dialog._current_percent)

            def on_progress(current_mb, total_mb, percent):
                status = f"Downloading... {current_mb:.1f}MB / {total_mb:.1f}MB"
                # Map download progress to 100-200 range for visual effect
                dialog.update_progress(status, percent)

            update_service = UpdateService(
                on_status_change=on_status, on_progress=on_progress
            )

            update_service.installer_url = update_info.get("download_url", "")
            update_service.new_version = update_info.get("version", "")
            update_service.changelog = update_info.get("changelog", "")

            def download_and_show():
                # Reset progress for download phase
                dialog.update_progress("Downloading update...", 0)

                success = update_service.download_update_sync()

                if success:
                    dialog.show_success("Download complete!")

                    def show_install_dialog():
                        # Close sync dialog first
                        dialog._close()

                        def on_install():
                            update_service.install_update(silent=True)

                        def on_later():
                            print("[Update] User chose to update later")

                        show_update_complete(
                            self.root,
                            update_service.installer_path,
                            update_service.new_version,
                            on_install=on_install,
                            on_later=on_later,
                        )

                    self.root.after(800, show_install_dialog)
                else:
                    dialog.show_error("Download failed")
                    dialog.close_after(3000)

            threading.Thread(target=download_and_show, daemon=True).start()

        # Show sync progress dialog
        show_sync_progress(
            self.root,
            feature_manager=self.feature_manager,
            on_complete=on_complete,
            on_update_available=on_update_available,
        )

    def _restart_app(self):
        """Restart the application"""
        import sys
        import os

        try:
            # Get the executable path
            if getattr(sys, "frozen", False):
                # Running as compiled exe
                exe_path = sys.executable
            else:
                # Running as script
                exe_path = sys.executable
                script_path = os.path.abspath(sys.argv[0])

            # Close all windows
            try:
                if self.midi_window and tk.Toplevel.winfo_exists(self.midi_window):
                    self.midi_window.destroy()
                if self.macro_window and tk.Toplevel.winfo_exists(self.macro_window):
                    self.macro_window.destroy()
                if self.wwm_window and tk.Toplevel.winfo_exists(self.wwm_window):
                    self.wwm_window.destroy()
            except:
                pass

            # Start new instance
            if getattr(sys, "frozen", False):
                # Compiled exe - just run the exe
                os.startfile(exe_path)
            else:
                # Script mode - run python with script
                import subprocess

                subprocess.Popen([exe_path, script_path])

            # Exit current instance
            self.root.destroy()
            sys.exit(0)

        except Exception as e:
            print(f"[Restart] Error: {e}")
            import traceback

            traceback.print_exc()

    def _show_update_splash(self, update_info):
        """Show update dialog when new version available"""
        try:
            from services.update_service import UpdateService
            from ui.update_complete_dialog import show_update_complete
            import threading

            version = update_info.get("version", "")
            download_url = update_info.get("download_url", "")
            changelog = update_info.get("changelog", "")

            if not download_url or not version:
                print("[Update] No update URL or version")
                return

            def on_status(status, color=None):
                print(f"[Update] {status}")

            def on_progress(current_mb, total_mb, percent):
                print(
                    f"[Update] Downloading: {current_mb:.1f}MB / {total_mb:.1f}MB ({percent:.0f}%)"
                )

            # Create update service
            update_service = UpdateService(
                on_status_change=on_status, on_progress=on_progress
            )

            # Set update info
            update_service.installer_url = download_url
            update_service.new_version = version
            update_service.changelog = changelog

            def download_and_show():
                # Download in background
                success = update_service.download_update_sync()

                if success:
                    # Show dialog on main thread
                    def show_dialog():
                        def on_install():
                            update_service.install_update(silent=True)

                        def on_later():
                            print("[Update] User chose to update later")

                        show_update_complete(
                            self.root,
                            update_service.installer_path,
                            update_service.new_version,
                            on_install=on_install,
                            on_later=on_later,
                        )

                    self.root.after(0, show_dialog)
                else:
                    print("[Update] Download failed")

            # Start download in background thread
            threading.Thread(target=download_and_show, daemon=True).start()

        except Exception as e:
            print(f"[Update] Error showing update: {e}")
            import traceback

            traceback.print_exc()

    def confirm_exit(self):
        """Show exit confirmation dialog"""
        from .exit_confirm_dialog import show_exit_confirm

        def do_exit():
            """Actually exit the application"""
            # Stop combo runtime listeners
            try:
                from services.wwm_combo_runtime import get_wwm_combo_runtime

                runtime = get_wwm_combo_runtime()
                runtime.stop_listeners()
            except:
                pass

            try:
                self.root.destroy()
            except:
                pass
            import sys

            sys.exit(0)

        show_exit_confirm(self.root, on_confirm=do_exit)

    def open_upgrade(self):
        """Open upgrade window - bring to front if already open"""
        # Check if upgrade window is already open
        if self.upgrade_window:
            try:
                if hasattr(self.upgrade_window, "window") and tk.Toplevel.winfo_exists(
                    self.upgrade_window.window
                ):
                    self.upgrade_window.window.lift()
                    self.upgrade_window.window.focus_force()
                    return
            except:
                pass

        from .upgrade_window import UpgradeWindow

        self.upgrade_window = UpgradeWindow(self.root)

    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MenuLauncher()
    app.run()
