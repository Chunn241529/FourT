"""
Server Service for FourT Helper Admin
Handles server process control and management
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Callable


class ServerService:
    """Service for managing the FastAPI server process"""
    
    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir
        self.server_process: Optional[subprocess.Popen] = None
        self.running = False
        
    def kill_existing_processes(self, log_callback: Optional[Callable[[str], None]] = None) -> list:
        """
        Kill existing server and ngrok processes
        Returns list of killed process descriptions
        """
        import psutil
        
        killed_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = ' '.join(cmdline).lower()
                        
                        # Kill uvicorn/fastapi server processes
                        if 'run_server.py' in cmdline_str or ('uvicorn' in cmdline_str and 'backend.main:app' in cmdline_str):
                            proc.kill()
                            killed_processes.append(f"Killed server process: PID {proc.info['pid']}")
                        
                        # Kill ngrok processes
                        elif 'ngrok' in proc.info['name'].lower():
                            proc.kill()
                            killed_processes.append(f"Killed ngrok process: PID {proc.info['pid']}")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
        except Exception as e:
            if log_callback:
                log_callback(f"Warning: Error checking processes: {e}\n")
        
        if killed_processes:
            # Wait a moment for processes to fully terminate
            import time
            time.sleep(1)
        
        return killed_processes
    
    def start_server(self, log_callback: Optional[Callable[[str], None]] = None) -> Optional[subprocess.Popen]:
        """
        Start the FastAPI server
        Returns the subprocess.Popen object if successful
        """
        if self.running:
            return None
        
        try:
            # Get path to run_server.py
            run_server_path = self.backend_dir / "run_server.py"
            
            # Ensure logs are unbuffered
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            # Start server process
            if getattr(sys, 'frozen', False):
                # Running as exe - use --run-server flag
                cmd = [sys.executable, "--run-server"]
            else:
                # Running as script
                cmd = [sys.executable, "-u", str(run_server_path)]

            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                cwd=str(self.backend_dir),
                env=env
            )
            
            self.running = True
            return self.server_process
            
        except Exception as e:
            if log_callback:
                log_callback(f"Error starting server: {e}\n")
            raise
    
    def stop_server(self) -> bool:
        """Stop the FastAPI server"""
        if not self.running or not self.server_process:
            return False
        
        try:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.running = False
            self.server_process = None
            return True
        except Exception as e:
            raise RuntimeError(f"Error stopping server: {e}")
    
    def is_running(self) -> bool:
        """Check if server is running"""
        if self.server_process and self.server_process.poll() is None:
            return True
        return self.running
    
    def get_process(self) -> Optional[subprocess.Popen]:
        """Get the server process object"""
        return self.server_process
