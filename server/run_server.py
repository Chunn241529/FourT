import uvicorn
import os
import sys
import subprocess
import threading
import time
import re
from dotenv import load_dotenv

load_dotenv()

# Global variable to track tunnel process
tunnel_process = None

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def start_bore_tunnel(port: int = 8000):
    """Start bore.pub tunnel and return the public URL"""
    global tunnel_process
    
    # Find bore executable
    bore_paths = [
        os.path.join(SCRIPT_DIR, "bore", "bore.exe"),
        os.path.join(SCRIPT_DIR, "bore.exe"),
        "bore",  # In PATH
    ]
    
    bore_exe = None
    for path in bore_paths:
        if os.path.exists(path) or path == "bore":
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    bore_exe = path
                    print(f"Found bore: {result.stdout.strip()}")
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
    
    if not bore_exe:
        print("bore not found. Please download from https://github.com/ekzhang/bore/releases")
        return None
    
    try:
        print(f"Starting bore.pub tunnel on port {port}...")
        
        # Start bore tunnel
        process = subprocess.Popen(
            [bore_exe, "local", str(port), "--to", "bore.pub"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        tunnel_process = process
        
        public_url = None
        start_time = time.time()
        
        def read_output():
            nonlocal public_url
            for line in process.stdout:
                line = line.strip()
                if line:
                    print(f"[bore] {line}")
                # Look for pattern: "listening at bore.pub:XXXXX"
                match = re.search(r'listening at bore\.pub:(\d+)', line, re.IGNORECASE)
                if match:
                    bore_port = match.group(1)
                    public_url = f"http://bore.pub:{bore_port}"
                    print(f"\n{'='*60}")
                    print(f"[OK] bore.pub Tunnel Started!")
                    print(f"   Public URL: {public_url}")
                    print(f"   Docs: {public_url}/docs")
                    print(f"{'='*60}\n")
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
        # Wait up to 15 seconds for URL
        while public_url is None and (time.time() - start_time) < 15:
            time.sleep(0.5)
        
        if public_url:
            return public_url
        else:
            print("Timeout waiting for bore.pub URL")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"Error starting bore: {e}")
        import traceback
        traceback.print_exc()
        return None


def start_localhost_run(port: int = 8000):
    """Start localhost.run SSH tunnel and return the public URL"""
    global tunnel_process
    
    # Check if SSH key exists
    ssh_key = os.path.expandvars(r"%USERPROFILE%\.ssh\id_rsa")
    if not os.path.exists(ssh_key):
        print("SSH key not found. localhost.run requires SSH key.")
        return None
    
    print(f"Starting localhost.run tunnel on port {port}...")
    
    try:
        process = subprocess.Popen(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=60",
                "-R", f"80:localhost:{port}",
                "localhost.run"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        tunnel_process = process
        
        public_url = None
        start_time = time.time()
        
        def read_output():
            nonlocal public_url
            for line in process.stdout:
                line = line.strip()
                if line:
                    print(f"[localhost.run] {line}")
                # Look for URL pattern
                match = re.search(r'(https://[a-z0-9]+\.[a-z0-9]+\.life)', line, re.IGNORECASE)
                if not match:
                    match = re.search(r'(https://[a-z0-9.-]+\.(link|run|io))', line, re.IGNORECASE)
                
                if match and 'localhost.run' not in match.group(1):
                    public_url = match.group(1)
                    print(f"\n{'='*60}")
                    print(f"[OK] localhost.run Tunnel Started!")
                    print(f"   Public URL: {public_url}")
                    print(f"{'='*60}\n")
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
        while public_url is None and (time.time() - start_time) < 30:
            time.sleep(0.5)
        
        if public_url:
            return public_url
        else:
            print("Timeout waiting for localhost.run URL")
            process.terminate()
            return None
            
    except FileNotFoundError:
        print("SSH not found.")
        return None
    except Exception as e:
        print(f"Error starting localhost.run: {e}")
        return None


def start_ngrok_tunnel(port: int = 8000):
    """Start ngrok tunnel and return the public URL"""
    global tunnel_process
    
    try:
        from pyngrok import ngrok, conf
        
        print(f"Starting ngrok tunnel on port {port}...")
        
        # Set authtoken from env if available
        ngrok_token = os.getenv("NGROK_AUTHTOKEN")
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
            print("[ngrok] Using authtoken from .env")
        
        # Kill any existing ngrok processes
        ngrok.kill()
        
        # Start tunnel
        public_url = ngrok.connect(port, "http")
        
        if public_url:
            url = str(public_url.public_url)
            print(f"\n{'='*60}")
            print(f"[OK] ngrok Tunnel Started!")
            print(f"   Public URL: {url}")
            print(f"   Docs: {url}/docs")
            print(f"{'='*60}\n")
            return url
        else:
            print("Failed to get ngrok URL")
            return None
            
    except ImportError:
        print("pyngrok not installed. Run: pip install pyngrok")
        return None
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        import traceback
        traceback.print_exc()
        return None


def start_cloudflare_tunnel(port: int = 8000):
    """Start Cloudflare Tunnel and return the public URL
    
    Uses cloudflared quick tunnel (no config needed) or configured tunnel.
    Quick tunnel: cloudflared tunnel --url http://localhost:8000
    """
    global tunnel_process
    
    # Find cloudflared executable
    cloudflared_paths = [
        os.path.join(SCRIPT_DIR, "cloudflared.exe"),
        "cloudflared",  # In PATH
    ]
    
    cloudflared_exe = None
    for path in cloudflared_paths:
        try:
            result = subprocess.run(
                [path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                cloudflared_exe = path
                print(f"Found cloudflared: {result.stdout.strip()}")
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not cloudflared_exe:
        print("cloudflared not found. Install: winget install cloudflare.cloudflared")
        return None
    
    try:
        print(f"Starting Cloudflare Tunnel on port {port}...")
        
        # Check for configured tunnel in env (default: fourtapi)
        tunnel_name = os.getenv("CLOUDFLARE_TUNNEL_NAME", "fourtapi")
        tunnel_url = os.getenv("CLOUDFLARE_TUNNEL_URL", "https://fourt.io.vn")
        
        if tunnel_name:
            # Use configured/named tunnel (fourt.io.vn)
            cmd = [cloudflared_exe, "tunnel", "run", "--url", f"http://localhost:{port}", tunnel_name]
            print(f"[Cloudflare] Using named tunnel: {tunnel_name}")
            print(f"[Cloudflare] Domain: {tunnel_url}")
        else:
            # Use quick tunnel (generates random URL) - fallback
            cmd = [cloudflared_exe, "tunnel", "--url", f"http://localhost:{port}"]
            print("[Cloudflare] Using quick tunnel (temporary URL)")
            tunnel_url = None  # Will be parsed from output
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        tunnel_process = process
        
        public_url = tunnel_url  # Use configured URL for named tunnel
        start_time = time.time()
        
        def read_output():
            nonlocal public_url
            for line in process.stdout:
                line = line.strip()
                if line:
                    print(f"[cloudflared] {line}")
                # For quick tunnel: Look for URL in output
                if not tunnel_name:
                    match = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', line, re.IGNORECASE)
                    if match:
                        public_url = match.group(1)
                        print(f"\n{'='*60}")
                        print(f"[OK] Cloudflare Quick Tunnel Started!")
                        print(f"   Public URL: {public_url}")
                        print(f"   Docs: {public_url}/docs")
                        print(f"{'='*60}\n")
                # For named tunnel: Check for "Registered tunnel connection"
                elif "Registered tunnel connection" in line or "Connection registered" in line:
                    print(f"\n{'='*60}")
                    print(f"[OK] Cloudflare Named Tunnel Connected!")
                    print(f"   Public URL: {tunnel_url}")
                    print(f"   Docs: {tunnel_url}/docs")
                    print(f"{'='*60}\n")
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
        # Wait up to 30 seconds for connection
        while (time.time() - start_time) < 30:
            time.sleep(0.5)
            if public_url:
                break
        
        if public_url:
            return public_url
        else:
            print("Timeout waiting for Cloudflare Tunnel")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"Error starting Cloudflare Tunnel: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_server_config(public_url: str, tunnel_type: str = "ngrok"):
    """Update server URL on npoint.io for client discovery
    
    Supports multiple tunnel types. Client will try them in priority order:
    cloudflare_url > ngrok_url > bore_url > server_url
    
    For named tunnels, checks if HTTPS is ready. Falls back to HTTP if not.
    """
    import json
    import urllib.request
    import ssl
    from datetime import datetime
    
    # Test if HTTPS is working for the URL
    def test_https(url: str, timeout: float = 5) -> bool:
        """Test if HTTPS connection works"""
        if not url.startswith("https://"):
            return True  # Not HTTPS, skip test
        try:
            req = urllib.request.Request(
                f"{url}/health",
                headers={'User-Agent': 'FourT-Server/1.0'}
            )
            # Create SSL context that doesn't verify (for testing)
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                return response.status in [200, 307, 308]
        except ssl.SSLError as e:
            print(f"[Config] HTTPS not ready (SSL): {e}")
            return False
        except Exception as e:
            error_str = str(e)
            # Check if error is SSL-related (wrapped in urllib error)
            if "SSL" in error_str or "ssl" in error_str or "certificate" in error_str.lower():
                print(f"[Config] HTTPS not ready: {e}")
                return False
            # Other errors (connection, timeout) - might still be starting up
            print(f"[Config] URL test: {e}")
            return True  # Assume OK for non-SSL errors
    
    # Check if HTTPS is ready, fallback to HTTP if not
    final_url = public_url
    if public_url.startswith("https://"):
        print(f"[Config] Testing HTTPS: {public_url}")
        if not test_https(public_url):
            http_url = public_url.replace("https://", "http://")
            print(f"[Config] HTTPS not ready, using HTTP temporarily: {http_url}")
            final_url = http_url
        else:
            print(f"[Config] HTTPS OK: {public_url}")
    
    # npoint.io endpoint
    NPOINT_API_URL = "https://api.npoint.io/c6878ec0e82ad63a767f"
    
    # First, fetch existing config to preserve other URLs
    existing_config = {}
    try:
        req = urllib.request.Request(
            NPOINT_API_URL,
            headers={'User-Agent': 'FourT-Server/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            existing_config = json.loads(response.read().decode('utf-8'))
    except:
        pass
    
    # Map tunnel type to field name
    field_map = {
        "cloudflare": "cloudflare_url",
        "ngrok": "ngrok_url",
        "bore": "bore_url",
        "localhost.run": "bore_url",  # Group with bore
    }
    
    field_name = field_map.get(tunnel_type, "server_url")
    
    # Build new config preserving existing URLs
    config_data = {
        "cloudflare_url": existing_config.get("cloudflare_url"),
        "ngrok_url": existing_config.get("ngrok_url"),
        "bore_url": existing_config.get("bore_url"),
        "server_url": final_url,  # Use tested URL (HTTPS or HTTP fallback)
        "updated_at": datetime.now().isoformat()
    }
    
    # Update the specific tunnel field with tested URL
    config_data[field_name] = final_url
    
    # Remove None values
    config_data = {k: v for k, v in config_data.items() if v is not None}
    
    # Also update local file for reference
    config_file = os.path.join(SCRIPT_DIR, "server_config.json")
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=4)
    except:
        pass
    
    # Update npoint.io
    try:
        data = json.dumps(config_data).encode('utf-8')
        req = urllib.request.Request(
            NPOINT_API_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'FourT-Server/1.0'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"[Config] [OK] Updated npoint.io with {tunnel_type}: {final_url}")
                print("[Config] Clients will automatically discover this URL!")
                print(f"[Config] Current URLs: cloudflare={config_data.get('cloudflare_url', 'N/A')}, ngrok={config_data.get('ngrok_url', 'N/A')}, bore={config_data.get('bore_url', 'N/A')}")
            else:
                print(f"[Config] [WARN] npoint.io returned status: {response.status}")
                
    except Exception as e:
        print(f"[Config] [WARN] Could not update npoint.io: {e}")
        print(f"[Config] Please manually update at: https://www.npoint.io/docs/c6878ec0e82ad63a767f")
        print(f"[Config] Set {field_name} to: {final_url}")


def run():
    # Add current directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    print("Starting FourT Helper Backend...")
    print("Documentation available at http://localhost:8000/docs")
    
    # Tunnel configuration
    # Options: cloudflare (recommended), ngrok, bore, localhost.run, none
    TUNNEL_TYPE = os.getenv("TUNNEL_TYPE", "ngrok")
    
    public_url = None
    actual_tunnel_type = None
    
    if TUNNEL_TYPE == "cloudflare":
        print("\n[Tunnel] Using Cloudflare Tunnel...")
        public_url = start_cloudflare_tunnel(8000)
        actual_tunnel_type = "cloudflare"
        if not public_url:
            print("[Tunnel] Cloudflare failed, trying ngrok...")
            public_url = start_ngrok_tunnel(8000)
            actual_tunnel_type = "ngrok"
    
    elif TUNNEL_TYPE == "ngrok":
        print("\n[Tunnel] Using ngrok...")
        public_url = start_ngrok_tunnel(8000)
        actual_tunnel_type = "ngrok"
        if not public_url:
            print("[Tunnel] ngrok failed, trying bore...")
            public_url = start_bore_tunnel(8000)
            actual_tunnel_type = "bore"
    
    elif TUNNEL_TYPE == "bore":
        print("\n[Tunnel] Using bore.pub...")
        public_url = start_bore_tunnel(8000)
        actual_tunnel_type = "bore"
        if not public_url:
            print("[Tunnel] bore failed, trying ngrok...")
            public_url = start_ngrok_tunnel(8000)
            actual_tunnel_type = "ngrok"
            
    elif TUNNEL_TYPE == "localhost.run":
        print("\n[Tunnel] Using localhost.run...")
        public_url = start_localhost_run(8000)
        actual_tunnel_type = "localhost.run"
        if not public_url:
            print("[Tunnel] localhost.run failed, trying ngrok...")
            public_url = start_ngrok_tunnel(8000)
            actual_tunnel_type = "ngrok"
            
    elif TUNNEL_TYPE == "none":
        print("\n[Tunnel] Tunneling disabled. Server available at localhost only.")
    else:
        print(f"\n[Tunnel] Unknown TUNNEL_TYPE: {TUNNEL_TYPE}, using ngrok...")
        public_url = start_ngrok_tunnel(8000)
        actual_tunnel_type = "ngrok"
    
    if public_url:
        os.environ["PUBLIC_URL"] = public_url
        print(f"\n[Server] Public URL: {public_url}")
        
        # Update npoint.io for client discovery (with correct tunnel type)
        update_server_config(public_url, actual_tunnel_type or TUNNEL_TYPE)
    else:
        print("\n[Server] No tunnel established. Running on localhost only.")

    # Import and run FastAPI app
    try:
        from backend.main import app
    except ImportError as e:
        print(f"Error importing backend.main: {e}")
        raise

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    run()
