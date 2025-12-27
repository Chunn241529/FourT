"""
Download stats router - Track download counts persistently
"""
from fastapi import APIRouter
from pathlib import Path
import json
from datetime import datetime

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Data file path
CURRENT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = CURRENT_DIR / "data"
STATS_FILE = DATA_DIR / "download_stats.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


def load_stats() -> dict:
    """Load download stats from file"""
    if not STATS_FILE.exists():
        return {"total_downloads": 0, "assets": {}}
    try:
        return json.loads(STATS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {"total_downloads": 0, "assets": {}}


def save_stats(stats: dict):
    """Save download stats to file"""
    try:
        STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"[Stats] Error saving stats: {e}")


@router.get("/downloads")
async def get_download_stats():
    """
    Get current download statistics
    Returns total download count and per-asset counts
    """
    stats = load_stats()
    return {
        "total_downloads": stats.get("total_downloads", 0),
        "assets": stats.get("assets", {})
    }


@router.post("/downloads/increment")
async def increment_download(asset_name: str = "FourT_Setup.exe"):
    """
    Increment download count for an asset
    Called when user clicks download button
    """
    stats = load_stats()
    
    # Increment total
    stats["total_downloads"] = stats.get("total_downloads", 0) + 1
    
    # Increment per-asset
    if "assets" not in stats:
        stats["assets"] = {}
    
    if asset_name not in stats["assets"]:
        stats["assets"][asset_name] = {
            "count": 0,
            "first_download": datetime.now().isoformat(),
            "last_download": None
        }
    
    stats["assets"][asset_name]["count"] += 1
    stats["assets"][asset_name]["last_download"] = datetime.now().isoformat()
    
    save_stats(stats)
    
    return {
        "success": True,
        "total_downloads": stats["total_downloads"],
        "asset_count": stats["assets"][asset_name]["count"]
    }


@router.post("/downloads/set")
async def set_download_count(total: int = 0):
    """
    Set total download count (admin only - for initial setup)
    """
    stats = load_stats()
    stats["total_downloads"] = total
    save_stats(stats)
    
    return {
        "success": True,
        "total_downloads": stats["total_downloads"]
    }
