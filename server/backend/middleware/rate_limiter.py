"""
Rate Limiting Middleware for FourT Helper Backend

Uses sliding window algorithm with SQLite for persistence.
Provides per-IP and per-endpoint rate limiting with auto-blacklist.
"""

import time
import logging
from typing import Dict, Tuple, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from backend import database as db

logger = logging.getLogger(__name__)


# Rate limit configurations per endpoint category
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    # (max_requests, window_seconds)
    "/license": (50, 60),  # 50 requests per minute for license operations
    "/trial": (20, 600),  # 20 requests per 10 minutes for trial
    "/payment": (30, 60),  # 30 requests per minute for payment
    "/sepay": (60, 60),  # 60 requests per minute for webhooks
    "/health": (300, 60),  # 300 requests per minute for health checks
    "/static": (500, 60),  # Higher limit for static files
    "/addons": (100, 60),  # Addon downloads
    "/community": (200, 60),  # Community pages and API
    "/api": (200, 60),  # API requests
    "default": (200, 60),  # Default: 200 requests per minute
}

# Auto-blacklist threshold
BLACKLIST_THRESHOLD = 50  # Number of violations before auto-blacklist
BLACKLIST_DURATION_HOURS = 24  # How long to block


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using in-memory cache with SQLite backup

    Features:
    - Sliding window rate limiting per IP
    - Different limits per endpoint category
    - Auto-blacklist for repeat offenders
    - Whitelist bypass for admin IPs
    - Rate limit headers in response
    """

    def __init__(self, app, whitelist_ips: set = None):
        super().__init__(app)
        # In-memory cache for fast lookups
        self._request_cache: Dict[str, list] = defaultdict(list)
        self._violation_count: Dict[str, int] = defaultdict(int)
        self._blacklist_cache: set = set()
        self._whitelist: set = whitelist_ips or {"127.0.0.1", "::1"}
        self._last_cleanup = time.time()

        logger.info("[RateLimit] Middleware initialized")

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request"""
        # Check X-Forwarded-For first (when behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _get_endpoint_category(self, path: str) -> str:
        """Get rate limit category for endpoint"""
        for prefix in RATE_LIMITS:
            if prefix != "default" and path.startswith(prefix):
                return prefix
        return "default"

    def _get_rate_limit(self, category: str) -> Tuple[int, int]:
        """Get rate limit config for category"""
        return RATE_LIMITS.get(category, RATE_LIMITS["default"])

    def _cleanup_old_requests(self, ip: str, category: str, window: int):
        """Remove expired requests from cache"""
        now = time.time()
        cutoff = now - window

        cache_key = f"{ip}:{category}"
        if cache_key in self._request_cache:
            self._request_cache[cache_key] = [
                ts for ts in self._request_cache[cache_key] if ts > cutoff
            ]

    def _check_rate_limit(self, ip: str, category: str) -> Tuple[bool, int, int, int]:
        """
        Check if request is within rate limit

        Returns: (allowed, current_count, limit, reset_time)
        """
        max_requests, window = self._get_rate_limit(category)
        now = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(ip, category, window)

        cache_key = f"{ip}:{category}"
        current_requests = self._request_cache[cache_key]
        current_count = len(current_requests)

        # Calculate reset time
        if current_requests:
            oldest = min(current_requests)
            reset_time = int(oldest + window - now)
        else:
            reset_time = window

        if current_count >= max_requests:
            return False, current_count, max_requests, max(0, reset_time)

        # Record this request
        current_requests.append(now)

        return True, current_count + 1, max_requests, max(0, reset_time)

    def _record_violation(self, ip: str, endpoint: str):
        """Record a rate limit violation"""
        self._violation_count[ip] += 1
        count = self._violation_count[ip]

        logger.warning(f"[RateLimit] Violation #{count} from {ip} on {endpoint}")

        # Auto-blacklist if threshold exceeded
        if count >= BLACKLIST_THRESHOLD:
            self._auto_blacklist(ip)

    def _auto_blacklist(self, ip: str):
        """Automatically blacklist an IP"""
        blocked_until = (
            datetime.now() + timedelta(hours=BLACKLIST_DURATION_HOURS)
        ).isoformat()

        # Add to memory cache
        self._blacklist_cache.add(ip)

        # Record in database (async - fire and forget pattern)
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            loop.create_task(
                db.add_to_blacklist(
                    ip,
                    reason="Auto-blacklisted: rate limit violations",
                    blocked_until=blocked_until,
                )
            )
        except Exception as e:
            logger.error(f"[RateLimit] Error adding to blacklist: {e}")

        logger.warning(f"[RateLimit] IP {ip} auto-blacklisted until {blocked_until}")

    async def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        # Check memory cache first
        if ip in self._blacklist_cache:
            return True

        # Check database
        try:
            is_blocked = await db.is_ip_blacklisted(ip)
            if is_blocked:
                self._blacklist_cache.add(ip)
            return is_blocked
        except Exception as e:
            logger.error(f"[RateLimit] Error checking blacklist: {e}")
            return False

    async def _is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        # Check in-memory whitelist first
        if ip in self._whitelist:
            return True

        # Check database
        try:
            return await db.is_ip_whitelisted(ip)
        except Exception:
            return False

    def _periodic_cleanup(self):
        """Periodic cleanup of stale cache entries"""
        now = time.time()
        if now - self._last_cleanup < 300:  # Every 5 minutes
            return

        self._last_cleanup = now

        # Clean old request entries
        for key in list(self._request_cache.keys()):
            if not self._request_cache[key]:
                del self._request_cache[key]

        logger.debug("[RateLimit] Cache cleanup completed")

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""
        ip = self._get_client_ip(request)
        path = request.url.path
        category = self._get_endpoint_category(path)

        # Periodic cleanup
        self._periodic_cleanup()

        # Check whitelist
        if await self._is_whitelisted(ip):
            response = await call_next(request)
            return response

        # Check blacklist
        if await self._is_blacklisted(ip):
            logger.warning(f"[RateLimit] Blocked request from blacklisted IP: {ip}")

            # Log security event
            await db.log_security_event(
                event_type="BLOCKED_REQUEST",
                ip_address=ip,
                endpoint=path,
                details={"reason": "IP blacklisted"},
            )

            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Your IP has been blocked due to suspicious activity",
                },
            )

        # Check rate limit
        allowed, count, limit, reset = self._check_rate_limit(ip, category)

        if not allowed:
            self._record_violation(ip, path)

            # Log security event
            await db.log_security_event(
                event_type="RATE_LIMIT_EXCEEDED",
                ip_address=ip,
                endpoint=path,
                details={"count": count, "limit": limit, "category": category},
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Try again in {reset} seconds.",
                    "retry_after": reset,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - count)
        response.headers["X-RateLimit-Reset"] = str(reset)

        return response
