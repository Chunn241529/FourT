"""
Community Router for FourT MIDI Platform
Handles MIDI CRUD, ratings, comments, and downloads
"""

import os
import shutil
from datetime import datetime
from typing import Optional, List
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    UploadFile,
    File,
    Form,
    Query,
)
from pydantic import BaseModel

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_user_optional
from services.auth_service import get_download_cost
from services.points_service import (
    add_points,
    deduct_points,
    can_earn_upload_points,
    can_earn_comment_points,
    check_download_milestones,
    check_rating_milestones,
    get_user_point_history,
    get_leaderboard,
    POINTS,
)

router = APIRouter(prefix="/api/community", tags=["community"])

# MIDI upload directory
MIDI_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "midi_uploads"
)
os.makedirs(MIDI_UPLOAD_DIR, exist_ok=True)


# ============== Pydantic Models ==============


class MidiResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    uploader_id: int
    uploader_username: Optional[str]
    file_size: int
    duration_seconds: Optional[float]
    midi_type: str
    download_count: int
    avg_rating: float
    rating_count: int
    status: str
    tags: Optional[str]
    created_at: str


class MidiListResponse(BaseModel):
    items: List[MidiResponse]
    total: int
    page: int
    page_size: int


class CommentRequest(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    content: str
    likes: int
    created_at: str


class RatingRequest(BaseModel):
    stars: int


# ============== MIDI Endpoints ==============


@router.get("/midi", response_model=MidiListResponse)
async def list_midi(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", pattern="^(newest|popular|rating)$"),
    search: Optional[str] = None,
    midi_type: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """List MIDI files with pagination and filtering"""
    async with get_db() as db:
        # Build query
        where_clauses = ["m.status = 'approved'"]
        params = []

        if search:
            where_clauses.append("(m.title LIKE ? OR m.tags LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        if midi_type:
            where_clauses.append("m.midi_type = ?")
            params.append(midi_type)

        where_sql = " AND ".join(where_clauses)

        # Sort
        sort_sql = {
            "newest": "m.created_at DESC",
            "popular": "m.download_count DESC",
            "rating": "m.avg_rating DESC",
        }.get(sort, "m.created_at DESC")

        # Count total
        cursor = await db.execute(
            f"""
            SELECT COUNT(*) as total FROM midi_files m WHERE {where_sql}
        """,
            params,
        )
        total = (await cursor.fetchone())["total"]

        # Get items with uploader info
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""
            SELECT m.*, u.username as uploader_username
            FROM midi_files m
            LEFT JOIN community_users u ON m.uploader_id = u.id
            WHERE {where_sql}
            ORDER BY {sort_sql}
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        )

        rows = await cursor.fetchall()
        items = [MidiResponse(**dict(row)) for row in rows]

        return MidiListResponse(
            items=items, total=total, page=page, page_size=page_size
        )


@router.get("/midi/pending")
async def get_pending_midi():
    """Get all pending MIDI files for admin review"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT m.*, u.username as uploader_username
            FROM midi_files m
            LEFT JOIN community_users u ON m.uploader_id = u.id
            ORDER BY m.created_at DESC
        """
        )
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]


@router.get("/midi/{midi_id}", response_model=MidiResponse)
async def get_midi(midi_id: int):
    """Get MIDI file details"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT m.*, u.username as uploader_username
            FROM midi_files m
            LEFT JOIN community_users u ON m.uploader_id = u.id
            WHERE m.id = ?
        """,
            (midi_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="MIDI not found")

        return MidiResponse(**dict(row))


@router.post("/midi")
async def upload_midi(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    midi_type: str = Form("normal"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a new MIDI file"""
    # Daily upload limit: 3 MIDI files per user per day
    DAILY_UPLOAD_LIMIT = 3

    async with get_db() as db:
        # Check today's upload count
        today_start = (
            datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
        )
        cursor = await db.execute(
            """
            SELECT COUNT(*) as count FROM midi_files 
            WHERE uploader_id = ? AND created_at >= ?
        """,
            (current_user["user_id"], today_start),
        )
        row = await cursor.fetchone()
        today_uploads = row["count"] if row else 0

        if today_uploads >= DAILY_UPLOAD_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"Bạn đã đạt giới hạn upload {DAILY_UPLOAD_LIMIT} bài/ngày. Vui lòng quay lại ngày mai!",
            )

    # Validate file
    if not file.filename.endswith(".mid") and not file.filename.endswith(".midi"):
        raise HTTPException(
            status_code=400, detail="File must be a MIDI file (.mid or .midi)"
        )

    # Check file size (max 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{current_user['user_id']}_{timestamp}_{file.filename}"
    file_path = os.path.join(MIDI_UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Get MIDI duration (optional, requires pretty_midi)
    duration = None
    try:
        import pretty_midi

        pm = pretty_midi.PrettyMIDI(file_path)
        duration = pm.get_end_time()
    except:
        pass

    # Save to database
    async with get_db() as db:
        now = datetime.now().isoformat()
        await db.execute(
            """
            INSERT INTO midi_files 
            (title, description, uploader_id, file_path, file_size, duration_seconds, midi_type, tags, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
            (
                title,
                description,
                current_user["user_id"],
                safe_filename,
                len(content),
                duration,
                midi_type,
                tags,
                now,
            ),
        )
        await db.commit()

        # Get inserted ID
        cursor = await db.execute("SELECT last_insert_rowid()")
        midi_id = (await cursor.fetchone())[0]

    return {
        "message": "MIDI uploaded successfully, pending review",
        "midi_id": midi_id,
        "status": "pending",
    }


@router.post("/midi/{midi_id}/download")
async def download_midi(midi_id: int, current_user: dict = Depends(get_current_user)):
    """Download a MIDI file (deducts points)"""
    async with get_db() as db:
        # Check if already downloaded
        cursor = await db.execute(
            """
            SELECT id FROM midi_downloads 
            WHERE user_id = ? AND midi_id = ?
        """,
            (current_user["user_id"], midi_id),
        )

        if await cursor.fetchone():
            # Already downloaded, return file info without charging
            cursor = await db.execute(
                "SELECT file_path FROM midi_files WHERE id = ?", (midi_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "message": "Already downloaded (free re-download)",
                    "file_path": f"/community/midi/{midi_id}/file",
                }

        # Get MIDI info
        cursor = await db.execute(
            """
            SELECT m.*, u.id as owner_id FROM midi_files m 
            LEFT JOIN community_users u ON m.uploader_id = u.id
            WHERE m.id = ? AND m.status = 'approved'
        """,
            (midi_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail="MIDI not found or not approved"
            )

        midi = dict(row)

        # Check if user is the uploader (free download)
        if midi["uploader_id"] == current_user["user_id"]:
            return {
                "message": "Free download (your own MIDI)",
                "file_path": f"/community/midi/{midi_id}/file",
            }

        # Calculate cost
        cost = get_download_cost(current_user["rank"], midi["midi_type"])

        # Deduct points
        success, message = await deduct_points(
            current_user["user_id"], cost, "download_midi", midi_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Record download
        now = datetime.now().isoformat()
        await db.execute(
            """
            INSERT INTO midi_downloads (user_id, midi_id, points_spent, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (current_user["user_id"], midi_id, cost, now),
        )

        # Increment download count
        await db.execute(
            "UPDATE midi_files SET download_count = download_count + 1 WHERE id = ?",
            (midi_id,),
        )
        await db.commit()

        # Award points to uploader (owner gets the download cost)
        if cost > 0:
            await add_points(midi["uploader_id"], cost, "download_received", midi_id)

        # Check milestones for uploader
        await check_download_milestones(midi_id, midi["uploader_id"])

        return {
            "message": f"Download successful ({cost} points spent)",
            "file_path": f"/community/midi/{midi_id}/file",
            "points_spent": cost,
        }


@router.get("/midi/{midi_id}/file")
async def get_midi_file(midi_id: int, current_user: dict = Depends(get_current_user)):
    """Get the actual MIDI file (only if downloaded or owned)"""
    from fastapi.responses import FileResponse

    async with get_db() as db:
        # Check access
        cursor = await db.execute(
            """
            SELECT m.file_path, m.title, m.uploader_id
            FROM midi_files m
            WHERE m.id = ?
        """,
            (midi_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="MIDI not found")

        midi = dict(row)

        # Check if user has access
        if midi["uploader_id"] != current_user["user_id"]:
            cursor = await db.execute(
                """
                SELECT id FROM midi_downloads 
                WHERE user_id = ? AND midi_id = ?
            """,
                (current_user["user_id"], midi_id),
            )

            if not await cursor.fetchone():
                raise HTTPException(
                    status_code=403, detail="You need to download this MIDI first"
                )

        file_path = os.path.join(MIDI_UPLOAD_DIR, midi["file_path"])
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")

        return FileResponse(
            file_path, filename=f"{midi['title']}.mid", media_type="audio/midi"
        )


@router.get("/midi/{midi_id}/preview")
async def preview_midi(midi_id: int):
    """
    Preview/stream MIDI file for web player (no login required).
    Only approved MIDI files can be previewed.
    """
    from fastapi.responses import FileResponse

    async with get_db() as db:
        # Get approved MIDI file
        cursor = await db.execute(
            """
            SELECT m.file_path, m.title
            FROM midi_files m
            WHERE m.id = ? AND m.status = 'approved'
        """,
            (midi_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail="MIDI not found or not approved"
            )

        midi = dict(row)
        file_path = os.path.join(MIDI_UPLOAD_DIR, midi["file_path"])

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")

        # Return file with CORS headers for web player
        response = FileResponse(
            file_path, filename=f"{midi['title']}.mid", media_type="audio/midi"
        )
        # Allow cross-origin access for web MIDI player
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response


# ============== Rating Endpoints ==============


@router.get("/midi/{midi_id}/my-rating")
async def get_my_rating(midi_id: int, current_user: dict = Depends(get_current_user)):
    """Get current user's rating for a MIDI file"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT stars FROM midi_ratings WHERE user_id = ? AND midi_id = ?",
            (current_user["user_id"], midi_id),
        )
        row = await cursor.fetchone()

        if row:
            return {"stars": row["stars"]}
        return {"stars": 0}


@router.post("/midi/{midi_id}/rate")
async def rate_midi(
    midi_id: int, request: RatingRequest, current_user: dict = Depends(get_current_user)
):
    """Rate a MIDI file (1-5 stars)"""
    if request.stars < 1 or request.stars > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5 stars")

    async with get_db() as db:
        # Check if MIDI exists
        cursor = await db.execute(
            "SELECT uploader_id FROM midi_files WHERE id = ? AND status = 'approved'",
            (midi_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="MIDI not found")

        uploader_id = row["uploader_id"]

        # Can't rate your own MIDI
        if uploader_id == current_user["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot rate your own MIDI")

        # Upsert rating
        now = datetime.now().isoformat()
        await db.execute(
            """
            INSERT INTO midi_ratings (user_id, midi_id, stars, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, midi_id) DO UPDATE SET stars = ?, created_at = ?
        """,
            (current_user["user_id"], midi_id, request.stars, now, request.stars, now),
        )

        # Update average rating
        cursor = await db.execute(
            """
            SELECT AVG(stars) as avg, COUNT(*) as count FROM midi_ratings WHERE midi_id = ?
        """,
            (midi_id,),
        )
        stats = await cursor.fetchone()

        await db.execute(
            """
            UPDATE midi_files SET avg_rating = ?, rating_count = ? WHERE id = ?
        """,
            (stats["avg"], stats["count"], midi_id),
        )
        await db.commit()

        # Check rating milestones for uploader
        if request.stars >= 4:
            await check_rating_milestones(midi_id, uploader_id)

        return {
            "message": "Rating saved",
            "new_avg": stats["avg"],
            "total_ratings": stats["count"],
        }


# ============== Comment Endpoints ==============


@router.get("/midi/{midi_id}/comments", response_model=List[CommentResponse])
async def get_comments(midi_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get comments for a MIDI file"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.*, u.username
            FROM midi_comments c
            JOIN community_users u ON c.user_id = u.id
            WHERE c.midi_id = ?
            ORDER BY c.created_at DESC
            LIMIT ?
        """,
            (midi_id, limit),
        )
        rows = await cursor.fetchall()

        return [CommentResponse(**dict(row)) for row in rows]


@router.post("/midi/{midi_id}/comments", response_model=CommentResponse)
async def add_comment(
    midi_id: int,
    request: CommentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a MIDI file"""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    # Check can earn points
    can_earn, msg = await can_earn_comment_points(current_user["user_id"])

    async with get_db() as db:
        # Check MIDI exists
        cursor = await db.execute(
            "SELECT id FROM midi_files WHERE id = ? AND status = 'approved'", (midi_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="MIDI not found")

        # Insert comment
        now = datetime.now().isoformat()
        await db.execute(
            """
            INSERT INTO midi_comments (user_id, midi_id, content, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (current_user["user_id"], midi_id, request.content.strip(), now),
        )
        await db.commit()

        cursor = await db.execute("SELECT last_insert_rowid()")
        comment_id = (await cursor.fetchone())[0]

        # Award points if eligible
        if can_earn:
            await add_points(
                current_user["user_id"], POINTS["comment"], "comment", comment_id
            )

        return CommentResponse(
            id=comment_id,
            user_id=current_user["user_id"],
            username=current_user["username"],
            content=request.content.strip(),
            likes=0,
            created_at=now,
        )


# ============== Leaderboard & Points ==============


@router.get("/leaderboard")
async def leaderboard(limit: int = Query(20, ge=1, le=100)):
    """Get community leaderboard"""
    return await get_leaderboard(limit)


@router.get("/points/history")
async def points_history(
    limit: int = Query(50, ge=1, le=200), current_user: dict = Depends(get_current_user)
):
    """Get current user's point transaction history"""
    return await get_user_point_history(current_user["user_id"], limit)


# ============== My MIDI Endpoints ==============


@router.get("/my/midi")
async def my_midi(
    current_user: dict = Depends(get_current_user), status: Optional[str] = None
):
    """Get current user's uploaded MIDI files"""
    async with get_db() as db:
        query = "SELECT * FROM midi_files WHERE uploader_id = ?"
        params = [current_user["user_id"]]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]


@router.get("/my/downloads")
async def my_downloads(current_user: dict = Depends(get_current_user)):
    """Get current user's downloaded MIDI files"""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT m.*, d.points_spent, d.created_at as downloaded_at, u.username as uploader_username
            FROM midi_downloads d
            JOIN midi_files m ON d.midi_id = m.id
            LEFT JOIN community_users u ON m.uploader_id = u.id
            WHERE d.user_id = ?
            ORDER BY d.created_at DESC
        """,
            (current_user["user_id"],),
        )
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]


# ============== Admin Review Endpoints ==============


class ReviewRequest(BaseModel):
    status: str  # "approved" or "rejected"


@router.post("/midi/{midi_id}/review")
async def review_midi(midi_id: int, request: ReviewRequest):
    """Approve or reject a MIDI file (admin action)"""
    if request.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400, detail="Status must be 'approved' or 'rejected'"
        )

    async with get_db() as db:
        # Get MIDI info
        cursor = await db.execute(
            "SELECT id, uploader_id, status FROM midi_files WHERE id = ?",
            (midi_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="MIDI not found")

        midi = dict(row)

        # Update status
        await db.execute(
            "UPDATE midi_files SET status = ? WHERE id = ?",
            (request.status, midi_id),
        )
        await db.commit()

        # Award points to uploader if approved
        if request.status == "approved" and midi["status"] == "pending":
            can_earn, msg = await can_earn_upload_points(midi["uploader_id"])
            if can_earn:
                await add_points(
                    midi["uploader_id"],
                    POINTS["upload_approved"],
                    "upload_approved",
                    midi_id,
                )

        return {
            "message": f"MIDI {request.status}",
            "midi_id": midi_id,
            "status": request.status,
        }
