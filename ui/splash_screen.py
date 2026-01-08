"""
FourT Splash Screen - Premium startup screen with smart progress system
"""

import tkinter as tk
import gc
import os
import sys
import ctypes
import threading
import tempfile
import shutil
import time
import math


class ProgressManager:
    """Smart progress management with weighted tasks and smooth animation"""

    # Task definitions with weights (weight = relative duration/importance)
    TASKS = {
        "connect": {"label": "Connecting...", "weight": 10},
        "url_refresh": {"label": "Updating server URL...", "weight": 5},
        "cache": {"label": "Clearing cache...", "weight": 5},
        "memory": {"label": "Optimizing memory...", "weight": 5},
        "license": {"label": "Verifying license...", "weight": 15},
        "skills": {"label": "Syncing skills...", "weight": 10},
        "modules": {"label": "Loading modules...", "weight": 20},
        "icons": {"label": "Loading skill icons...", "weight": 10},
        "templates": {"label": "Loading templates...", "weight": 8},
        "midi": {"label": "Syncing MIDI library...", "weight": 12},
        "update": {"label": "Checking updates...", "weight": 8},
        "download": {"label": "Downloading update...", "weight": 15},
        "ready": {"label": "Ready!", "weight": 2},
    }

    def __init__(self, task_ids: list):
        """Initialize with list of task IDs to run"""
        self.task_ids = task_ids
        self.total_weight = sum(
            self.TASKS[tid]["weight"] for tid in task_ids if tid in self.TASKS
        )
        self.completed_weight = 0
        self.current_task_idx = 0
        self._current_percent = 0.0

    def start_task(self, task_id: str) -> tuple:
        """Mark task as started, return (label, target_percent)"""
        if task_id not in self.TASKS:
            return ("Processing...", self._current_percent)

        task = self.TASKS[task_id]
        return (task["label"], self._current_percent)

    def complete_task(self, task_id: str) -> float:
        """Mark task as completed, return new target percent"""
        if task_id in self.TASKS:
            self.completed_weight += self.TASKS[task_id]["weight"]

        self._current_percent = (
            (self.completed_weight / self.total_weight * 100)
            if self.total_weight > 0
            else 100
        )
        return self._current_percent

    def get_task_progress(self, task_id: str, ratio: float) -> float:
        """Get progress percent for partial task completion (0.0 to 1.0)"""
        if task_id not in self.TASKS:
            return self._current_percent

        task_weight = self.TASKS[task_id]["weight"]
        partial_weight = task_weight * ratio
        total_done = self.completed_weight + partial_weight
        return (total_done / self.total_weight * 100) if self.total_weight > 0 else 0

    @property
    def current_percent(self):
        return self._current_percent


class SplashScreen:
    """Premium splash screen with system optimization and update checking"""

    # Animation constants
    ANIMATION_FPS = 60
    ANIMATION_INTERVAL = 16  # ~60fps
    SHIMMER_SPEED = 2  # pixels per frame

    def __init__(self, on_complete=None, on_update_available=None):
        """
        Initialize splash screen

        Args:
            on_complete: Callback when all tasks complete (no update)
            on_update_available: Callback(version, changelog, url, type) when update found
        """
        self.on_complete = on_complete
        self.on_update_available = on_update_available
        self.update_info = None
        self.feature_manager = None

        # Animation state
        self._current_display_percent = 0.0
        self._target_percent = 0.0
        self._animation_id = None
        self._shimmer_position = 0
        self._is_indeterminate = False
        self._shimmer_id = None
        self._pulse_dots = 0
        self._pulse_id = None

        # Progress manager (will be set before run)
        self.progress_mgr = None

        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()  # Hide initially

        # Window setup
        from utils.stealth_utils import stealth_manager

        self.root.title(stealth_manager.get_safe_window_title())
        self.root.overrideredirect(True)
        self.root.attributes("-transparentcolor", "#000001")
        self.root.attributes("-topmost", True)

        # Dimensions
        self.width = 500  # Increased from 450
        self.height = 300  # Increased from 280

        # Center on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = (screen_h - self.height) // 2

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(bg="#000001")

        self._create_ui()

        # Show window
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.update()

    def _create_ui(self):
        """Create the splash screen UI"""
        # Canvas for custom drawing
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg="#000001",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Draw rounded background
        self._draw_rounded_rect(
            10,
            10,
            self.width - 10,
            self.height - 10,
            radius=20,
            fill="#0d0d0d",
            outline="#1a1a2e",
            width=2,
        )

        # FourT Branding - Large stylish font
        self.canvas.create_text(
            self.width // 2,
            100,
            text="FourT",
            font=("Segoe UI", 48, "bold"),  # Reduced from 56
            fill="#ffffff",
        )

        # Subtle tagline
        self.canvas.create_text(
            self.width // 2,
            155,
            text="Helper Suite",
            font=("Segoe UI", 12),
            fill="#667eea",
        )

        # Progress bar area
        self.progress_y = 195
        self.progress_x1 = 30
        self.progress_x2 = self.width - 30
        self.progress_height = 4

        # Progress bar background (track)
        self._draw_rounded_rect(
            self.progress_x1,
            self.progress_y,
            self.progress_x2,
            self.progress_y + self.progress_height,
            radius=2,
            fill="#1a1a2e",
            outline="",
        )

        # Progress bar fill (will be updated)
        self.progress_bar_id = self._draw_rounded_rect(
            self.progress_x1,
            self.progress_y,
            self.progress_x1 + 1,
            self.progress_y + self.progress_height,
            radius=2,
            fill="#667eea",
            outline="",
        )

        # Shimmer overlay (for indeterminate mode)
        self.shimmer_id = None

        # Status area - below progress bar
        status_y = 220

        # Status label (left-aligned)
        self.status_id = self.canvas.create_text(
            30,
            status_y,
            text="Initializing...",
            font=("Segoe UI", 10),
            fill="#8888aa",
            anchor="w",
        )

        # Percentage (right-aligned)
        self.percent_id = self.canvas.create_text(
            self.width - 30,
            status_y,
            text="0%",
            font=("Segoe UI", 10, "bold"),
            fill="#667eea",
            anchor="e",
        )

        # Version info at bottom
        try:
            from utils import get_current_version

            version = get_current_version()
        except:
            version = "1.0.0"

        self.canvas.create_text(
            self.width // 2,
            self.height - 25,
            text=f"v{version}",
            font=("Segoe UI", 9),
            fill="#4a4a6a",
        )

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        """Draw a rounded rectangle on canvas"""
        points = [
            x1 + radius,
            y1,
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def _update_progress_bar(self, percent):
        """Update progress bar width based on percent"""
        bar_width = self.progress_x2 - self.progress_x1
        fill_width = max(1, int(bar_width * percent / 100))

        # Delete old bar and create new one
        if self.progress_bar_id:
            self.canvas.delete(self.progress_bar_id)

        self.progress_bar_id = self._draw_rounded_rect(
            self.progress_x1,
            self.progress_y,
            self.progress_x1 + fill_width,
            self.progress_y + self.progress_height,
            radius=2,
            fill="#667eea",
            outline="",
        )

        # Keep shimmer on top if active
        if self.shimmer_id:
            self.canvas.tag_raise(self.shimmer_id)

    def _animate_to_percent(self, target_percent):
        """Start smooth animation to target percent"""
        self._target_percent = min(100, max(0, target_percent))

        # Cancel existing animation
        if self._animation_id:
            try:
                self.root.after_cancel(self._animation_id)
            except:
                pass
            self._animation_id = None

        # Avoid recursion - use after() instead of direct call
        self.root.after(1, self._run_animation)

    def _run_animation(self):
        """Run one frame of progress animation"""
        # Guard against recursion
        if not hasattr(self, "_animating"):
            self._animating = False
        if self._animating:
            return
        self._animating = True

        try:
            if abs(self._current_display_percent - self._target_percent) < 0.5:
                # Close enough, snap to target
                self._current_display_percent = self._target_percent
                self._update_progress_bar(self._current_display_percent)
                self.canvas.itemconfig(
                    self.percent_id, text=f"{int(self._current_display_percent)}%"
                )
                self._animation_id = None
                return

            # Ease towards target (quick start, slow end)
            diff = self._target_percent - self._current_display_percent
            step = diff * 0.15  # Easing factor

            # Minimum step to ensure progress
            if abs(step) < 0.3:
                step = 0.3 if diff > 0 else -0.3

            self._current_display_percent += step

            # Update UI
            self._update_progress_bar(self._current_display_percent)
            self.canvas.itemconfig(
                self.percent_id, text=f"{int(self._current_display_percent)}%"
            )

            # Schedule next frame
            self._animation_id = self.root.after(
                self.ANIMATION_INTERVAL, self._run_animation
            )
        finally:
            self._animating = False

    def _start_indeterminate(self):
        """Start indeterminate shimmer animation"""
        if self._is_indeterminate:
            return

        self._is_indeterminate = True
        self._shimmer_position = 0  # Start at 0 (relative to progress bar start)
        self._run_shimmer()
        self._start_pulse_dots()

    def _stop_indeterminate(self):
        """Stop indeterminate animation"""
        self._is_indeterminate = False

        if self._shimmer_id:
            self.root.after_cancel(self._shimmer_id)
            self._shimmer_id = None

        if self._pulse_id:
            self.root.after_cancel(self._pulse_id)
            self._pulse_id = None

        # Remove shimmer overlay
        if self.shimmer_id:
            self.canvas.delete(self.shimmer_id)
            self.shimmer_id = None

    def _run_shimmer(self):
        """Run shimmer animation frame"""
        if not self._is_indeterminate:
            return

        # Remove old shimmer
        if self.shimmer_id:
            self.canvas.delete(self.shimmer_id)

        # Calculate shimmer position
        bar_width = self.progress_x2 - self.progress_x1
        shimmer_width = 60

        # Create gradient-like shimmer with multiple rectangles
        x = self.progress_x1 + self._shimmer_position

        # Only show within progress bar bounds
        if x < self.progress_x2 - 10:
            # Shimmer highlight
            alpha_colors = ["#7788ff", "#8899ff", "#99aaff", "#8899ff", "#7788ff"]
            highlight_width = shimmer_width // len(alpha_colors)

            for i, color in enumerate(alpha_colors):
                sx1 = x + (i * highlight_width)
                sx2 = min(sx1 + highlight_width, self.progress_x2)
                if sx1 < self.progress_x2:
                    self.shimmer_id = self.canvas.create_rectangle(
                        sx1,
                        self.progress_y,
                        sx2,
                        self.progress_y + self.progress_height,
                        fill=color,
                        outline="",
                    )

        # Move shimmer
        self._shimmer_position += self.SHIMMER_SPEED
        if self._shimmer_position > bar_width + shimmer_width:
            self._shimmer_position = -shimmer_width

        # Schedule next frame
        self._shimmer_id = self.root.after(self.ANIMATION_INTERVAL, self._run_shimmer)

    def _start_pulse_dots(self):
        """Start pulsing dots animation next to status"""
        self._pulse_dots = 0
        self._run_pulse_dots()

    def _run_pulse_dots(self):
        """Update pulsing dots"""
        if not self._is_indeterminate:
            return

        # Get current status text and add dots
        current_text = self.canvas.itemcget(self.status_id, "text")
        base_text = current_text.rstrip(".")

        dots = "." * (self._pulse_dots % 4)
        self.canvas.itemconfig(self.status_id, text=f"{base_text}{dots}")

        self._pulse_dots += 1
        self._pulse_id = self.root.after(400, self._run_pulse_dots)

    def update_status(self, text, percent):
        """Update status text and trigger animation to percent"""
        # Update status text (without dots if indeterminate will add them)
        self.canvas.itemconfig(self.status_id, text=text)

        # Animate to new percent
        self._animate_to_percent(percent)

        self.root.update()

    def run(self):
        """Run splash screen with all optimization tasks"""
        # Start tasks in background thread
        threading.Thread(target=self._run_tasks, daemon=True).start()

        # Run mainloop
        self.root.mainloop()

    def _run_tasks(self):
        """Run optimization tasks in sequence - UPDATE CHECK FIRST, then sync"""
        from services.connection_manager import get_connection_manager

        try:
            # Initial minimal task list - will expand after connection check
            initial_tasks = ["connect"]
            self.progress_mgr = ProgressManager(initial_tasks)

            # Task 1: Check Server Connection
            label, _ = self.progress_mgr.start_task("connect")
            self._update_ui(label, 0)

            # Start indeterminate mode for network operation
            self.root.after(0, self._start_indeterminate)

            conn_mgr = get_connection_manager()
            is_online = conn_mgr.check_connection()  # 2s timeout max

            # Stop indeterminate
            self.root.after(0, self._stop_indeterminate)

            if is_online:
                # Use FULL task list from the start (including download as contingency)
                # This prevents progress jumping when switching task lists
                full_task_list = [
                    "connect",
                    "url_refresh",
                    "update",
                    "download",
                    "cache",
                    "memory",
                    "license",
                    "skills",
                    "modules",
                    "icons",
                    "templates",
                    "midi",
                    "ready",
                ]
                self.progress_mgr = ProgressManager(full_task_list)

                # Mark connect as done
                percent = self.progress_mgr.complete_task("connect")
                self._update_ui("Server connected!", percent)

                # Refresh server URL first (needed for update check)
                label, _ = self.progress_mgr.start_task("url_refresh")
                self._update_ui(label, percent)

                from core.config import refresh_server_url

                try:
                    refresh_server_url()
                except Exception as e:
                    print(f"[Splash] URL refresh failed (non-critical): {e}")

                percent = self.progress_mgr.complete_task("url_refresh")
                self._update_ui("Server URL updated", percent)
                time.sleep(0.03)

                # Check for updates IMMEDIATELY (before sync)
                label, _ = self.progress_mgr.start_task("update")
                self._update_ui(label, percent)

                self.root.after(0, self._start_indeterminate)
                has_update = self._check_updates()
                self.root.after(0, self._stop_indeterminate)

                percent = self.progress_mgr.complete_task("update")

                if has_update:
                    # Update found! Skip remaining tasks and go straight to download
                    self._update_ui("Update available!", percent)
                    time.sleep(0.2)

                    # Handle update (includes download task)
                    self._handle_update()
                    return

                # No update - mark "download" as skipped (instant complete)
                percent = self.progress_mgr.complete_task("download")
                self._update_ui("No updates", percent)
                time.sleep(0.03)

            else:
                # Offline mode - simplified task list
                offline_tasks = [
                    "connect",
                    "cache",
                    "memory",
                    "license",
                    "modules",
                    "ready",
                ]
                self.progress_mgr = ProgressManager(offline_tasks)
                percent = self.progress_mgr.complete_task("connect")
                self._update_ui("Offline mode", percent)

            time.sleep(0.05)

            # Task: Clear Cache
            label, _ = self.progress_mgr.start_task("cache")
            self._update_ui(label, self.progress_mgr.current_percent)
            self._clear_cache()
            percent = self.progress_mgr.complete_task("cache")
            time.sleep(0.05)

            # Task: Optimize RAM
            label, _ = self.progress_mgr.start_task("memory")
            self._update_ui(label, percent)
            self._optimize_ram()
            self._clear_gpu_cache()
            percent = self.progress_mgr.complete_task("memory")
            time.sleep(0.05)

            # Task: Full Sync from Server (only if online)
            if is_online:
                self._run_sync()
            else:
                # Offline: just load from cache
                label, _ = self.progress_mgr.start_task("license")
                self._update_ui(label, percent)
                self._init_and_verify_license(is_online)
                percent = self.progress_mgr.complete_task("license")

                label, _ = self.progress_mgr.start_task("modules")
                self._update_ui(label, percent)
                self._preload_wwm_combo()
                percent = self.progress_mgr.complete_task("modules")

            time.sleep(0.05)

            # Final: Ready
            label, _ = self.progress_mgr.start_task("ready")
            percent = self.progress_mgr.complete_task("ready")
            self._update_ui("Ready!", 100)
            time.sleep(0.2)
            self._complete()

        except Exception as e:
            print(f"Splash error: {e}")
            import traceback

            traceback.print_exc()
            self._update_ui("Ready!", 100)
            self._complete()

    def _run_sync(self):
        """Run full sync from server during splash screen (silent, no dialogs)"""
        try:
            # Step 1: Sync License
            label, _ = self.progress_mgr.start_task("license")
            self._update_ui(label, self.progress_mgr.current_percent)

            self.root.after(0, self._start_indeterminate)
            self._init_and_verify_license(is_online=True)
            self.root.after(0, self._stop_indeterminate)

            percent = self.progress_mgr.complete_task("license")
            self._update_ui("License verified", percent)
            time.sleep(0.03)

            # Step 2: Sync Skills
            label, _ = self.progress_mgr.start_task("skills")
            self._update_ui(label, percent)

            self.root.after(0, self._start_indeterminate)
            self._sync_skills()
            self.root.after(0, self._stop_indeterminate)

            percent = self.progress_mgr.complete_task("skills")
            time.sleep(0.03)

            # Step 3: Preload WWM Combo
            label, _ = self.progress_mgr.start_task("modules")
            self._update_ui(label, percent)
            self._preload_wwm_combo_with_progress()
            percent = self.progress_mgr.complete_task("modules")
            time.sleep(0.03)

            # Step 4: Sync MIDI Library
            label, _ = self.progress_mgr.start_task("midi")
            self._update_ui(label, percent)

            self.root.after(0, self._start_indeterminate)
            self._sync_midi_library()
            self.root.after(0, self._stop_indeterminate)

            percent = self.progress_mgr.complete_task("midi")
            self._update_ui("Sync complete", percent)

        except Exception as e:
            print(f"[Splash] Sync error (non-critical): {e}")
            # Complete remaining tasks even on error
            for task_id in [
                "license",
                "skills",
                "modules",
                "icons",
                "templates",
                "midi",
            ]:
                self.progress_mgr.complete_task(task_id)

    def _sync_skills(self):
        """Sync skills.json from server"""
        try:
            from services.connection_manager import is_server_offline

            if is_server_offline():
                return

            from core.config import get_license_server_url
            import requests
            import os

            api_url = f"{get_license_server_url()}/skills/data"
            response = requests.get(api_url, timeout=8)

            if response.status_code == 200:
                import json

                data = response.json()

                # Determine data directory
                data_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "data"
                )
                skills_file = os.path.join(data_dir, "skills.json")

                os.makedirs(data_dir, exist_ok=True)
                with open(skills_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"[Splash] Skills synced: {len(data.get('skills', []))} skills")
        except Exception as e:
            print(f"[Splash] Skills sync error: {e}")

    def _sync_midi_library(self):
        """Sync MIDI files from server"""
        try:
            from services.connection_manager import is_server_offline

            if is_server_offline():
                return

            from core.config import get_license_server_url
            import requests
            import os

            # Get list from server
            api_url = f"{get_license_server_url()}/midi/list"
            response = requests.get(api_url, timeout=8)

            if response.status_code != 200:
                return

            server_files = response.json().get("files", [])
            if not server_files:
                return

            # Check local files
            midi_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "midi_files"
            )
            os.makedirs(midi_dir, exist_ok=True)
            local_files = (
                set(os.listdir(midi_dir)) if os.path.exists(midi_dir) else set()
            )

            # Download missing files
            base_url = get_license_server_url()
            downloaded = 0

            for file_info in server_files:
                filename = file_info.get("filename", "")
                if filename and filename not in local_files:
                    try:
                        url = file_info.get("url", f"/midi/{filename}")
                        if not url.startswith("http"):
                            url = f"{base_url}{url}"

                        file_response = requests.get(url, timeout=30)
                        if file_response.status_code == 200:
                            file_path = os.path.join(midi_dir, filename)
                            with open(file_path, "wb") as f:
                                f.write(file_response.content)
                            downloaded += 1
                    except Exception:
                        pass

            if downloaded > 0:
                print(f"[Splash] MIDI synced: {downloaded} new files")

        except Exception as e:
            print(f"[Splash] MIDI sync error: {e}")

    def _update_ui(self, status, percent):
        """Thread-safe UI update with debounce to prevent recursion"""
        # Debounce: only update if not already pending
        if not hasattr(self, "_update_pending"):
            self._update_pending = False
        if not hasattr(self, "_last_status"):
            self._last_status = ""
        if not hasattr(self, "_last_percent"):
            self._last_percent = 0

        # Skip if same status and similar percent
        if self._update_pending:
            # Store latest values for when pending update runs
            self._pending_status = status
            self._pending_percent = percent
            return

        self._update_pending = True
        self._pending_status = status
        self._pending_percent = percent

        def do_update():
            try:
                self.update_status(self._pending_status, self._pending_percent)
            except Exception as e:
                print(f"[Splash] UI update error: {e}")
            finally:
                self._update_pending = False

        self.root.after(16, do_update)  # Throttle to ~60fps max

    def _clear_cache(self):
        """Clear application cache and temp files"""
        try:
            # Clear temp directory for this app
            temp_app_dir = os.path.join(tempfile.gettempdir(), "FourT")
            if os.path.exists(temp_app_dir):
                try:
                    shutil.rmtree(temp_app_dir, ignore_errors=True)
                except:
                    pass

        except Exception as e:
            print(f"[Splash] Cache clear error: {e}")

    def _optimize_ram(self):
        """Optimize RAM usage"""
        try:
            # Python garbage collection
            gc.collect()
            gc.collect()  # Double collect for cyclic references

            # Windows-specific: trim working set
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(
                        ctypes.windll.kernel32.GetCurrentProcess(), -1, -1
                    )
                except:
                    pass

        except Exception as e:
            print(f"[Splash] RAM optimize error: {e}")

    def _clear_gpu_cache(self):
        """Clear GPU cache if available"""
        try:
            # Try to clear CUDA cache if torch is available
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    print("[Splash] Cleared CUDA cache")
            except ImportError:
                pass

        except Exception as e:
            print(f"[Splash] GPU cache clear error: {e}")

    def _init_and_verify_license(self, is_online: bool = False):
        """Initialize Feature Manager - skip network if offline"""
        try:
            from feature_manager import get_feature_manager

            # Pass online status to skip network calls if offline
            self.feature_manager = get_feature_manager(skip_network=not is_online)

            print(f"[Launcher] Package: {self.feature_manager.get_current_package()}")

            # Only check trial if online (to avoid timeout)
            if is_online and self.feature_manager.is_trial_active():
                remaining = self.feature_manager.get_trial_remaining_time()
                print(f"[Launcher] Trial remaining: {remaining}s")

            # Preload features config for menu_launcher (avoid API call on menu open)
            if is_online:
                self._preload_features_config()

        except Exception as e:
            print(f"[Splash] License error: {e}")

    def _preload_features_config(self):
        """Preload /features/config to cache packages data for menu_launcher"""
        try:
            from core.config import get_license_server_url
            import requests

            url = f"{get_license_server_url()}/features/config"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                packages = data.get("packages", {})
                menu_items = data.get("menu_items", {})

                # Store in feature_manager for menu_launcher to use
                if hasattr(self, "feature_manager") and self.feature_manager:
                    self.feature_manager._packages_cache = packages
                    self.feature_manager._menu_items_cache = menu_items

                    # Extract features from packages and set to FeatureManager
                    # This enables dynamic feature config from admin
                    features_by_package = {}
                    for pkg_id, pkg_data in packages.items():
                        features_by_package[pkg_id] = pkg_data.get("features", [])

                    self.feature_manager.set_server_package_features(
                        features_by_package
                    )
                    print(
                        f"[Splash] Preloaded {len(packages)} packages, {len(menu_items)} menu items"
                    )
        except Exception as e:
            print(f"[Splash] Features config preload error: {e}")

    def _preload_wwm_combo(self):
        """Preload WWM Combo module, skills and images (no progress reporting)"""
        try:
            print("[Launcher] Preloading WWM Combo module...")
            from ui.wwm_combo_window import WWMComboWindow
            from services.wwm_combo_service import SkillLoader, get_resources_dir
            from pathlib import Path

            # Preload skills data
            resources_dir = Path(get_resources_dir())
            loader = SkillLoader(resources_dir)
            loader.load_skills(force=True)
            print(f"[Launcher] Preloaded {len(loader.skills)} skills")

        except Exception as e:
            print(f"[Launcher] Preload failed (non-critical): {e}")

    def _preload_wwm_combo_with_progress(self):
        """Preload WWM Combo module, skills and images with progress updates"""
        try:
            print("[Launcher] Preloading WWM Combo module...")
            from ui.wwm_combo_window import WWMComboWindow
            from services.wwm_combo_service import SkillLoader, get_resources_dir
            from pathlib import Path

            # Preload skills data
            resources_dir = Path(get_resources_dir())
            loader = SkillLoader(resources_dir)
            loader.load_skills(force=True)
            print(f"[Launcher] Preloaded {len(loader.skills)} skills")

            # Update progress for icons
            percent = self.progress_mgr.complete_task("modules")
            label, _ = self.progress_mgr.start_task("icons")
            self._update_ui(label, percent)

            # Preload skill images into PIL cache (for instant WWM open)
            loaded_count = 0
            total_skills = len(loader.skills)

            for i, skill in enumerate(loader.skills):
                img_source = skill.get("image", "")
                if not img_source or skill["id"] in SkillLoader._pil_image_cache:
                    continue
                try:
                    pil_img = loader._load_from_file(img_source)
                    if pil_img:
                        # Resize and cache
                        try:
                            resample = pil_img.Resampling.LANCZOS
                        except AttributeError:
                            from PIL import Image

                            resample = Image.LANCZOS
                        pil_img = pil_img.resize((40, 40), resample)
                        SkillLoader._pil_image_cache[skill["id"]] = pil_img
                        loaded_count += 1
                except Exception:
                    pass

                # Update progress every 20 icons
                if i > 0 and i % 20 == 0:
                    ratio = i / total_skills
                    p = self.progress_mgr.get_task_progress("icons", ratio)
                    self._update_ui(f"Loading skill icons ({i}/{total_skills})...", p)

            print(f"[Launcher] Preloaded {loaded_count} skill icons")
            percent = self.progress_mgr.complete_task("icons")

            # Preload combo templates from server
            label, _ = self.progress_mgr.start_task("templates")
            self._update_ui(label, percent)

            self.root.after(0, self._start_indeterminate)
            try:
                from services.wwm_combo_service import TemplateManager

                template_mgr = TemplateManager(resources_dir)
                templates = template_mgr.fetch_server_templates(timeout=8)
                print(f"[Launcher] Preloaded {len(templates)} server templates")
            except Exception as e:
                print(f"[Launcher] Template preload skipped: {e}")
            self.root.after(0, self._stop_indeterminate)

            percent = self.progress_mgr.complete_task("templates")
            self._update_ui("Modules loaded", percent)

        except Exception as e:
            print(f"[Launcher] Preload failed (non-critical): {e}")

    def _check_updates(self):
        """Check for available updates - only called when online"""
        try:
            from utils import get_current_version
            from services.connection_manager import is_server_online
            import urllib.request
            import json

            # Quick check - skip if offline
            if not is_server_online():
                print("[Splash] Update check skipped - server offline")
                return False

            # Use dynamic server URL (not static UPDATE_SERVER_URL which may be stale)
            from core.config import get_license_server_url

            server_url = get_license_server_url()
            update_url = f"{server_url}/update/info"

            print(f"[Splash] Checking updates from: {update_url}")

            # Short timeout since we already know server is online
            req = urllib.request.Request(
                update_url, headers={"User-Agent": "FourT-Helper/1.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())

            server_version = data.get("version", "")
            current_version = get_current_version()

            print(f"[Splash] Current: v{current_version}, Server: v{server_version}")

            # DEBUG: Show version info in popup (remove after testing)
            # import tkinter.messagebox as msgbox
            # msgbox.showinfo("Update Check", f"Current: {current_version}\nServer: {server_version}\nURL: {update_url}")

            if self._compare_versions(server_version, current_version) > 0:
                installer_url = data.get("installer_url", "")
                if installer_url and not installer_url.startswith("http"):
                    from urllib.parse import urljoin

                    base_url = update_url.rsplit("/", 2)[0] + "/"
                    installer_url = urljoin(base_url, installer_url)

                self.update_info = {
                    "version": server_version,
                    "changelog": data.get("changelog", ""),
                    "download_url": installer_url,
                }
                print(f"[Splash] Update found: v{server_version}, URL: {installer_url}")
                return True
            else:
                print(f"[Splash] No update needed (current >= server)")
            return False

        except Exception as e:
            print(f"[Splash] Update check error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _compare_versions(self, v1, v2):
        """Compare version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]

            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except:
            return 0

    def _handle_update(self):
        """Handle update download and installation - auto download without popup"""
        if not self.update_info:
            self._complete()
            return

        # Start download immediately without asking
        label, _ = self.progress_mgr.start_task("download")
        self._update_ui(label, self.progress_mgr.current_percent)
        self._download_update()

    def _download_update(self):
        """Download and show update dialog using new UpdateService"""
        if not self.update_info:
            self._complete()
            return

        def download_thread():
            try:
                from services.update_service import UpdateService

                def on_status(msg, color=None):
                    self._update_ui(msg, self.progress_mgr.current_percent)

                def on_progress(current, total, percent):
                    # Use task progress for download
                    ratio = percent / 100
                    p = self.progress_mgr.get_task_progress("download", ratio)
                    self._update_ui(
                        f"Downloading... {current:.1f}MB / {total:.1f}MB", p
                    )

                # Create update service with callbacks
                update_service = UpdateService(
                    on_status_change=on_status, on_progress=on_progress
                )

                # Set update info
                update_service.installer_url = self.update_info["download_url"]
                update_service.new_version = self.update_info["version"]
                update_service.changelog = self.update_info.get("changelog", "")

                # Download synchronously
                success = update_service.download_update_sync()

                if success:
                    # Complete download task
                    percent = self.progress_mgr.complete_task("download")
                    self._update_ui("Download complete!", percent)

                    # Show update dialog on main thread
                    # Pass callback to continue app if user clicks "Later"
                    def show_dialog():
                        from ui.update_complete_dialog import show_update_complete

                        def on_install():
                            update_service.install_update(silent=True)

                        def on_later():
                            # User chose Later - continue to main app
                            print(
                                "[Splash] User chose to update later, continuing to app"
                            )
                            self._complete()

                        show_update_complete(
                            self.root,
                            update_service.installer_path,
                            update_service.new_version,
                            on_install=on_install,
                            on_later=on_later,
                        )

                    self.root.after(500, show_dialog)
                else:
                    self._update_ui("Download failed, continuing...", 99)
                    self.root.after(1000, self._complete)

            except Exception as e:
                print(f"[Splash] Download error: {e}")
                import traceback

                traceback.print_exc()
                self._update_ui("Update failed, starting app...", 99)
                self.root.after(1000, self._complete)

        threading.Thread(target=download_thread, daemon=True).start()

    def _complete(self):
        """Complete splash and call callback"""

        def finish():
            # Cancel any pending animations
            if self._animation_id:
                self.root.after_cancel(self._animation_id)
            if self._shimmer_id:
                self.root.after_cancel(self._shimmer_id)
            if self._pulse_id:
                self.root.after_cancel(self._pulse_id)

            try:
                self.root.destroy()
            except:
                pass

            if self.on_complete:
                self.on_complete()

        self.root.after(0, finish)


def show_splash(on_complete=None):
    """Show splash screen and run tasks"""
    splash = SplashScreen(on_complete=on_complete)
    splash.run()
