"""
Request Validator Middleware for FourT Helper Backend

Validates incoming requests with HMAC signature verification.
Prevents replay attacks with nonce tracking and timestamp validation.
"""

import time
import hmac
import hashlib
import logging
from typing import Optional, Set
from collections import OrderedDict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from backend import database as db

logger = logging.getLogger(__name__)


# Configuration
SIGNATURE_ENABLED = True  # Set to False to disable signature validation
SIGNATURE_TIMEOUT = 300  # 5 minutes - reject requests older than this
NONCE_CACHE_SIZE = 10000  # Max nonces to track
EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/static",
    "/addons",
    "/sepay/webhook",  # Webhook has its own auth
}
EXEMPT_PREFIXES = ["/static/", "/addons/"]

# Secret key for HMAC (should be loaded from environment in production)
import os
SIGNATURE_SECRET = os.getenv("FOURT_SIGNATURE_SECRET", "fourt-helper-secret-key-2025")


class NonceCache:
    """LRU cache for tracking used nonces to prevent replay attacks"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: OrderedDict[str, float] = OrderedDict()
    
    def contains(self, nonce: str) -> bool:
        """Check if nonce was already used"""
        return nonce in self._cache
    
    def add(self, nonce: str) -> None:
        """Add nonce to cache"""
        if nonce in self._cache:
            return
        
        # Evict oldest entries if cache is full
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        
        self._cache[nonce] = time.time()
    
    def cleanup(self, max_age: int = 600) -> int:
        """Remove nonces older than max_age seconds"""
        cutoff = time.time() - max_age
        removed = 0
        
        # Create list of keys to remove (can't modify during iteration)
        to_remove = [k for k, v in self._cache.items() if v < cutoff]
        for key in to_remove:
            del self._cache[key]
            removed += 1
        
        return removed


class RequestValidatorMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware with HMAC signature verification
    
    Required headers for protected endpoints:
    - X-Timestamp: Unix timestamp when request was created
    - X-Nonce: Random unique string for this request
    - X-Signature: HMAC-SHA256 signature
    
    Signature is computed as:
    HMAC-SHA256(secret, f"{timestamp}:{nonce}:{method}:{path}:{body_hash}")
    
    Features:
    - Timestamp validation (rejects old requests)
    - Nonce tracking (prevents replay attacks)
    - HMAC signature verification
    - Configurable exempt paths
    """
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled and SIGNATURE_ENABLED
        self.nonce_cache = NonceCache(NONCE_CACHE_SIZE)
        self._last_cleanup = time.time()
        logger.info(f"[RequestValidator] Middleware initialized, enabled={self.enabled}")
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from signature validation"""
        if path in EXEMPT_PATHS:
            return True
        
        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _verify_timestamp(self, timestamp_str: str) -> tuple[bool, str]:
        """Verify timestamp is valid and not too old"""
        try:
            timestamp = int(timestamp_str)
        except (ValueError, TypeError):
            return False, "Invalid timestamp format"
        
        now = int(time.time())
        age = now - timestamp
        
        if age < -60:  # Allow 1 minute clock skew
            return False, "Timestamp is in the future"
        
        if age > SIGNATURE_TIMEOUT:
            return False, f"Request expired (age: {age}s, max: {SIGNATURE_TIMEOUT}s)"
        
        return True, "OK"
    
    def _verify_nonce(self, nonce: str) -> tuple[bool, str]:
        """Verify nonce hasn't been used before"""
        if not nonce or len(nonce) < 8:
            return False, "Invalid nonce format (min 8 characters)"
        
        if self.nonce_cache.contains(nonce):
            return False, "Nonce already used (replay attack detected)"
        
        return True, "OK"
    
    def _compute_signature(
        self,
        timestamp: str,
        nonce: str,
        method: str,
        path: str,
        body: bytes
    ) -> str:
        """Compute expected HMAC signature"""
        # Hash the body
        body_hash = hashlib.sha256(body).hexdigest()
        
        # Create message to sign
        message = f"{timestamp}:{nonce}:{method}:{path}:{body_hash}"
        
        # Compute HMAC
        signature = hmac.new(
            SIGNATURE_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_signature(
        self,
        provided: str,
        expected: str
    ) -> tuple[bool, str]:
        """Verify the provided signature matches expected"""
        if not provided:
            return False, "Missing signature"
        
        if not hmac.compare_digest(provided, expected):
            return False, "Invalid signature"
        
        return True, "OK"
    
    def _periodic_cleanup(self):
        """Periodically cleanup old nonces"""
        now = time.time()
        if now - self._last_cleanup < 300:  # Every 5 minutes
            return
        
        self._last_cleanup = now
        removed = self.nonce_cache.cleanup(SIGNATURE_TIMEOUT * 2)
        if removed > 0:
            logger.debug(f"[RequestValidator] Cleaned up {removed} old nonces")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with signature validation"""
        path = request.url.path
        
        # Skip if disabled or path is exempt
        if not self.enabled or self._is_exempt(path):
            return await call_next(request)
        
        # Periodic cleanup
        self._periodic_cleanup()
        
        # Get required headers
        timestamp = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")
        signature = request.headers.get("X-Signature")
        
        # Check if headers are present (for development, allow unsigned requests)
        # In production, remove this check
        if not timestamp and not nonce and not signature:
            # Allow unsigned requests in development
            # TODO: Remove this in production
            return await call_next(request)
        
        # Validate timestamp
        valid, error = self._verify_timestamp(timestamp)
        if not valid:
            await db.log_security_event(
                event_type="INVALID_TIMESTAMP",
                ip_address=request.client.host if request.client else None,
                endpoint=path,
                details={"error": error, "timestamp": timestamp}
            )
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": error}
            )
        
        # Validate nonce
        valid, error = self._verify_nonce(nonce)
        if not valid:
            await db.log_security_event(
                event_type="INVALID_NONCE",
                ip_address=request.client.host if request.client else None,
                endpoint=path,
                details={"error": error, "nonce": nonce}
            )
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": error}
            )
        
        # Read body for signature verification
        body = await request.body()
        
        # Compute expected signature
        expected_signature = self._compute_signature(
            timestamp,
            nonce,
            request.method,
            path,
            body
        )
        
        # Verify signature
        valid, error = self._verify_signature(signature, expected_signature)
        if not valid:
            await db.log_security_event(
                event_type="INVALID_SIGNATURE",
                ip_address=request.client.host if request.client else None,
                endpoint=path,
                details={"error": error}
            )
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": error}
            )
        
        # All validation passed - record nonce and proceed
        self.nonce_cache.add(nonce)
        
        return await call_next(request)


def create_signature(
    method: str,
    path: str,
    body: bytes = b"",
    secret: str = None
) -> dict:
    """
    Helper function to create signature headers for client use
    
    Returns dict with:
    - X-Timestamp
    - X-Nonce
    - X-Signature
    """
    import uuid
    
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    
    # Hash the body
    body_hash = hashlib.sha256(body).hexdigest()
    
    # Create message to sign
    message = f"{timestamp}:{nonce}:{method}:{path}:{body_hash}"
    
    # Compute HMAC
    key = (secret or SIGNATURE_SECRET).encode()
    signature = hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
    
    return {
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature
    }
