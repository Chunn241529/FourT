"""
YouTube Search Router
Provides API endpoint for searching YouTube videos using yt-dlp
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import subprocess
import sys
import json
import re
import os

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

# Get path to loading page
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(os.path.dirname(_current_dir))
_loading_page = os.path.join(_root_dir, "web", "video_loading.html")


@router.get("/player")
async def video_player_page(q: str = Query(..., description="Search query")):
    """
    Serve the video loading page that searches and redirects to YouTube video
    """
    if os.path.exists(_loading_page):
        return FileResponse(_loading_page, media_type="text/html")
    else:
        # Fallback: redirect to YouTube search
        from fastapi.responses import RedirectResponse
        import urllib.parse

        return RedirectResponse(
            url=f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
        )


def clean_search_query(query: str) -> str:
    """Clean and normalize search query"""
    # Remove special characters that may cause issues
    query = re.sub(r'[/\\|<>:"]', " ", query)
    # Remove extra whitespace
    query = " ".join(query.split())
    return query.strip()


@router.get("/search")
async def search_youtube(
    q: str = Query(..., description="Search query"),
    limit: int = Query(1, ge=1, le=5, description="Number of results to return"),
):
    """
    Search YouTube and return video information

    Uses yt-dlp on server side to get video URLs
    Returns first video by default (for auto-play)
    """
    try:
        # Clean the query
        clean_query = clean_search_query(q)
        if not clean_query:
            raise HTTPException(status_code=400, detail="Empty query after cleaning")

        print(f"[YouTubeSearch] Original query: {q}")
        print(f"[YouTubeSearch] Cleaned query: {clean_query}")

        # Use yt-dlp to search (without --flat-playlist which can cause issues)
        search_query = f"ytsearch{limit}:{clean_query}"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                search_query,
                "--dump-json",
                "--no-download",
                "--quiet",
                "--no-warnings",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0
            ),
        )

        print(f"[YouTubeSearch] yt-dlp returncode: {result.returncode}")
        if result.stderr:
            print(f"[YouTubeSearch] yt-dlp stderr: {result.stderr[:500]}")

        # If failed, try with simpler query (first few words only)
        if result.returncode != 0 or not result.stdout.strip():
            words = clean_query.split()[:3]  # First 3 words
            simple_query = " ".join(words)
            if simple_query:
                print(f"[YouTubeSearch] Retrying with simple query: {simple_query}")
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "yt_dlp",
                        f"ytsearch1:{simple_query}",
                        "--dump-json",
                        "--no-download",
                        "--quiet",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                        else 0
                    ),
                )

        videos = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    video_info = json.loads(line)
                    video_id = video_info.get("id", "")
                    if video_id:
                        videos.append(
                            {
                                "id": video_id,
                                "title": video_info.get("title", ""),
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "thumbnail": video_info.get("thumbnail", ""),
                                "duration": video_info.get("duration", 0),
                                "channel": video_info.get("channel", ""),
                            }
                        )
                except json.JSONDecodeError:
                    continue

        if not videos:
            print(f"[YouTubeSearch] No videos found for query: {clean_query}")
            raise HTTPException(status_code=404, detail="No videos found")

        return {
            "success": True,
            "query": q,
            "count": len(videos),
            "videos": videos,
            "first_video_url": videos[0]["url"] + "&autoplay=1" if videos else None,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Search timeout")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="yt-dlp not installed on server")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[YouTubeSearch] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
