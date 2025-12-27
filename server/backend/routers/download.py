"""
Download router for serving build artifacts
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
import os
from pathlib import Path
from datetime import datetime
from backend.database import increment_download_count

router = APIRouter()

# Directory paths - server/ is CURRENT_DIR, client/ is PROJECT_ROOT/client
CURRENT_DIR = Path(__file__).parent.parent.parent  # server/
PROJECT_ROOT = CURRENT_DIR.parent  # FourT/
CLIENT_DIR = PROJECT_ROOT / "client"

DIST_DIR = CLIENT_DIR / "dist"
FAVICON_PATH = CLIENT_DIR / "favicon.ico"
UPDATE_INFO_FILE = CLIENT_DIR / "update_info.json"


def get_app_version() -> str:
    """Read version from update_info.json (the built version)"""
    try:
        if UPDATE_INFO_FILE.exists():
            import json

            data = json.loads(UPDATE_INFO_FILE.read_text(encoding="utf-8"))
            return data.get("version", "1.0.0")
    except Exception:
        pass
    return "1.0.0"


def get_download_page_html(
    request: Request, file_size: str, last_modified: str, version: str
) -> str:
    """Generate beautiful download page HTML from template"""
    base_url = str(request.base_url).rstrip("/")

    # Path to the template file
    template_path = CURRENT_DIR / "web" / "download.html"

    if not template_path.exists():
        # Fallback if template is missing (should not happen in dev)
        return """<html><body>Error: Template not found</body></html>"""

    html_content = template_path.read_text(encoding="utf-8")

    # Replace placeholders
    html_content = html_content.replace("{{base_url}}", base_url)
    html_content = html_content.replace("{{version}}", version)
    html_content = html_content.replace("{{file_size}}", file_size)
    html_content = html_content.replace("{{last_modified}}", last_modified)

    return html_content


@router.get("/installer")
async def download_installer_page(request: Request):
    """
    Display beautiful download page for FourT Helper installer
    """
    # Get specific version-tagged installer file path
    version = get_app_version()
    installer_filename = f"FourT_Setup_v{version}.exe"
    releases_dir = CLIENT_DIR / "releases"
    installer_path = releases_dir / version / installer_filename

    # Logic to handle missing installer gracefully (optional: show mock data for dev)
    file_size_display = "0 MB"
    last_modified_display = datetime.now().strftime("%d/%m/%Y")

    if installer_path.exists():
        # Get file info
        file_stat = installer_path.stat()
        file_size_mb = file_stat.st_size / (1024 * 1024)
        file_size_display = f"{file_size_mb:.1f} MB"
        last_modified_display = datetime.fromtimestamp(file_stat.st_mtime).strftime(
            "%d/%m/%Y"
        )

    return HTMLResponse(
        content=get_download_page_html(
            request, file_size_display, last_modified_display, version
        )
    )


@router.get("/favicon.ico")
async def get_favicon():
    """Serve favicon.ico for download page"""
    if not FAVICON_PATH.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")

    return FileResponse(path=str(FAVICON_PATH), media_type="image/x-icon")


@router.head("/installer/file")
@router.get("/installer/file")
async def download_installer_file(request: Request):
    """
    Direct download the FourT Setup installer file

    Returns the versioned setup file from the releases folder.
    Supports HEAD request for getting file size.
    """
    version = get_app_version()
    installer_filename = f"FourT_Setup_v{version}.exe"
    releases_dir = CLIENT_DIR / "releases"
    installer_path = releases_dir / version / installer_filename

    if not installer_path.exists():
        # Fallback check - maybe it was just uploaded with generic name?
        fallback_path = releases_dir / version / "FourT_Setup.exe"
        if fallback_path.exists():
            installer_path = fallback_path
            installer_filename = "FourT_Setup.exe"
        else:
            raise HTTPException(
                status_code=404, detail=f"Installer for version {version} not found."
            )

    file_size = installer_path.stat().st_size

    # For HEAD requests, return just headers without body
    if request.method == "HEAD":
        from fastapi.responses import Response

        return Response(
            headers={
                "Content-Length": str(file_size),
                "Content-Type": "application/octet-stream",
                "Content-Disposition": f"attachment; filename={installer_filename}",
            }
        )

    # Increment download count (only for GET requests)
    if request.method != "HEAD":
        await increment_download_count(version, installer_filename)

    return FileResponse(
        path=str(installer_path),
        filename=installer_filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={installer_filename}"},
    )


@router.head("/installer/zip")
@router.get("/installer/zip")
async def download_installer_zip(request: Request):
    """
    Download ZIP file for manual installation (web download).
    The ZIP contains the setup exe for easier distribution.
    """
    version = get_app_version()
    zip_filename = f"FourT_v{version}.zip"
    releases_dir = CLIENT_DIR / "releases"
    zip_path = releases_dir / version / zip_filename

    if not zip_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"ZIP for version {version} not found. Please build the installer first.",
        )

    file_size = zip_path.stat().st_size

    # For HEAD requests, return just headers without body
    if request.method == "HEAD":
        from fastapi.responses import Response

        return Response(
            headers={
                "Content-Length": str(file_size),
                "Content-Type": "application/zip",
                "Content-Disposition": f"attachment; filename={zip_filename}",
            }
        )

    # Increment download count (only for GET requests)
    await increment_download_count(version, zip_filename)

    return FileResponse(
        path=str(zip_path),
        filename=zip_filename,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )
