"""
Sync Service - Handles full synchronization from server to client
Syncs: License, Skills, Templates, MIDI files, and Version check
"""

import os
import json
import threading
from typing import Callable, Optional, Dict, Any, List


class SyncService:
    """
    Central service for syncing data from server to client.
    Reuses existing logic from connection_manager, feature_manager, 
    wwm_combo_service, and update_service.
    """
    
    def __init__(self, feature_manager=None):
        """
        Initialize sync service
        
        Args:
            feature_manager: FeatureManager instance for license operations
        """
        self.feature_manager = feature_manager
        self._sync_results: Dict[str, Any] = {}
        
    def sync_all(
        self, 
        on_progress: Optional[Callable[[str, int], None]] = None,
        on_complete: Optional[Callable[[Dict], None]] = None,
        threaded: bool = True
    ):
        """
        Run full sync from server
        
        Args:
            on_progress: Callback(status_text, percent) for progress updates
            on_complete: Callback(result_dict) when sync completes
            threaded: If True, run in background thread
        """
        if threaded:
            thread = threading.Thread(
                target=self._sync_all_internal,
                args=(on_progress, on_complete),
                daemon=True
            )
            thread.start()
        else:
            self._sync_all_internal(on_progress, on_complete)
    
    def _sync_all_internal(
        self, 
        on_progress: Optional[Callable[[str, int], None]],
        on_complete: Optional[Callable[[Dict], None]]
    ):
        """Internal sync implementation"""
        results = {
            'success': True,
            'license_synced': False,
            'skills_synced': False,
            'templates_synced': 0,
            'midi_synced': 0,
            'has_update': False,
            'update_info': None,
            'errors': []
        }
        
        def update_progress(status: str, percent: int):
            if on_progress:
                on_progress(status, percent)
            print(f"[Sync] {status} ({percent}%)")
        
        try:
            # Step 1: Check connection (0-10%)
            update_progress("Đang kết nối server...", 0)
            is_online = self._check_connection()
            
            if not is_online:
                update_progress("❌ Server offline", 100)
                results['success'] = False
                results['errors'].append("Server offline - không thể đồng bộ")
                if on_complete:
                    on_complete(results)
                return
            
            update_progress("✅ Server connected", 10)
            
            # Step 2: Sync License (10-25%)
            update_progress("Đang xác thực license...", 15)
            license_ok = self._sync_license()
            results['license_synced'] = license_ok
            update_progress("✅ License verified" if license_ok else "⚠️ License check failed", 25)
            
            # Step 3: Sync Skills (25-40%)
            update_progress("Đang tải skill data...", 30)
            skills_ok = self._sync_skills()
            results['skills_synced'] = skills_ok
            update_progress("✅ Skills synced" if skills_ok else "⚠️ Skills sync skipped", 40)
            
            # Step 4: Sync Templates (40-60%)
            update_progress("Đang tải combo templates...", 45)
            templates_count = self._sync_templates()
            results['templates_synced'] = templates_count
            update_progress(f"✅ {templates_count} templates mới", 60)
            
            # Step 5: Sync MIDI Library (60-85%)
            update_progress("Đang kiểm tra MIDI files...", 65)
            midi_count = self._sync_midi_library(
                lambda p: update_progress(f"Đang tải MIDI ({p}%)...", 65 + int(p * 0.2))
            )
            results['midi_synced'] = midi_count
            update_progress(f"✅ {midi_count} MIDI files mới", 85)
            
            # Step 6: Check Version (85-100%)
            update_progress("Đang kiểm tra phiên bản...", 90)
            has_update, update_info = self._check_version()
            results['has_update'] = has_update
            results['update_info'] = update_info
            
            if has_update:
                update_progress(f"🆕 Có phiên bản mới: {update_info.get('version', '')}", 100)
            else:
                update_progress("✅ Đã cập nhật mới nhất!", 100)
            
        except Exception as e:
            print(f"[Sync] Error: {e}")
            import traceback
            traceback.print_exc()
            results['success'] = False
            results['errors'].append(str(e))
            if on_progress:
                on_progress(f"❌ Lỗi: {e}", 100)
        
        if on_complete:
            on_complete(results)
        
        return results
    
    def _check_connection(self) -> bool:
        """Check server connection"""
        try:
            from services.connection_manager import get_connection_manager
            from core.config import refresh_server_url
            
            conn_mgr = get_connection_manager()
            is_online = conn_mgr.check_connection(force=True)
            
            if is_online:
                # Refresh server URL
                refresh_server_url()
            
            return is_online
        except Exception as e:
            print(f"[Sync] Connection check error: {e}")
            return False
    
    def _sync_license(self) -> bool:
        """Re-verify license with server"""
        try:
            if not self.feature_manager:
                from feature_manager import get_feature_manager
                self.feature_manager = get_feature_manager()
            
            if self.feature_manager and self.feature_manager.license_key:
                verified = self.feature_manager.verify_license()
                if verified:
                    self.feature_manager._save_license_cache()
                    print(f"[Sync] License verified: {self.feature_manager.current_package}")
                    return True
                else:
                    print("[Sync] License verification failed")
            else:
                print("[Sync] No license to sync")
            return False
        except Exception as e:
            print(f"[Sync] License sync error: {e}")
            return False
    
    def _sync_skills(self) -> bool:
        """Sync skills.json from server"""
        try:
            from services.connection_manager import is_server_offline
            if is_server_offline():
                return False
            
            from core.config import get_license_server_url
            import requests
            
            api_url = f"{get_license_server_url()}/skills/data"
            print(f"[Sync] Fetching skills from: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Save to local data/skills.json
                data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
                skills_file = os.path.join(data_dir, "skills.json")
                
                os.makedirs(data_dir, exist_ok=True)
                with open(skills_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                skills_count = len(data.get('skills', []))
                print(f"[Sync] Saved {skills_count} skills to {skills_file}")
                return True
            else:
                print(f"[Sync] Skills API returned {response.status_code}")
        except Exception as e:
            print(f"[Sync] Skills sync error: {e}")
        return False
    
    def _sync_templates(self) -> int:
        """Sync combo templates from server. Returns count of new templates."""
        try:
            from services.wwm_combo_service import TemplateManager, get_combos_dir
            
            combos_dir = get_combos_dir()
            template_mgr = TemplateManager(combos_dir)
            
            # Get count before sync
            before_count = len(template_mgr.templates)
            
            # Fetch and merge server templates (existing logic)
            template_mgr.fetch_server_templates(timeout=10)
            
            # Count new templates
            after_count = len(template_mgr.templates)
            new_count = after_count - before_count
            
            print(f"[Sync] Templates: {before_count} -> {after_count} (+{new_count})")
            return new_count
            
        except Exception as e:
            print(f"[Sync] Template sync error: {e}")
            return 0
    
    def _sync_midi_library(self, on_progress: Optional[Callable[[int], None]] = None) -> int:
        """
        Sync MIDI files from server library.
        Downloads new files that don't exist locally.
        Returns count of new files downloaded.
        """
        try:
            from services.connection_manager import is_server_offline
            if is_server_offline():
                return 0
                
            from core.config import get_license_server_url
            import requests
            
            # Step 1: Get MIDI list from server
            api_url = f"{get_license_server_url()}/midi/list"
            print(f"[Sync] Fetching MIDI list from: {api_url}")
            
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                print(f"[Sync] MIDI list API returned {response.status_code}")
                return 0
            
            server_files = response.json().get('files', [])
            if not server_files:
                print("[Sync] No MIDI files on server")
                return 0
            
            # Step 2: Check which files are missing locally
            midi_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "midi_files")
            os.makedirs(midi_dir, exist_ok=True)
            
            local_files = set(os.listdir(midi_dir)) if os.path.exists(midi_dir) else set()
            
            # Find files to download
            files_to_download = []
            for file_info in server_files:
                filename = file_info.get('filename', '')
                if filename and filename not in local_files:
                    files_to_download.append(file_info)
            
            if not files_to_download:
                print("[Sync] All MIDI files already up to date")
                return 0
            
            print(f"[Sync] {len(files_to_download)} new MIDI files to download")
            
            # Step 3: Download missing files
            base_url = get_license_server_url()
            downloaded = 0
            
            for i, file_info in enumerate(files_to_download):
                try:
                    filename = file_info['filename']
                    url = file_info.get('url', f"/midi/{filename}")
                    
                    if not url.startswith('http'):
                        url = f"{base_url}{url}"
                    
                    # Download file
                    file_response = requests.get(url, timeout=30)
                    if file_response.status_code == 200:
                        file_path = os.path.join(midi_dir, filename)
                        with open(file_path, 'wb') as f:
                            f.write(file_response.content)
                        downloaded += 1
                        print(f"[Sync] Downloaded: {filename}")
                    
                    # Progress callback
                    if on_progress:
                        percent = int((i + 1) / len(files_to_download) * 100)
                        on_progress(percent)
                        
                except Exception as e:
                    print(f"[Sync] Failed to download {file_info.get('filename', '?')}: {e}")
            
            return downloaded
            
        except Exception as e:
            print(f"[Sync] MIDI sync error: {e}")
            return 0
    
    def _check_version(self) -> tuple:
        """
        Check for app version update.
        Returns (has_update: bool, update_info: dict or None)
        """
        try:
            from utils import get_current_version
            from core.config import get_license_server_url
            import urllib.request
            
            # Use dynamic server URL (not static UPDATE_SERVER_URL which may be stale)
            update_url = f"{get_license_server_url()}/update/info"
            
            req = urllib.request.Request(update_url, headers={'User-Agent': 'FourT-Helper/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            server_version = data.get('version', '')
            current_version = get_current_version()
            
            if self._compare_versions(server_version, current_version) > 0:
                # Build full download URL
                installer_url = data.get('installer_url', '')
                if installer_url and not installer_url.startswith('http'):
                    from urllib.parse import urljoin
                    base_url = update_url.rsplit('/', 2)[0] + '/'
                    installer_url = urljoin(base_url, installer_url)
                
                update_info = {
                    'version': server_version,
                    'current_version': current_version,
                    'changelog': data.get('changelog', ''),
                    'download_url': installer_url,
                }
                print(f"[Sync] Update available: {current_version} -> {server_version}")
                return True, update_info
            
            print(f"[Sync] Version up to date: {current_version}")
            return False, None
            
        except Exception as e:
            print(f"[Sync] Version check error: {e}")
            return False, None
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
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


# Convenience function
def get_sync_service(feature_manager=None) -> SyncService:
    """Get a SyncService instance"""
    return SyncService(feature_manager)
