"""
Points Service for FourT Community
Handles point transactions, anti-abuse logic, and rank updates
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging

from backend.database import get_db
from services.auth_service import calculate_rank

logger = logging.getLogger(__name__)

# ============== Constants ==============

# Daily limits for earning points
MAX_UPLOAD_POINTS_PER_DAY = 15  # 3 uploads x 5 points
MAX_COMMENT_POINTS_PER_DAY = 3  # 3 comments x 1 point
UPLOAD_COOLDOWN_MINUTES = 30
COMMENT_COOLDOWN_MINUTES = 5

# Point values
POINTS = {
    "register_bonus": 5,
    "daily_checkin": 1,
    "streak_bonus": 3,  # Every 7 days
    "upload_approved": 5,
    "comment": 1,
    "comment_liked": 1,  # Per 5 likes
    "rating_received": 1,  # Per 3 ratings
    "milestone_50_downloads": 10,
    "milestone_100_downloads": 20,
    "midi_of_week": 30,
    "fulfill_request": 8,
    "referral": 5,
    "first_upload_badge": 3,
    "century_badge": 15,
    "popular_badge": 20,
    "top_creator_badge": 50,
    "community_star_badge": 30,
}

# Download costs by MIDI type
DOWNLOAD_COSTS = {
    "normal": 3,
    "premium": 8,
    "exclusive": 15,
}


# ============== Point Transaction Functions ==============


async def add_points(
    user_id: int, amount: int, reason: str, reference_id: Optional[int] = None
) -> bool:
    """Add points to user and log transaction"""
    async with get_db() as db:
        try:
            now = datetime.now().isoformat()

            # Update user points
            await db.execute(
                """
                UPDATE community_users SET 
                    points = points + ?,
                    total_points_earned = total_points_earned + ?
                WHERE id = ?
            """,
                (amount, amount, user_id),
            )

            # Log transaction
            await db.execute(
                """
                INSERT INTO point_transactions (user_id, amount, reason, reference_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, amount, reason, reference_id, now),
            )

            # Update rank
            cursor = await db.execute(
                "SELECT total_points_earned FROM community_users WHERE id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row:
                new_rank = calculate_rank(row["total_points_earned"])
                await db.execute(
                    "UPDATE community_users SET rank = ? WHERE id = ?",
                    (new_rank, user_id),
                )

            await db.commit()
            logger.info(
                f"[Points] Added {amount} points to user {user_id} for {reason}"
            )
            return True
        except Exception as e:
            logger.error(f"[Points] Error adding points: {e}")
            return False


async def deduct_points(
    user_id: int, amount: int, reason: str, reference_id: Optional[int] = None
) -> Tuple[bool, str]:
    """Deduct points from user. Returns (success, message)"""
    async with get_db() as db:
        try:
            # Check if user has enough points
            cursor = await db.execute(
                "SELECT points FROM community_users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False, "User not found"

            if row["points"] < amount:
                return (
                    False,
                    f"Insufficient points. Need {amount}, have {row['points']}",
                )

            now = datetime.now().isoformat()

            # Deduct points (don't affect total_points_earned)
            await db.execute(
                """
                UPDATE community_users SET points = points - ? WHERE id = ?
            """,
                (amount, user_id),
            )

            # Log transaction (negative amount)
            await db.execute(
                """
                INSERT INTO point_transactions (user_id, amount, reason, reference_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, -amount, reason, reference_id, now),
            )

            await db.commit()
            logger.info(
                f"[Points] Deducted {amount} points from user {user_id} for {reason}"
            )
            return True, "Success"
        except Exception as e:
            logger.error(f"[Points] Error deducting points: {e}")
            return False, str(e)


async def get_points_earned_today(user_id: int, reason: str) -> int:
    """Get total points earned today for a specific reason"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM point_transactions
            WHERE user_id = ? 
            AND reason = ?
            AND date(created_at) = date('now')
            AND amount > 0
        """,
            (user_id, reason),
        )
        row = await cursor.fetchone()
        return row["total"] if row else 0


async def get_last_action_time(user_id: int, reason: str) -> Optional[datetime]:
    """Get the timestamp of user's last action for cooldown checking"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT created_at FROM point_transactions
            WHERE user_id = ? AND reason = ?
            ORDER BY created_at DESC LIMIT 1
        """,
            (user_id, reason),
        )
        row = await cursor.fetchone()
        if row:
            return datetime.fromisoformat(row["created_at"])
        return None


# ============== Anti-Abuse Checks ==============


async def can_earn_upload_points(user_id: int) -> Tuple[bool, str]:
    """Check if user can earn points from upload (cooldown + daily limit)"""
    # Check daily limit
    earned_today = await get_points_earned_today(user_id, "upload_approved")
    if earned_today >= MAX_UPLOAD_POINTS_PER_DAY:
        return False, "Daily upload point limit reached (max 3 uploads)"

    # Check cooldown
    last_upload = await get_last_action_time(user_id, "upload_approved")
    if last_upload:
        cooldown_end = last_upload + timedelta(minutes=UPLOAD_COOLDOWN_MINUTES)
        if datetime.now() < cooldown_end:
            remaining = (cooldown_end - datetime.now()).seconds // 60
            return False, f"Upload cooldown: {remaining} minutes remaining"

    return True, "OK"


async def can_earn_comment_points(user_id: int) -> Tuple[bool, str]:
    """Check if user can earn points from comment"""
    # Check daily limit
    earned_today = await get_points_earned_today(user_id, "comment")
    if earned_today >= MAX_COMMENT_POINTS_PER_DAY:
        return False, "Daily comment point limit reached (max 3 comments)"

    # Check cooldown
    last_comment = await get_last_action_time(user_id, "comment")
    if last_comment:
        cooldown_end = last_comment + timedelta(minutes=COMMENT_COOLDOWN_MINUTES)
        if datetime.now() < cooldown_end:
            remaining = (cooldown_end - datetime.now()).seconds // 60
            return False, f"Comment cooldown: {remaining} minutes remaining"

    return True, "OK"


# ============== Milestone Checks ==============


async def check_download_milestones(midi_id: int, uploader_id: int) -> List[str]:
    """Check and award download milestones for a MIDI file"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT download_count FROM midi_files WHERE id = ?", (midi_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return []

        download_count = row["download_count"]
        awarded = []

        # Check 50 downloads milestone
        if download_count == 50:
            await add_points(
                uploader_id,
                POINTS["milestone_50_downloads"],
                "milestone_50_downloads",
                midi_id,
            )
            awarded.append("50 downloads")

        # Check 100 downloads milestone
        elif download_count == 100:
            await add_points(
                uploader_id,
                POINTS["milestone_100_downloads"],
                "milestone_100_downloads",
                midi_id,
            )
            awarded.append("100 downloads")

        return awarded


async def check_rating_milestones(midi_id: int, uploader_id: int) -> bool:
    """Check if uploader should get points for ratings received"""
    async with get_db() as db:
        # Count ratings with 4-5 stars since last point
        cursor = await db.execute(
            """
            SELECT COUNT(*) as count FROM midi_ratings 
            WHERE midi_id = ? AND stars >= 4
        """,
            (midi_id,),
        )
        row = await cursor.fetchone()

        if row and row["count"] > 0 and row["count"] % 3 == 0:
            # Every 3 good ratings = 1 point
            await add_points(
                uploader_id, POINTS["rating_received"], "rating_received", midi_id
            )
            return True

        return False


# ============== User Stats ==============


async def get_user_point_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get user's point transaction history"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM point_transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    """Get community leaderboard by total points earned"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, username, avatar_url, total_points_earned, rank
            FROM community_users
            WHERE is_active = 1
            ORDER BY total_points_earned DESC
            LIMIT ?
        """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
