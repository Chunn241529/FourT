"""
Server Control Tab for Admin UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
from backend.admin.tabs.base_tab import BaseTab


class ServerTab(BaseTab):
    """Server Control tab - Start/Stop server and view output"""

    def setup(self):
        """Setup Server Control tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        public_url = os.getenv("PUBLIC_URL", "http://localhost:8000")

        # State
        self.server_running = False
        self.server_process = None

        # Status Section
        status_frame = tk.Frame(self.parent, bg=COLORS["card"], relief=tk.FLAT, bd=2)
        status_frame.pack(fill=tk.X, padx=20, pady=20)

        tk.Label(
            status_frame,
            text="Server Status",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 5))

        # Status indicator
        status_inner = tk.Frame(status_frame, bg=COLORS["card"])
        status_inner.pack(fill=tk.X, padx=15, pady=(5, 15))

        self.status_indicator = tk.Label(
            status_inner,
            text="●",
            font=("Segoe UI", 20),
            bg=COLORS["card"],
            fg=COLORS["error"],
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))

        self.status_label = tk.Label(
            status_inner,
            text="Server Stopped",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.status_label.pack(side=tk.LEFT)

        # Server info
        info_frame = tk.Frame(self.parent, bg=COLORS["card"])
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        tk.Label(
            info_frame,
            text="Server Configuration",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor=tk.W, padx=15, pady=(15, 10))

        # Host and Port
        config_inner = tk.Frame(info_frame, bg=COLORS["card"])
        config_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        tk.Label(
            config_inner,
            text="Host:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS.get("text_dim", COLORS["fg"]),
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        tk.Label(
            config_inner,
            text="0.0.0.0",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        ).grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        tk.Label(
            config_inner,
            text="Port:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS.get("text_dim", COLORS["fg"]),
        ).grid(row=1, column=0, sticky=tk.W, pady=5)

        tk.Label(
            config_inner,
            text="8000",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["success"],
        ).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        tk.Label(
            config_inner,
            text="Local URL:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS.get("text_dim", COLORS["fg"]),
        ).grid(row=2, column=0, sticky=tk.W, pady=5)

        self.local_url_label = tk.Label(
            config_inner,
            text=f"{public_url}",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["accent"],
        )
        self.local_url_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Control buttons
        button_frame = tk.Frame(self.parent, bg=COLORS["bg"])
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        self.start_button = ModernButton(
            button_frame,
            text="▶ Start Server",
            command=self._start_server,
            kind="success",
            font=FONTS["h2"],
            width=20,
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ModernButton(
            button_frame,
            text="⏹ Stop Server",
            command=self._stop_server,
            kind="danger",
            font=FONTS["h2"],
            width=20,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT)

        # Terminal section (integrated into server tab)
        terminal_header = tk.Frame(self.parent, bg=COLORS["card"])
        terminal_header.pack(fill=tk.X, padx=20, pady=(20, 0))

        tk.Label(
            terminal_header,
            text="Server Output",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT, padx=10, pady=10)

        clear_btn = ModernButton(
            terminal_header,
            text="Clear",
            command=self._clear_terminal,
            kind="secondary",
            width=10,
        )
        clear_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # Terminal output
        terminal_frame = tk.Frame(self.parent, bg=COLORS["input_bg"])
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.terminal_output = scrolledtext.ScrolledText(
            terminal_frame,
            font=FONTS["code"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            height=15,
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.terminal_output.config(state=tk.DISABLED)

    def _log_to_terminal(self, message):
        """Log message to terminal widget"""

        def append():
            try:
                # Check if widget still exists
                if not self.terminal_output.winfo_exists():
                    return
                self.terminal_output.config(state=tk.NORMAL)
                self.terminal_output.insert(tk.END, message)
                self.terminal_output.see(tk.END)
                self.terminal_output.config(state=tk.DISABLED)
            except tk.TclError:
                # Widget was destroyed, ignore
                pass

        # Schedule on main thread
        try:
            self.root.after(0, append)
        except tk.TclError:
            # Root was destroyed
            pass

    def _clear_terminal(self):
        """Clear terminal output"""
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.delete(1.0, tk.END)
        self.terminal_output.config(state=tk.DISABLED)

    def _update_server_status(self, running):
        """Update server status UI"""
        COLORS = self.COLORS
        if running:
            self.status_indicator.config(fg=COLORS["success"])
            self.status_label.config(text="Server Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.status_indicator.config(fg=COLORS["error"])
            self.status_label.config(text="Server Stopped")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _start_server(self):
        """Start the FastAPI server using ServerService"""
        if self.admin.server_service.is_running():
            return

        try:
            # Kill any existing server/ngrok processes first
            self._log_to_terminal("=== Checking for existing processes ===\n")
            killed_count = self._kill_existing_processes()

            if killed_count > 0:
                self._log_to_terminal(
                    f"Cleaned up {killed_count} existing process(es)\n\n"
                )
            else:
                self._log_to_terminal("No existing processes found\n\n")

            # Start server using service
            self.server_process = self.admin.server_service.start_server(
                self._log_to_terminal
            )
            self.server_running = self.admin.server_service.is_running()
            self._update_server_status(True)

            # Update admin window state
            self.admin.server_running = self.server_running
            self.admin.server_process = self.server_process

            # Start thread to read output
            threading.Thread(target=self._read_server_output, daemon=True).start()

            self._log_to_terminal("=== Starting FourT Helper Backend Server ===\n")

        except Exception as e:
            self._log_to_terminal(f"Error starting server: {e}\n")
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def _stop_server(self):
        """Stop the FastAPI server using ServerService"""
        if not self.admin.server_service.is_running():
            return

        try:
            self.admin.server_service.stop_server()
            self.server_running = False
            self.server_process = None
            self._update_server_status(False)

            # Update admin window state
            self.admin.server_running = False
            self.admin.server_process = None

            self._log_to_terminal("Server stopped\n")
        except Exception as e:
            self._log_to_terminal(f"Error stopping server: {e}\n")
            messagebox.showerror("Error", f"Failed to stop server: {e}")

    def _kill_existing_processes(self):
        """Kill existing server and ngrok processes using ServerService"""
        killed_processes = self.admin.server_service.kill_existing_processes(
            self._log_to_terminal
        )

        for msg in killed_processes:
            self._log_to_terminal(f"{msg}\n")

        return len(killed_processes)

    def _read_server_output(self):
        """Read server output and display in terminal"""
        try:
            while self.server_running and self.server_process:
                line = self.server_process.stdout.readline()
                if line:
                    self._log_to_terminal(line)
                elif self.server_process.poll() is not None:
                    # Process has terminated
                    self._log_to_terminal("\n=== Server process terminated ===\n")
                    break
        except Exception as e:
            self._log_to_terminal(f"Error reading server output: {e}\n")
