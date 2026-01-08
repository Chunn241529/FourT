"""
Request Signer Service for FourT Helper Client

Signs outgoing requests with HMAC signature for server validation.
Ensures request integrity and prevents tampering.
"""

import time
import hmac
import hashlib
import uuid
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RequestSigner:
    """
    Signs HTTP requests with HMAC signature
    
    Used by client to add authentication headers to API requests.
    Compatible with RequestValidatorMiddleware on server.
    """
    
    def __init__(self, secret: str = None):
        """
        Initialize RequestSigner
        
        Args:
            secret: Shared secret for HMAC. If None, uses environment variable
                   FOURT_SIGNATURE_SECRET or default key.
        """
        self.secret = secret or os.getenv(
            "FOURT_SIGNATURE_SECRET",
            "fourt-helper-secret-key-2025"
        )
        self._enabled = True
    
    def create_signature_headers(
        self,
        method: str,
        path: str,
        body: bytes = b""
    ) -> Dict[str, str]:
        """
        Create signature headers for a request
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path (e.g., /license/verify)
            body: Request body as bytes
            
        Returns:
            Dict with X-Timestamp, X-Nonce, X-Signature headers
        """
        if not self._enabled:
            return {}
        
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        
        # Hash the body
        body_hash = hashlib.sha256(body).hexdigest()
        
        # Create message to sign
        message = f"{timestamp}:{nonce}:{method}:{path}:{body_hash}"
        
        # Compute HMAC-SHA256
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature
        }
    
    def sign_request(
        self,
        method: str,
        url: str,
        body: bytes = b"",
        existing_headers: Dict = None
    ) -> Dict[str, str]:
        """
        Sign a request and return complete headers dict
        
        Args:
            method: HTTP method
            url: Full URL or just path
            body: Request body
            existing_headers: Existing headers to merge with
            
        Returns:
            Headers dict with signature headers added
        """
        from urllib.parse import urlparse
        
        # Extract path from URL
        parsed = urlparse(url)
        path = parsed.path or "/"
        
        # Get signature headers
        sig_headers = self.create_signature_headers(method, path, body)
        
        # Merge with existing headers
        headers = dict(existing_headers or {})
        headers.update(sig_headers)
        
        return headers
    
    def enable(self):
        """Enable request signing"""
        self._enabled = True
        logger.info("[RequestSigner] Enabled")
    
    def disable(self):
        """Disable request signing (for development/testing)"""
        self._enabled = False
        logger.info("[RequestSigner] Disabled")
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled


# Global instance
request_signer = RequestSigner()


def sign_request_headers(
    method: str,
    path: str,
    body: bytes = b""
) -> Dict[str, str]:
    """
    Convenience function to create signature headers
    
    Usage:
        headers = sign_request_headers("POST", "/license/verify", json_body)
        requests.post(url, headers={**base_headers, **headers}, data=json_body)
    """
    return request_signer.create_signature_headers(method, path, body)
