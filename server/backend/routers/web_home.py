from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, HTMLResponse
import os
import time
from pathlib import Path

router = APIRouter()

# Use absolute path relative to project root
# Assuming this file is at backend/routers/web_home.py
# Standard project structure:
# root/
#   backend/
#     routers/
#       web_home.py
#   web/
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
WEB_DIR = PROJECT_ROOT / "web"


def get_file_content_with_version(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8")
    version = str(int(time.time()))
    return content.replace("{{version}}", version)


@router.get("/")
async def home():
    file_path = WEB_DIR / "index.html"
    if not file_path.exists():
        return {"error": "Web files not found"}

    # Render with version
    content = get_file_content_with_version(file_path)
    return HTMLResponse(content=content)


@router.get("/style.css")
async def style():
    response = FileResponse(WEB_DIR / "style.css")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@router.get("/script.js")
async def script():
    response = FileResponse(WEB_DIR / "script.js")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@router.get("/favicon.ico")
async def favicon():
    file_path = PROJECT_ROOT / "favicon.ico"
    if file_path.exists():
        return FileResponse(file_path, media_type="image/x-icon")
    return Response(status_code=404)


# NOTE: Community routes moved to backend/routers/community_web.py


@router.get("/{filename}")
async def get_web_resource(filename: str):
    # Allow serving other assets from web dir if needed
    file_path = WEB_DIR / filename

    # Check web dir first
    if file_path.exists() and file_path.is_file():
        # If HTML, render with version
        if filename.endswith(".html"):
            content = get_file_content_with_version(file_path)
            return HTMLResponse(content=content)

        # For XML files (sitemap.xml)
        if filename.endswith(".xml"):
            return FileResponse(file_path, media_type="application/xml")

        # For text files (robots.txt)
        if filename.endswith(".txt"):
            return FileResponse(file_path, media_type="text/plain")

        # For other files
        response = FileResponse(file_path)
        # Disable cache for JS/CSS files during dev
        if filename.endswith((".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    # Check project root fallback (e.g. for robots.txt, sitemap.xml)
    root_path = PROJECT_ROOT / filename
    if root_path.exists() and root_path.is_file():
        if filename.endswith(".xml"):
            return FileResponse(root_path, media_type="application/xml")
        if filename.endswith(".txt"):
            return FileResponse(root_path, media_type="text/plain")
        return FileResponse(root_path)

    # Default 404
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="File not found")
