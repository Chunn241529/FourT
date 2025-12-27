"""
Auth Middleware for FourT Community
Provides dependency injection for authenticated routes
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import verify_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Get current authenticated user from JWT token.
    Raises 401 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": int(payload.get("sub")),
        "username": payload.get("username"),
        "rank": payload.get("rank"),
    }


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    Does not raise exception if not authenticated.
    """
    if credentials is None:
        return None

    payload = verify_token(credentials.credentials, token_type="access")
    if payload is None:
        return None

    return {
        "user_id": int(payload.get("sub")),
        "username": payload.get("username"),
        "rank": payload.get("rank"),
    }
