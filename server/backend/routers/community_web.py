"""
Community Web Router - Serves MIDI Community web pages
Designed for subdomain: midi.fourt.io.vn
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import time

router = APIRouter(tags=["community-web"])

# Paths
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent  # server/
WEB_DIR = PROJECT_ROOT / "web"
COMMUNITY_DIR = WEB_DIR / "community"


def get_file_content_with_version(file_path: Path) -> str:
    """Read file and inject version for cache busting"""
    content = file_path.read_text(encoding="utf-8")
    version = str(int(time.time()))
    return content.replace("{{version}}", version)


# ============== Community Pages ==============


@router.get("/")
@router.get("")
async def community_index():
    """Community homepage - MIDI browse"""
    file_path = COMMUNITY_DIR / "index.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Community files not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


@router.get("/leaderboard")
@router.get("/leaderboard.html")
async def community_leaderboard():
    """Leaderboard page"""
    file_path = COMMUNITY_DIR / "leaderboard.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Leaderboard page not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


@router.get("/upload")
@router.get("/upload.html")
async def community_upload():
    """Upload page"""
    file_path = COMMUNITY_DIR / "upload.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Upload page not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


# ============== User Pages ==============


@router.get("/profile")
@router.get("/profile.html")
async def community_profile():
    """User profile page"""
    file_path = COMMUNITY_DIR / "profile.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Profile page not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


@router.get("/my-midi")
@router.get("/my-midi.html")
async def community_my_midi():
    """User's uploaded MIDI page"""
    file_path = COMMUNITY_DIR / "my-midi.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="My MIDI page not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


@router.get("/downloads")
@router.get("/downloads.html")
async def community_downloads():
    """User's download history page"""
    file_path = COMMUNITY_DIR / "downloads.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Downloads page not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


@router.get("/checkin")
@router.get("/checkin.html")
async def community_checkin():
    """Daily check-in page"""
    file_path = COMMUNITY_DIR / "checkin.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Check-in page not found")
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


# ============== Static Assets ==============


@router.get("/community.css")
async def community_css():
    """Community styles"""
    file_path = COMMUNITY_DIR / "community.css"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="CSS not found")
    response = FileResponse(file_path, media_type="text/css")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@router.get("/app.js")
async def community_js():
    """Community JavaScript"""
    file_path = COMMUNITY_DIR / "app.js"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="JS not found")
    response = FileResponse(file_path, media_type="application/javascript")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@router.get("/{filename:path}")
async def community_static(filename: str):
    """Serve other static files from community directory"""
    file_path = COMMUNITY_DIR / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    # HTML files - inject version
    if filename.endswith(".html"):
        content = get_file_content_with_version(file_path)
        return HTMLResponse(content=content)

    # CSS/JS - no cache
    response = FileResponse(file_path)
    if filename.endswith((".js", ".css")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return response
