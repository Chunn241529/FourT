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
    GOOD = "good"            # 30-60ms
    FAIR = "fair"            # 60-100ms
    POOR = "poor"            # 100-150ms
    BAD = "bad"              # > 150ms


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
        PingQuality.GOOD: "#a6e3a1",       # Light green
        PingQuality.FAIR: "#f9e2af",       # Yellow
        PingQuality.POOR: "#fab387",       # Orange
        PingQuality.BAD: "#f38ba8",        # Red
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
    
    def estimate_ping(self, target: str = None, 
                      on_complete: Optional[Callable[[PingResult], None]] = None) -> Optional[PingResult]:
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
                target=self._measure_ping_async,
                args=(target, on_complete),
                daemon=True
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
                    latency_ms=latency,
                    quality=quality,
                    target=target,
                    success=True
                )
            else:
                # Fallback to ICMP ping
                latency = self._icmp_ping(target)
                if latency is not None:
                    quality = get_ping_quality(latency)
                    result = PingResult(
                        latency_ms=latency,
                        quality=quality,
                        target=target,
                        success=True
                    )
                else:
                    result = PingResult(
                        latency_ms=999,
                        quality=PingQuality.BAD,
                        target=target,
                        success=False,
                        error="Không thể đo ping"
                    )
        except Exception as e:
            result = PingResult(
                latency_ms=999,
                quality=PingQuality.BAD,
                target=target,
                success=False,
                error=str(e)
            )
        
        self._is_measuring = False
        self._last_result = result
        return result
    
    def _socket_ping(self, target: str, port: int = 443, timeout: float = 2.0) -> Optional[float]:
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
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout
            
            # Parse "time=XXms" or "time<1ms"
            import re
            match = re.search(r'time[=<](\d+)ms', output, re.IGNORECASE)
            if match:
                return float(match.group(1))
            
            return None
        except:
            return None
    
    def benchmark_dns(self, on_progress: Optional[Callable[[str, float], None]] = None,
                      on_complete: Optional[Callable[[List[tuple]], None]] = None):
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
        def run_flush():
            results = []
            success = True
            
            commands = [
                ("ipconfig /flushdns", "Flush DNS cache"),
                ("netsh winsock reset catalog", "Reset Winsock"),
                ("netsh int ip reset", "Reset IP stack"),
            ]
            
            for cmd, desc in commands:
                try:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if result.returncode == 0:
                        results.append(f"✅ {desc}")
                    else:
                        results.append(f"⚠️ {desc} (cần Admin)")
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
                (r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
                 "TcpNoDelay", 1, "Disable Nagle"),
                (r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
                 "TcpAckFrequency", 1, "Optimize ACK"),
                # Disable network throttling
                (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                 "NetworkThrottlingIndex", 0xffffffff, "Disable Throttling"),
                (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                 "SystemResponsiveness", 0, "Max Priority"),
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
                        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
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
    def set_dns(dns_key: str, on_complete: Optional[Callable[[bool, str], None]] = None):
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
                # Get active network adapter
                result = subprocess.run(
                    'netsh interface show interface',
                    shell=True,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Find connected adapters
                adapters = []
                for line in result.stdout.split('\n'):
                    if 'Connected' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            adapter_name = ' '.join(parts[3:])
                            adapters.append(adapter_name)
                
                if not adapters:
                    adapters = ["Ethernet", "Wi-Fi"]  # Fallback
                
                success = True
                messages = []
                
                for adapter in adapters:
                    try:
                        # Set primary DNS
                        cmd1 = f'netsh interface ip set dns "{adapter}" static {dns.primary}'
                        # Add secondary DNS
                        cmd2 = f'netsh interface ip add dns "{adapter}" {dns.secondary} index=2'
                        
                        subprocess.run(cmd1, shell=True, capture_output=True, 
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                        subprocess.run(cmd2, shell=True, capture_output=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                        
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


# Singleton instance
_optimizer_instance: Optional[PingOptimizer] = None


def get_ping_optimizer() -> PingOptimizer:
    """Get singleton PingOptimizer instance"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = PingOptimizer()
    return _optimizer_instance
