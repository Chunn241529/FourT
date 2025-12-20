"""
Secure License Cache - Encryption, HMAC, and Hardware Binding
Protects license data from tampering when used offline
"""

import os
import json
import base64
import hashlib
import hmac
import time
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from device_utils import get_device_id


class SecureLicenseCache:
    """
    Secure license cache with:
    1. AES encryption (Fernet) using device-bound key
    2. HMAC signature for tamper detection
    3. Hardware binding via device_id
    """
    
    # Salt for key derivation (can be public, adds entropy)
    SALT = b"FourT_License_Salt_v1"
    
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.device_id = get_device_id()
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance with device-bound key"""
        # Derive key from device_id using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.SALT,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.device_id.encode()))
        return Fernet(key)
    
    def _compute_hmac(self, data: bytes) -> str:
        """Compute HMAC-SHA256 for data integrity"""
        secret = (self.device_id + "FourT_HMAC_Secret").encode()
        return hmac.new(secret, data, hashlib.sha256).hexdigest()
    
    def save(self, license_data: Dict[str, Any]) -> bool:
        """
        Save license data with encryption and signature.
        
        Args:
            license_data: Dict containing license_key, package, expires_at, last_verified_at
            
        Returns:
            True if saved successfully
        """
        try:
            # Add hardware binding
            license_data['bound_device_id'] = self.device_id
            license_data['cached_at'] = time.time()
            
            # Serialize to JSON
            json_data = json.dumps(license_data, ensure_ascii=False)
            
            # Encrypt
            encrypted_data = self._fernet.encrypt(json_data.encode('utf-8'))
            
            # Compute HMAC
            signature = self._compute_hmac(encrypted_data)
            
            # Package together
            package = {
                'encrypted_data': base64.b64encode(encrypted_data).decode('ascii'),
                'signature': signature,
                'version': 1
            }
            
            # Ensure directory exists
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            
            # Write to file
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(package, f)
            
            print(f"[SecureCache] License saved and encrypted")
            return True
            
        except Exception as e:
            print(f"[SecureCache] Save error: {e}")
            return False
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load and verify license data.
        
        Returns:
            Decrypted license data if valid, None if invalid/missing/tampered
        """
        if not os.path.exists(self.cache_file):
            return None
            
        try:
            # Read package
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                package = json.load(f)
            
            encrypted_data = base64.b64decode(package['encrypted_data'])
            stored_signature = package['signature']
            
            # Verify HMAC first (detect tampering before decryption)
            computed_signature = self._compute_hmac(encrypted_data)
            if not hmac.compare_digest(stored_signature, computed_signature):
                print("[SecureCache] HMAC verification failed - file tampered!")
                self._remove_cache()
                return None
            
            # Decrypt
            decrypted_data = self._fernet.decrypt(encrypted_data)
            license_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Verify hardware binding
            bound_device = license_data.get('bound_device_id', '')
            if bound_device != self.device_id:
                print(f"[SecureCache] Device mismatch - cache from different machine!")
                self._remove_cache()
                return None
            
            print(f"[SecureCache] License loaded and verified")
            return license_data
            
        except Exception as e:
            print(f"[SecureCache] Load error: {e}")
            self._remove_cache()
            return None
    
    def _remove_cache(self):
        """Safely remove corrupted cache file"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("[SecureCache] Removed invalid cache file")
        except Exception as e:
            print(f"[SecureCache] Remove error: {e}")
    
    def is_valid(self) -> bool:
        """Check if cache exists and is valid (without full load)"""
        return self.load() is not None
