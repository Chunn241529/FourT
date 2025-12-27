"""
Auth Service for FourT Community
Handles password hashing, JWT tokens, and session management
"""

import os
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Rank thresholds
RANK_THRESHOLDS = {
    "newcomer": 0,
    "player": 30,
    "contributor": 100,
    "artist": 300,
    "star": 600,
    "legend": 1000,
}

# Download cost discounts by rank
RANK_DISCOUNTS = {
    "newcomer": 0,
    "player": 1,
    "contributor": 1,
    "artist": 2,
    "star": 3,
    "legend": 99,  # Free
}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly"""
    # Truncate to 72 bytes (bcrypt limit)
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a token for storage (used for refresh tokens)"""
    return hashlib.sha256(token.encode()).hexdigest()


def calculate_rank(total_points_earned: int) -> str:
    """Calculate user rank based on total points earned"""
    current_rank = "newcomer"
    for rank, threshold in RANK_THRESHOLDS.items():
        if total_points_earned >= threshold:
            current_rank = rank
    return current_rank


def get_download_cost(user_rank: str, midi_type: str = "normal") -> int:
    """Calculate download cost based on user rank and MIDI type"""
    base_costs = {"normal": 3, "premium": 8, "exclusive": 15}
    base_cost = base_costs.get(midi_type, 3)
    discount = RANK_DISCOUNTS.get(user_rank, 0)
    return max(0, base_cost - discount)


def generate_token_pair(user_id: int, username: str, rank: str) -> Dict[str, str]:
    """Generate both access and refresh tokens for a user"""
    token_data = {"sub": str(user_id), "username": username, "rank": rank}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
