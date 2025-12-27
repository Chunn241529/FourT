"""
Build & Release Tab for Admin UI
"""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from backend.admin.tabs.base_tab import BaseTab


class BuildTab(BaseTab):
    """Build & Release tab - Nuitka and Installer builds"""

    def setup(self):
        """Setup Build & Release tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        # State
        self.build_running = False
        self.download_url = ""
        self.current_process = None

        # Header
        header = tk.Frame(self.parent, bg=COLORS["card"])
        header.pack(fill=tk.X, padx=20, pady=(20, 10))

        tk.Label(
            header,
            text="📦 Build & Release",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=15, pady=15)

        # Version Section
        version_frame = tk.Frame(self.parent, bg=COLORS["card"])
        version_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(
            version_frame,
            text="Version",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 5))

        version_inner = tk.Frame(version_frame, bg=COLORS["card"])
        version_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Current version display
        tk.Label(
            version_inner,
            text="Current:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS.get("fg_dim", COLORS["fg"]),
        ).pack(side=tk.LEFT)

        self.current_version_label = tk.Label(
            version_inner,
            text=self._get_current_version(),
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        )
        self.current_version_label.pack(side=tk.LEFT, padx=(10, 30))

        # New version input
        tk.Label(
            version_inner,
            text="New Version:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        self.new_version_entry = tk.Entry(
            version_inner,
            font=FONTS["code"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            width=15,
        )
        self.new_version_entry.pack(side=tk.LEFT, padx=10)
        self.new_version_entry.insert(0, self._get_next_version())

        # Clean build checkbox
        self.clean_build_var = tk.BooleanVar(value=False)
        self.clean_build_check = tk.Checkbutton(
            version_inner,
            text="🧹 Clean Build",
            variable=self.clean_build_var,
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["fg"],
            selectcolor=COLORS["input_bg"],
        )
        self.clean_build_check.pack(side=tk.LEFT, padx=(20, 0))

        # Download link section (hidden by default)
        self.download_frame = tk.Frame(self.parent, bg=COLORS["card"])

        dl_inner = tk.Frame(self.download_frame, bg=COLORS["card"])
        dl_inner.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(
            dl_inner,
            text="📥 Download:",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.download_url_label = tk.Label(
            dl_inner,
            text="",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["accent"],
            cursor="hand2",
        )
        self.download_url_label.pack(side=tk.LEFT)
        self.download_url_label.bind("<Button-1>", lambda e: self._copy_download_url())

        ModernButton(
            dl_inner,
            text="📋 Copy",
            command=self._copy_download_url,
            kind="secondary",
            width=8,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Build Buttons
        buttons_frame = tk.Frame(self.parent, bg=COLORS["bg"])
        buttons_frame.pack(fill=tk.X, padx=20, pady=15)

        # Build App Button (Nuitka)
        self.build_app_btn = ModernButton(
            buttons_frame,
            text="🔨 Build App (Nuitka)",
            command=self._build_nuitka,
            kind="primary",
            font=FONTS["h2"],
            width=22,
        )
        self.build_app_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Build Installer Button
        self.build_installer_btn = ModernButton(
            buttons_frame,
            text="📦 Build Installer",
            command=self._build_installer,
            kind="success",
            font=FONTS["h2"],
            width=18,
        )
        self.build_installer_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Open Dist Folder Button
        ModernButton(
            buttons_frame,
            text="📂",
            command=self._open_dist_folder,
            kind="secondary",
            width=5,
        ).pack(side=tk.LEFT, padx=(0, 15))

        # Stop Build Button (Icon only to save space)
        self.stop_build_btn = ModernButton(
            buttons_frame,
            text="🛑",
            command=self._stop_build,
            kind="danger",
            width=5,
        )
        self.stop_build_btn.pack(side=tk.LEFT)
        self.stop_build_btn.config(state=tk.DISABLED)

        # Progress Section
        progress_frame = tk.Frame(self.parent, bg=COLORS["card"])
        progress_frame.pack(fill=tk.X, padx=20, pady=10)

        progress_inner = tk.Frame(progress_frame, bg=COLORS["card"])
        progress_inner.pack(fill=tk.X, padx=15, pady=15)

        # Status label
        self.build_status_label = tk.Label(
            progress_inner,
            text="Ready to build",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.build_status_label.pack(anchor=tk.W)

        # Progress bar
        self.build_progress = ttk.Progressbar(
            progress_inner, mode="indeterminate", length=400
        )
        self.build_progress.pack(fill=tk.X, pady=(10, 0))

        # Build Output Log
        log_header = tk.Frame(self.parent, bg=COLORS["card"])
        log_header.pack(fill=tk.X, padx=20, pady=(10, 0))

        tk.Label(
            log_header,
            text="Build Output",
            font=FONTS["bold"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=10, pady=10)

        ModernButton(
            log_header,
            text="Clear",
            command=self._clear_build_log,
            kind="secondary",
            width=8,
        ).pack(side=tk.RIGHT, padx=10, pady=10)

        # Output text
        log_frame = tk.Frame(self.parent, bg=COLORS["input_bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.build_output = scrolledtext.ScrolledText(
            log_frame,
            font=FONTS["code"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            height=12,
        )
        self.build_output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.build_output.config(state=tk.DISABLED)

    def _get_current_version(self):
        """Get current version from version.ini"""
        try:
            version_file = self.client_dir / "version.ini"
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except:
            pass
        return "1.0.0"

    def _get_next_version(self):
        """Suggest next version (increment patch)"""
        current = self._get_current_version()
        try:
            parts = current.split(".")
            if len(parts) >= 3:
                parts[-1] = str(int(parts[-1]) + 1)
                return ".".join(parts)
        except:
            pass
        return current

    def _log_build(self, message, color=None):
        """Log message to build output"""

        def append():
            self.build_output.config(state=tk.NORMAL)
            self.build_output.insert(tk.END, message + "\n")
            self.build_output.see(tk.END)
            self.build_output.config(state=tk.DISABLED)

        self.root.after(0, append)

    def _clear_build_log(self):
        """Clear build output"""
        self.build_output.config(state=tk.NORMAL)
        self.build_output.delete(1.0, tk.END)
        self.build_output.config(state=tk.DISABLED)

    def _stop_build(self):
        """Kill the current build process"""
        if self.current_process and self.build_running:
            self._log_build("\n🛑 Stopping build process...", "red")
            try:
                # Force kill the process tree
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self._log_build(f"Could not kill process: {e}")

            self.build_running = False
            self.current_process = None
            self._update_build_status("Build stopped by user", False)
            self._log_build("🛑 Build terminated.\n")

    def _update_ui_state(self, is_running):
        """Update buttons state"""
        if is_running:
            self.build_app_btn.config(state=tk.DISABLED)
            self.build_installer_btn.config(state=tk.DISABLED)
            self.stop_build_btn.config(state=tk.NORMAL)
            self.build_progress.start(10)
        else:
            self.build_app_btn.config(state=tk.NORMAL)
            self.build_installer_btn.config(state=tk.NORMAL)
            self.stop_build_btn.config(state=tk.DISABLED)
            self.build_progress.stop()

    def _update_build_status(self, status, is_running=None):
        """Update build status label"""

        def update():
            self.build_status_label.config(text=status)
            if is_running is not None:
                self.build_running = is_running
                self._update_ui_state(is_running)

        self.root.after(0, update)

    def _build_nuitka(self):
        """Run Nuitka build"""
        if self.build_running:
            return

        new_version = self.new_version_entry.get().strip()
        if not new_version:
            messagebox.showwarning("Warning", "Please enter a version number")
            return

        self._clear_build_log()
        self._update_build_status(f"Building app v{new_version}...", True)
        self._log_build(f"=== Building FourT v{new_version} with Nuitka ===\n")

        def run_build():
            try:
                # Clean dist folder before building
                dist_path = self.client_dir / "dist"
                if dist_path.exists():
                    self._log_build(f"🗑️ Cleaning dist folder: {dist_path}")
                    try:
                        import shutil

                        shutil.rmtree(dist_path)
                        self._log_build("✅ dist folder deleted successfully\n")
                    except Exception as e:
                        self._log_build(
                            f"⚠️ Warning: Could not delete dist folder: {e}\n"
                        )

                script_path = self.client_dir / "build_nuitka.ps1"
                if not script_path.exists():
                    self._log_build(
                        f"ERROR: build_nuitka.ps1 not found at {script_path}"
                    )
                    self._update_build_status("Build failed!", False)
                    return

                # Run PowerShell script with UTF-8 encoding
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                # Build command with optional -Clean flag
                cmd = [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    "-NewVersion",
                    new_version,
                ]
                if self.clean_build_var.get():
                    cmd.append("-Clean")
                    self._log_build(
                        "🧹 Clean build mode enabled - deleting Nuitka cache\n"
                    )

                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.client_dir),
                    env=env,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )
                process = self.current_process

                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        try:
                            text = line.decode("utf-8", errors="replace").rstrip()
                        except:
                            text = line.decode("cp1252", errors="replace").rstrip()
                        self._log_build(text)

                process.wait()

                if process.returncode == 0:
                    self._log_build("\n✅ Build completed successfully!")

                    # Zip the dist folder and copy to releases
                    dist_path = self.client_dir / "dist"
                    if dist_path.exists():
                        try:
                            import zipfile
                            import shutil

                            # Create releases folder
                            releases_dir = self.client_dir / "releases" / new_version
                            releases_dir.mkdir(parents=True, exist_ok=True)

                            zip_filename = f"FourT_v{new_version}.zip"
                            zip_path = releases_dir / zip_filename

                            self._log_build(f"\n📦 Creating zip from dist folder...")

                            with zipfile.ZipFile(
                                zip_path, "w", zipfile.ZIP_DEFLATED
                            ) as zf:
                                for file in dist_path.rglob("*"):
                                    if file.is_file():
                                        # Skip build cache folders
                                        rel_path = file.relative_to(dist_path)
                                        if ".build" in str(
                                            rel_path
                                        ) or ".onefile" in str(rel_path):
                                            continue
                                        zf.write(file, rel_path)

                            # Get zip size
                            zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
                            self._log_build(
                                f"✅ Created: {zip_filename} ({zip_size_mb:.1f} MB)"
                            )
                            self._log_build(f"📁 Location: {releases_dir}")
                        except Exception as e:
                            self._log_build(f"⚠️ Failed to create zip: {e}")

                    self._update_build_status("Build completed!", False)
                    # Update current version display (but don't increment yet - wait for installer)
                    self.root.after(
                        0, lambda: self.current_version_label.config(text=new_version)
                    )
                else:
                    self._log_build(f"\n❌ Build failed with code {process.returncode}")
                    self._update_build_status("Build failed!", False)

            except Exception as e:
                self._log_build(f"\n❌ Error: {str(e)}")
                self._update_build_status("Build error!", False)

        threading.Thread(target=run_build, daemon=True).start()

    def _build_installer(self):
        """Run Inno Setup installer build"""
        if self.build_running:
            return

        self._clear_build_log()
        self._update_build_status("Building installer...", True)
        self._log_build("=== Building FourT Installer ===\n")

        def run_build():
            try:
                script_path = self.client_dir / "build_installer.ps1"
                if not script_path.exists():
                    self._log_build(
                        f"ERROR: build_installer.ps1 not found at {script_path}"
                    )
                    self._update_build_status("Build failed!", False)
                    return

                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"

                self.current_process = subprocess.Popen(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script_path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.client_dir),
                    env=env,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )
                process = self.current_process

                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        try:
                            text = line.decode("utf-8", errors="replace").rstrip()
                        except:
                            text = line.decode("cp1252", errors="replace").rstrip()
                        self._log_build(text)

                process.wait()

                if process.returncode == 0:
                    self._log_build("\n✅ Installer created successfully!")
                    self._log_build("📌 Installer is for auto-update only")
                    self._log_build(
                        "📦 Web download uses zip file (created in Nuitka build)"
                    )

                    self._update_build_status("Installer ready!", False)

                    public_url = os.getenv("PUBLIC_URL", "http://localhost:8000")
                    download_url = f"{public_url}/download/installer"
                    self.root.after(0, lambda: self._show_download_link(download_url))

                    # Increment version for next build after installer is complete
                    self.root.after(0, lambda: self.new_version_entry.delete(0, tk.END))
                    self.root.after(
                        0,
                        lambda: self.new_version_entry.insert(
                            0, self._get_next_version()
                        ),
                    )
                else:
                    self._log_build(f"\n❌ Build failed with code {process.returncode}")
                    self._update_build_status("Build failed!", False)

            except Exception as e:
                self._log_build(f"\n❌ Error: {str(e)}")
                self._update_build_status("Build error!", False)

        threading.Thread(target=run_build, daemon=True).start()

    def _show_download_link(self, download_url: str):
        """Show the download link in the UI"""
        self.download_url_label.config(text=download_url)
        self.download_url = download_url
        self.download_frame.pack(
            fill=tk.X, padx=20, pady=(0, 10), after=self.new_version_entry.master.master
        )
        self._log_build(f"\n📥 Download URL: {download_url}")

    def _copy_download_url(self):
        """Copy download URL to clipboard"""
        if self.download_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.download_url)
            self.root.update()
            messagebox.showinfo(
                "Copied", f"Download URL copied to clipboard!\n\n{self.download_url}"
            )

    def _open_dist_folder(self):
        """Open dist folder in file explorer"""
        dist_path = self.client_dir / "dist"
        if dist_path.exists():
            os.startfile(str(dist_path))
        else:
            messagebox.showinfo("Info", "dist folder doesn't exist yet. Build first!")
