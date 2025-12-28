"""
Ping Optimizer Service
Provides network optimization utilities for reducing latency
"""

import subprocess
import socket
import time
import threading
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class PingQuality(Enum):
    """Ping quality levels"""

    EXCELLENT = "excellent"  # < 30ms
    GOOD = "good"  # 30-60ms
    FAIR = "fair"  # 60-100ms
    POOR = "poor"  # 100-150ms
    BAD = "bad"  # > 150ms


@dataclass
class PingResult:
    """Result of a ping measurement"""

    latency_ms: float
    quality: PingQuality
    target: str
    success: bool
    error: Optional[str] = None


@dataclass
class DNSServer:
    """DNS server configuration"""

    name: str
    primary: str
    secondary: str
    icon: str = "🌐"


# Pre-defined DNS servers
DNS_SERVERS: Dict[str, DNSServer] = {
    "cloudflare": DNSServer("Cloudflare", "1.1.1.1", "1.0.0.1", "☁️"),
    "google": DNSServer("Google", "8.8.8.8", "8.8.4.4", "🔍"),
    "quad9": DNSServer("Quad9", "9.9.9.9", "149.112.112.112", "🛡️"),
    "opendns": DNSServer("OpenDNS", "208.67.222.222", "208.67.220.220", "🌐"),
    "adguard": DNSServer("AdGuard", "94.140.14.14", "94.140.15.15", "🚫"),
}

# Ping targets for estimation
PING_TARGETS = [
    ("1.1.1.1", "Cloudflare"),
    ("8.8.8.8", "Google"),
    ("208.67.222.222", "OpenDNS"),
]


# Game server targets for direct ping
@dataclass
class GameServer:
    """Game server configuration"""

    name: str
    servers: List[str]  # List of hostnames/IPs
    icon: str = "🎮"


# Default game: Where Winds Meet (燕云十六声) by Everstone / NetEase
DEFAULT_GAME_SERVER = GameServer(
    name="Where Winds Meet",
    servers=[
        "wherewindsmeet.com",  # Official website
        "www.neteasegames.com",  # NetEase Games
        "gwstatic.neteasegames.com",  # NetEase static assets
        "1.1.1.1",  # Fallback
    ],
    icon="⚔️",
)


def get_ping_quality(latency_ms: float) -> PingQuality:
    """Get quality level based on latency"""
    if latency_ms < 30:
        return PingQuality.EXCELLENT
    elif latency_ms < 60:
        return PingQuality.GOOD
    elif latency_ms < 100:
        return PingQuality.FAIR
    elif latency_ms < 150:
        return PingQuality.POOR
    else:
        return PingQuality.BAD


def get_quality_color(quality: PingQuality) -> str:
    """Get color for ping quality"""
    colors = {
        PingQuality.EXCELLENT: "#00d9a0",  # Teal green
        PingQuality.GOOD: "#a6e3a1",  # Light green
        PingQuality.FAIR: "#f9e2af",  # Yellow
        PingQuality.POOR: "#fab387",  # Orange
        PingQuality.BAD: "#f38ba8",  # Red
    }
    return colors.get(quality, "#8888aa")


def get_quality_label(quality: PingQuality) -> str:
    """Get Vietnamese label for quality"""
    labels = {
        PingQuality.EXCELLENT: "Xuất sắc",
        PingQuality.GOOD: "Tốt",
        PingQuality.FAIR: "Trung bình",
        PingQuality.POOR: "Kém",
        PingQuality.BAD: "Rất kém",
    }
    return labels.get(quality, "Không xác định")


class PingOptimizer:
    """Main ping optimizer service"""

    def __init__(self):
        self._is_measuring = False
        self._last_result: Optional[PingResult] = None
        self._realtime_stop = False

        # State tracking for dashboard
        self._ping_before: Optional[float] = None
        self._ping_after: Optional[float] = None
        self._optimization_status = {
            "dns": {"active": False, "name": None, "latency": None},
            "tcp": {"active": False},
            "dns_cache": {"active": False},
        }

    def get_optimization_status(self) -> dict:
        """Get current optimization status for dashboard"""
        return {
            "ping_before": self._ping_before,
            "ping_after": self._ping_after,
            "optimizations": self._optimization_status.copy(),
        }

    def get_improvement_percent(self) -> Optional[float]:
        """Calculate improvement percentage"""
        if self._ping_before and self._ping_after and self._ping_before > 0:
            improvement = (
                (self._ping_before - self._ping_after) / self._ping_before * 100
            )
            return round(improvement, 1)
        return None

    def estimate_ping(
        self,
        target: str = None,
        on_complete: Optional[Callable[[PingResult], None]] = None,
    ) -> Optional[PingResult]:
        """
        Estimate ping to target server

        Args:
            target: IP or hostname to ping (default: auto-select best target)
            on_complete: Callback with result (for async mode)

        Returns:
            PingResult if sync, None if async (result via callback)
        """
        if on_complete:
            # Async mode
            threading.Thread(
                target=self._measure_ping_async, args=(target, on_complete), daemon=True
            ).start()
            return None
        else:
            # Sync mode
            return self._measure_ping(target)

    def _measure_ping_async(self, target: str, callback: Callable):
        """Async ping measurement"""
        result = self._measure_ping(target)
        callback(result)

    def _measure_ping(self, target: str = None) -> PingResult:
        """Perform actual ping measurement"""
        self._is_measuring = True

        # Use first target if not specified
        if not target:
            target = PING_TARGETS[0][0]

        try:
            # Use socket-based ping (doesn't require admin)
            latency = self._socket_ping(target)

            if latency is not None:
                quality = get_ping_quality(latency)
                result = PingResult(
                    latency_ms=latency, quality=quality, target=target, success=True
                )
            else:
                # Fallback to ICMP ping
                latency = self._icmp_ping(target)
                if latency is not None:
                    quality = get_ping_quality(latency)
                    result = PingResult(
                        latency_ms=latency, quality=quality, target=target, success=True
                    )
                else:
                    result = PingResult(
                        latency_ms=999,
                        quality=PingQuality.BAD,
                        target=target,
                        success=False,
                        error="Không thể đo ping",
                    )
        except Exception as e:
            result = PingResult(
                latency_ms=999,
                quality=PingQuality.BAD,
                target=target,
                success=False,
                error=str(e),
            )

        self._is_measuring = False
        self._last_result = result
        return result

    def _socket_ping(
        self, target: str, port: int = 443, timeout: float = 2.0
    ) -> Optional[float]:
        """
        TCP-based latency measurement (no admin required)
        Measures time to establish TCP connection
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            start = time.perf_counter()
            sock.connect((target, port))
            end = time.perf_counter()

            sock.close()

            latency_ms = (end - start) * 1000
            return round(latency_ms, 1)
        except:
            return None

    def _icmp_ping(self, target: str) -> Optional[float]:
        """ICMP ping using Windows ping command"""
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "1000", target],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            output = result.stdout

            # Parse "time=XXms" or "time<1ms"
            import re

            match = re.search(r"time[=<](\d+)ms", output, re.IGNORECASE)
            if match:
                return float(match.group(1))

            return None
        except:
            return None

    def benchmark_dns(
        self,
        on_progress: Optional[Callable[[str, float], None]] = None,
        on_complete: Optional[Callable[[List[tuple]], None]] = None,
    ):
        """
        Benchmark all DNS servers and find the fastest

        Args:
            on_progress: Callback(dns_name, latency_ms) for each test
            on_complete: Callback([(name, latency_ms), ...]) sorted by speed
        """

        def run_benchmark():
            results = []

            for key, dns in DNS_SERVERS.items():
                latency = self._socket_ping(dns.primary, port=53, timeout=2.0)
                if latency is None:
                    latency = 999

                results.append((dns.name, latency, key))

                if on_progress:
                    on_progress(dns.name, latency)

            # Sort by latency
            results.sort(key=lambda x: x[1])

            if on_complete:
                on_complete(results)

        threading.Thread(target=run_benchmark, daemon=True).start()

    @staticmethod
    def flush_network(on_complete: Optional[Callable[[bool, str], None]] = None):
        """
        Flush DNS cache and reset network state
        Requires admin for some operations

        Args:
            on_complete: Callback(success, message)
        """
        import os

        def run_flush():
            results = []
            success = True

            # Get system32 path for absolute command paths
            system32 = os.path.join(
                os.environ.get("SystemRoot", r"C:\Windows"), "System32"
            )
            ipconfig = os.path.join(system32, "ipconfig.exe")
            netsh = os.path.join(system32, "netsh.exe")

            commands = [
                ([ipconfig, "/flushdns"], "Flush DNS cache"),
                ([netsh, "winsock", "reset", "catalog"], "Reset Winsock"),
                ([netsh, "int", "ip", "reset"], "Reset IP stack"),
            ]

            for cmd, desc in commands:
                try:
                    # Use list form instead of shell=True for better compatibility
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=15,
                        creationflags=(
                            subprocess.CREATE_NO_WINDOW
                            if hasattr(subprocess, "CREATE_NO_WINDOW")
                            else 0
                        ),
                    )
                    if result.returncode == 0:
                        results.append(f"✅ {desc}")
                    else:
                        # Check stderr for access denied
                        stderr = result.stderr.lower() if result.stderr else ""
                        if (
                            "access" in stderr
                            or "denied" in stderr
                            or "administrator" in stderr
                        ):
                            results.append(f"⚠️ {desc} (cần Admin)")
                        else:
                            results.append(f"⚠️ {desc} (cần Admin)")
                        success = False
                except FileNotFoundError:
                    results.append(f"❌ {desc}: Command not found")
                    success = False
                except Exception as e:
                    results.append(f"❌ {desc}: {e}")
                    success = False

            message = "\n".join(results)

            if on_complete:
                on_complete(success, message)

        threading.Thread(target=run_flush, daemon=True).start()

    @staticmethod
    def optimize_tcp(on_complete: Optional[Callable[[bool, str], None]] = None):
        """
        Apply TCP optimizations via registry
        REQUIRES ADMIN PRIVILEGES

        Optimizations:
        - Disable Nagle algorithm (TcpNoDelay)
        - Optimize ACK frequency
        - Disable network throttling

        Args:
            on_complete: Callback(success, message)
        """

        def run_optimize():
            import winreg

            optimizations = [
                # Disable Nagle algorithm
                (
                    r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
                    "TcpNoDelay",
                    1,
                    "Disable Nagle",
                ),
                (
                    r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
                    "TcpAckFrequency",
                    1,
                    "Optimize ACK",
                ),
                # Disable network throttling
                (
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                    "NetworkThrottlingIndex",
                    0xFFFFFFFF,
                    "Disable Throttling",
                ),
                (
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                    "SystemResponsiveness",
                    0,
                    "Max Priority",
                ),
            ]

            results = []
            success = True

            for reg_path, value_name, value_data, desc in optimizations:
                try:
                    # Try to open/create key
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        reg_path,
                        0,
                        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
                    )
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value_data)
                    winreg.CloseKey(key)
                    results.append(f"✅ {desc}")
                except PermissionError:
                    results.append(f"⚠️ {desc} (cần Admin)")
                    success = False
                except Exception as e:
                    results.append(f"❌ {desc}: {e}")
                    success = False

            message = "\n".join(results)
            if success:
                message += "\n\n🔄 Khởi động lại máy để áp dụng đầy đủ."

            if on_complete:
                on_complete(success, message)

        threading.Thread(target=run_optimize, daemon=True).start()

    @staticmethod
    def set_dns(
        dns_key: str, on_complete: Optional[Callable[[bool, str], None]] = None
    ):
        """
        Set DNS server for all network adapters
        REQUIRES ADMIN PRIVILEGES

        Args:
            dns_key: Key from DNS_SERVERS dict
            on_complete: Callback(success, message)
        """

        def run_set_dns():
            if dns_key not in DNS_SERVERS:
                if on_complete:
                    on_complete(False, f"DNS không hợp lệ: {dns_key}")
                return

            dns = DNS_SERVERS[dns_key]

            try:
                import os

                system32 = os.path.join(
                    os.environ.get("SystemRoot", r"C:\Windows"), "System32"
                )
                netsh = os.path.join(system32, "netsh.exe")

                # Get active network adapter
                result = subprocess.run(
                    [netsh, "interface", "show", "interface"],
                    capture_output=True,
                    text=True,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

                # Find connected adapters
                adapters = []
                for line in result.stdout.split("\n"):
                    if "Connected" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            adapter_name = " ".join(parts[3:])
                            adapters.append(adapter_name)

                if not adapters:
                    adapters = ["Ethernet", "Wi-Fi"]  # Fallback

                success = True
                messages = []

                for adapter in adapters:
                    try:
                        # Set primary DNS
                        subprocess.run(
                            [
                                netsh,
                                "interface",
                                "ip",
                                "set",
                                "dns",
                                adapter,
                                "static",
                                dns.primary,
                            ],
                            capture_output=True,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW
                                if hasattr(subprocess, "CREATE_NO_WINDOW")
                                else 0
                            ),
                        )
                        # Add secondary DNS
                        subprocess.run(
                            [
                                netsh,
                                "interface",
                                "ip",
                                "add",
                                "dns",
                                adapter,
                                dns.secondary,
                                "index=2",
                            ],
                            capture_output=True,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW
                                if hasattr(subprocess, "CREATE_NO_WINDOW")
                                else 0
                            ),
                        )

                        messages.append(f"✅ {adapter}: {dns.name}")
                    except:
                        messages.append(f"⚠️ {adapter}: Cần Admin")
                        success = False

                message = f"DNS: {dns.name} ({dns.primary})\n" + "\n".join(messages)

                if on_complete:
                    on_complete(success, message)

            except Exception as e:
                if on_complete:
                    on_complete(False, f"Lỗi: {e}")

        threading.Thread(target=run_set_dns, daemon=True).start()

    @property
    def is_measuring(self) -> bool:
        return self._is_measuring

    @property
    def last_result(self) -> Optional[PingResult]:
        return self._last_result

    # ============ NEW FEATURES ============

    def ping_game_server(
        self, on_complete: Optional[Callable[[PingResult], None]] = None
    ) -> Optional[PingResult]:
        """
        Ping the default game server (Where Winds Meet)

        Args:
            on_complete: Async callback
        """
        game = DEFAULT_GAME_SERVER

        # Ping all servers and return best
        def measure():
            best_result = None
            best_latency = 9999

            # Ports to try for each server
            ports_to_try = [443, 80, 53]

            for server in game.servers:
                latency = None

                # Try each port until one works
                for port in ports_to_try:
                    latency = self._socket_ping(server, port=port, timeout=1.5)
                    if latency is not None:
                        break

                # Fallback to ICMP if all ports fail
                if latency is None:
                    latency = self._icmp_ping(server)

                if latency is not None and latency < best_latency:
                    best_latency = latency

                    best_result = PingResult(
                        latency_ms=latency,
                        quality=get_ping_quality(latency),
                        target=game.name,
                        success=True,
                    )

                    # If we got a good result, stop trying more servers
                    if latency < 200:
                        break

            if best_result is None:
                best_result = PingResult(
                    latency_ms=999,
                    quality=PingQuality.BAD,
                    target=game.name,
                    success=False,
                    error="Không thể kết nối",
                )

            self._last_result = best_result
            return best_result

        if on_complete:

            def async_measure():
                result = measure()
                on_complete(result)

            threading.Thread(target=async_measure, daemon=True).start()
            return None
        else:
            return measure()

    def one_click_boost(
        self,
        on_progress: Optional[Callable[[str, int], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None,
    ):
        """
        All-in-one network optimization:
        1. Flush DNS cache
        2. Find and apply best DNS
        3. Apply TCP optimizations

        Args:
            on_progress: Callback(step_name, percent)
            on_complete: Callback(success, summary_message)
        """

        def run_boost():
            results = []
            overall_success = True

            # STEP 0: Measure ping BEFORE optimization
            if on_progress:
                on_progress("📊 Đo ping hiện tại...", 5)

            before_result = self.ping_game_server()
            if before_result and before_result.success:
                self._ping_before = before_result.latency_ms

            # Step 1: Flush DNS (10%)
            if on_progress:
                on_progress("🔄 Flush DNS cache...", 15)

            try:
                import os

                system32 = os.path.join(
                    os.environ.get("SystemRoot", r"C:\Windows"), "System32"
                )
                ipconfig = os.path.join(system32, "ipconfig.exe")

                result = subprocess.run(
                    [ipconfig, "/flushdns"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )
                if result.returncode == 0:
                    results.append("✅ Flush DNS cache")
                    self._optimization_status["dns_cache"]["active"] = True
                else:
                    results.append("⚠️ Flush DNS (cần Admin)")
            except Exception as e:
                results.append(f"❌ Flush DNS: {e}")

            # Step 2: Find best DNS (40%)
            if on_progress:
                on_progress("🌐 Tìm DNS nhanh nhất...", 35)

            best_dns_key = "cloudflare"  # Default
            best_latency = 9999

            for key, dns in DNS_SERVERS.items():
                latency = self._socket_ping(dns.primary, port=53, timeout=1.5)
                if latency is not None and latency < best_latency:
                    best_latency = latency
                    best_dns_key = key

            results.append(
                f"✅ Best DNS: {DNS_SERVERS[best_dns_key].name} ({best_latency:.0f}ms)"
            )

            # Update DNS status
            self._optimization_status["dns"]["active"] = True
            self._optimization_status["dns"]["name"] = DNS_SERVERS[best_dns_key].name
            self._optimization_status["dns"]["latency"] = best_latency

            # Step 3: Apply best DNS (60%)
            if on_progress:
                on_progress(f"🌐 Áp dụng {DNS_SERVERS[best_dns_key].name}...", 55)

            # Note: set_dns requires admin, just try it
            try:
                dns = DNS_SERVERS[best_dns_key]
                netsh = os.path.join(system32, "netsh.exe")

                result = subprocess.run(
                    [netsh, "interface", "show", "interface"],
                    capture_output=True,
                    text=True,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

                adapters = []
                for line in result.stdout.split("\n"):
                    if "Connected" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            adapters.append(" ".join(parts[3:]))

                if adapters:
                    for adapter in adapters[:1]:  # Just first adapter
                        subprocess.run(
                            [
                                netsh,
                                "interface",
                                "ip",
                                "set",
                                "dns",
                                adapter,
                                "static",
                                dns.primary,
                            ],
                            capture_output=True,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW
                                if hasattr(subprocess, "CREATE_NO_WINDOW")
                                else 0
                            ),
                        )
                    results.append(f"✅ DNS: {dns.name}")
                else:
                    results.append("⚠️ Không tìm thấy adapter")
            except Exception as e:
                results.append("⚠️ Set DNS cần Admin")

            # Step 4: TCP Optimizations (80%)
            if on_progress:
                on_progress("⚡ Tối ưu TCP...", 75)

            try:
                import winreg

                # Disable network throttling
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                    0,
                    winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
                )
                winreg.SetValueEx(
                    key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xFFFFFFFF
                )
                winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                results.append("✅ TCP Optimization")
                self._optimization_status["tcp"]["active"] = True
            except PermissionError:
                results.append("⚠️ TCP Opt cần Admin")
            except Exception as e:
                results.append(f"⚠️ TCP: {str(e)[:30]}")

            # Step 5: Measure ping AFTER optimization (95%)
            if on_progress:
                on_progress("📊 Đo ping sau tối ưu...", 90)

            after_result = self.ping_game_server()
            if after_result and after_result.success:
                self._ping_after = after_result.latency_ms

            # Step 6: Done (100%)
            if on_progress:
                on_progress("✅ Hoàn tất!", 100)

            time.sleep(0.3)  # Brief pause for UI

            summary = "\n".join(results)
            if on_complete:
                on_complete(overall_success, summary)

        threading.Thread(target=run_boost, daemon=True).start()

    def start_realtime_monitor(
        self,
        interval_ms: int = 3000,
        on_update: Optional[Callable[[PingResult], None]] = None,
    ):
        """
        Start continuous ping monitoring for Where Winds Meet

        Args:
            interval_ms: Update interval
            on_update: Callback for each ping result
        """
        self._realtime_stop = False

        def monitor_loop():
            while not self._realtime_stop:
                result = self.ping_game_server()

                if on_update and not self._realtime_stop:
                    on_update(result)

                # Sleep in small increments to allow quick stop
                sleep_steps = max(1, interval_ms // 100)
                for _ in range(sleep_steps):
                    if self._realtime_stop:
                        break
                    time.sleep(0.1)

        self._realtime_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._realtime_thread.start()

    def stop_realtime_monitor(self):
        """Stop continuous monitoring"""
        self._realtime_stop = True

    @staticmethod
    def boost_process(
        process_name: str = None,
        on_complete: Optional[Callable[[bool, str], None]] = None,
    ):
        """
        Set game process to HIGH priority for better performance

        Args:
            process_name: Process name (e.g., "WeSky.exe")
            on_complete: Callback(success, message)
        """
        import ctypes

        def run_boost():
            try:
                import psutil

                # Find process
                found = False
                for proc in psutil.process_iter(["name", "pid"]):
                    if (
                        process_name
                        and process_name.lower() in proc.info["name"].lower()
                    ):
                        try:
                            # Set high priority
                            p = psutil.Process(proc.info["pid"])
                            p.nice(psutil.HIGH_PRIORITY_CLASS)
                            found = True

                            if on_complete:
                                on_complete(
                                    True, f"✅ {proc.info['name']} → HIGH priority"
                                )
                            return
                        except Exception as e:
                            if on_complete:
                                on_complete(False, f"⚠️ Cần Admin: {e}")
                            return

                if not found:
                    if on_complete:
                        on_complete(False, f"❌ Không tìm thấy: {process_name}")

            except ImportError:
                if on_complete:
                    on_complete(False, "❌ Cần cài psutil")
            except Exception as e:
                if on_complete:
                    on_complete(False, f"❌ Lỗi: {e}")

        threading.Thread(target=run_boost, daemon=True).start()

    @staticmethod
    def get_running_games() -> List[str]:
        """Get list of running game processes"""
        try:
            import psutil

            game_keywords = [
                "sky",
                "wesky",
                "flipper",
                "genshin",
                "zenless",
                "honkai",
                "valorant",
                "league",
                "lol",
                "pubg",
                "mlbb",
                "mobile legends",
                "fortnite",
                "minecraft",
                "steam",
                "epic",
                "origin",
            ]

            games = []
            for proc in psutil.process_iter(["name"]):
                name = proc.info["name"].lower()
                if any(kw in name for kw in game_keywords):
                    games.append(proc.info["name"])

            return list(set(games))  # Remove duplicates
        except:
            return []


# Singleton instance
_optimizer_instance: Optional[PingOptimizer] = None


def get_ping_optimizer() -> PingOptimizer:
    """Get singleton PingOptimizer instance"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = PingOptimizer()
    return _optimizer_instance
