"""
Auth Router for FourT Community
Handles user registration, login, token refresh, and logout
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, validator

from backend.database import get_db
from services.auth_service import (
    hash_password,
    verify_password,
    generate_token_pair,
    verify_token,
    hash_token,
    calculate_rank,
)
from backend.middleware.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============== Pydantic Models ==============


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @validator("username")
    def username_valid(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, and underscores"
            )
        return v.lower()

    @validator("password")
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class DeviceLinkRequest(BaseModel):
    device_id: str
    device_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    points: int
    total_points_earned: int
    rank: str
    avatar_url: Optional[str]
    is_verified: bool
    created_at: str
    checkin_streak: Optional[int] = 0
    last_checkin: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


# ============== Endpoints ==============


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """Register a new community user"""
    async with get_db() as db:
        # Check if email already exists
        cursor = await db.execute(
            "SELECT id FROM community_users WHERE email = ?", (request.email,)
        )
        if await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check if username already exists
        cursor = await db.execute(
            "SELECT id FROM community_users WHERE username = ?", (request.username,)
        )
        if await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

        # Create user
        password_hash = hash_password(request.password)
        now = datetime.now().isoformat()

        await db.execute(
            """
            INSERT INTO community_users 
            (username, email, password_hash, points, total_points_earned, rank, created_at)
            VALUES (?, ?, ?, 5, 5, 'newcomer', ?)
        """,
            (request.username, request.email, password_hash, now),
        )
        await db.commit()

        # Get created user
        cursor = await db.execute(
            "SELECT * FROM community_users WHERE email = ?", (request.email,)
        )
        user = dict(await cursor.fetchone())

        # Log point transaction for registration bonus
        await db.execute(
            """
            INSERT INTO point_transactions (user_id, amount, reason, created_at)
            VALUES (?, 5, 'register_bonus', ?)
        """,
            (user["id"], now),
        )
        await db.commit()

        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            points=user["points"],
            total_points_earned=user["total_points_earned"],
            rank=user["rank"],
            avatar_url=user.get("avatar_url"),
            is_verified=bool(user.get("is_verified", 0)),
            created_at=user["created_at"],
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login and get access/refresh tokens"""
    async with get_db() as db:
        # Find user by email
        cursor = await db.execute(
            "SELECT * FROM community_users WHERE email = ?", (request.email,)
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        user = dict(row)

        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if user is active
        if not user.get("is_active", 1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
            )

        # Generate tokens
        tokens = generate_token_pair(user["id"], user["username"], user["rank"])

        # Store refresh token hash
        refresh_hash = hash_token(tokens["refresh_token"])
        expires_at = datetime.now().isoformat()  # Will be set properly by token

        await db.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, datetime('now', '+30 days'), datetime('now'))
        """,
            (user["id"], refresh_hash),
        )

        # Update last login
        await db.execute(
            "UPDATE community_users SET last_login = datetime('now') WHERE id = ?",
            (user["id"],),
        )
        await db.commit()

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                points=user["points"],
                total_points_earned=user["total_points_earned"],
                rank=user["rank"],
                avatar_url=user.get("avatar_url"),
                is_verified=bool(user.get("is_verified", 0)),
                created_at=user["created_at"],
            ),
        )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token"""
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = int(payload.get("sub"))
    token_hash = hash_token(request.refresh_token)

    async with get_db() as db:
        # Check if refresh token exists and is not revoked
        cursor = await db.execute(
            """
            SELECT * FROM refresh_tokens 
            WHERE user_id = ? AND token_hash = ? AND revoked = 0
            AND expires_at > datetime('now')
        """,
            (user_id, token_hash),
        )

        if not await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or expired",
            )

        # Get user info
        cursor = await db.execute(
            "SELECT id, username, rank FROM community_users WHERE id = ?", (user_id,)
        )
        user = dict(await cursor.fetchone())

        # Generate new tokens
        tokens = generate_token_pair(user["id"], user["username"], user["rank"])

        # Revoke old refresh token and create new one
        await db.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,)
        )

        new_refresh_hash = hash_token(tokens["refresh_token"])
        await db.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, datetime('now', '+30 days'), datetime('now'))
        """,
            (user_id, new_refresh_hash),
        )
        await db.commit()

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "expires_in": tokens["expires_in"],
        }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout - revoke all refresh tokens for user"""
    async with get_db() as db:
        await db.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?",
            (current_user["user_id"],),
        )
        await db.commit()

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM community_users WHERE id = ?", (current_user["user_id"],)
        )
        user = dict(await cursor.fetchone())

        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            points=user["points"],
            total_points_earned=user["total_points_earned"],
            rank=user["rank"],
            avatar_url=user.get("avatar_url"),
            is_verified=bool(user.get("is_verified", 0)),
            created_at=user["created_at"],
            checkin_streak=user.get("checkin_streak"),
            last_checkin=user.get("last_checkin"),
        )


@router.post("/device-link")
async def link_device(
    request: DeviceLinkRequest, current_user: dict = Depends(get_current_user)
):
    """Link a device to the user account"""
    async with get_db() as db:
        # Upsert device link
        await db.execute(
            """
            INSERT INTO user_devices (user_id, device_id, device_name, last_used)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, device_id) DO UPDATE SET 
                device_name = COALESCE(excluded.device_name, device_name),
                last_used = datetime('now')
        """,
            (current_user["user_id"], request.device_id, request.device_name),
        )
        await db.commit()

    return {"message": "Device linked successfully", "device_id": request.device_id}


@router.post("/checkin")
async def daily_checkin(current_user: dict = Depends(get_current_user)):
    """Daily check-in for bonus points"""
    async with get_db() as db:
        # Get user's last checkin
        cursor = await db.execute(
            "SELECT last_checkin, checkin_streak FROM community_users WHERE id = ?",
            (current_user["user_id"],),
        )
        user = dict(await cursor.fetchone())

        now = datetime.now()
        last_checkin = user.get("last_checkin")
        streak = user.get("checkin_streak", 0) or 0

        # Check if already checked in today
        if last_checkin:
            last_dt = datetime.fromisoformat(last_checkin)
            if last_dt.date() == now.date():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Already checked in today",
                )

            # Check if streak continues (yesterday)
            days_diff = (now.date() - last_dt.date()).days
            if days_diff == 1:
                streak += 1
            else:
                streak = 1  # Reset streak
        else:
            streak = 1

        # Calculate points based on streak (sync với frontend UI)
        # 1-6 days: +2 pts
        # Day 7 (streak=7): +5 pts bonus
        # Days 8-29: +3 pts
        # Day 30 (streak=30): +15 pts bonus
        if streak == 7:
            points = 5
        elif streak == 30:
            points = 15
        elif streak > 7:
            points = 3
        else:
            points = 2

        # Update user
        await db.execute(
            """
            UPDATE community_users SET 
                last_checkin = ?,
                checkin_streak = ?,
                points = points + ?,
                total_points_earned = total_points_earned + ?
            WHERE id = ?
        """,
            (
                now.isoformat(),
                streak,
                points,
                points,
                current_user["user_id"],
            ),
        )

        # Log transaction
        await db.execute(
            """
            INSERT INTO point_transactions (user_id, amount, reason, created_at)
            VALUES (?, ?, 'daily_checkin', ?)
        """,
            (current_user["user_id"], points, now.isoformat()),
        )

        # Update rank if needed
        cursor = await db.execute(
            "SELECT total_points_earned FROM community_users WHERE id = ?",
            (current_user["user_id"],),
        )
        row = dict(await cursor.fetchone())
        new_rank = calculate_rank(row["total_points_earned"])

        await db.execute(
            "UPDATE community_users SET rank = ? WHERE id = ?",
            (new_rank, current_user["user_id"]),
        )
        await db.commit()

        return {
            "message": "Check-in successful",
            "points_earned": points,
            "streak": streak,
            "new_streak": streak,  # For frontend to update display
        }
