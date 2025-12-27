"""
Releases router - Manage releases from releases/ folder and database
Syncs folder contents with database for tracking download counts
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

from backend import database as db

router = APIRouter(prefix="/api/releases", tags=["releases"])

# Directory paths - server/ is CURRENT_DIR, client/ is PROJECT_ROOT/client
CURRENT_DIR = Path(__file__).parent.parent.parent  # server/
PROJECT_ROOT = CURRENT_DIR.parent  # FourT/
CLIENT_DIR = PROJECT_ROOT / "client"

RELEASES_DIR = CLIENT_DIR / "releases"
UPDATE_INFO_FILE = CLIENT_DIR / "update_info.json"
DIST_DIR = CLIENT_DIR / "dist"

# Ensure releases directory exists
RELEASES_DIR.mkdir(exist_ok=True)


async def sync_releases_from_folder():
    """Sync releases folder with database"""
    import json

    if not RELEASES_DIR.exists():
        return

    # Get current version from update_info.json
    current_version = None
    if UPDATE_INFO_FILE.exists():
        try:
            info = json.loads(UPDATE_INFO_FILE.read_text(encoding="utf-8"))
            current_version = info.get("version")
        except Exception:
            pass

    # Scan version folders
    for version_dir in RELEASES_DIR.iterdir():
        if not version_dir.is_dir():
            continue

        version = version_dir.name

        # Check if release exists in DB
        existing = await db.get_release_by_version(version)

        if not existing:
            # Create new release
            release_date = datetime.fromtimestamp(
                version_dir.stat().st_mtime
            ).isoformat()
            release_id = await db.create_release(
                version=version, name=f"FourT v{version}", published_at=release_date
            )

            if release_id:
                # Add assets
                for file in version_dir.iterdir():
                    if file.is_file() and file.suffix.lower() in [
                        ".exe",
                        ".zip",
                        ".msi",
                    ]:
                        await db.create_release_asset(
                            release_id=release_id,
                            filename=file.name,
                            size=file.stat().st_size,
                            download_url=f"/api/releases/download/{version}/{file.name}",
                        )
        else:
            # Sync assets for existing release
            existing_assets = {a["filename"]: a for a in existing.get("assets", [])}
            found_files = set()

            for file in version_dir.iterdir():
                if file.is_file() and file.suffix.lower() in [".exe", ".zip", ".msi"]:
                    filename = file.name
                    found_files.add(filename)

                    if filename in existing_assets:
                        # Update size and download_url if needed
                        asset = existing_assets[filename]
                        updates = {}
                        if asset["size"] != file.stat().st_size:
                            updates["size"] = file.stat().st_size
                        if not asset.get("download_url"):
                            updates["download_url"] = (
                                f"/api/releases/download/{version}/{filename}"
                            )
                        if updates:
                            await db.update_release_asset(
                                release_id=existing["id"],
                                filename=filename,
                                updates=updates,
                            )
                    else:
                        # Check if there's a similar asset with size=0 (manually created placeholder)
                        # that should be merged with this file
                        merged = False
                        for asset_name, asset_data in existing_assets.items():
                            if (
                                asset_data.get("size", 0) == 0
                                and asset_data.get("download_count", 0) > 0
                            ):
                                # This is a placeholder with counts - check if filenames are similar
                                # e.g. FourT_Setup.exe matches FourT_Setup_v0.0.1.exe
                                if "Setup" in asset_name and "Setup" in filename:
                                    # Merge: delete the placeholder, create with its count
                                    old_count = asset_data.get("download_count", 0)
                                    print(
                                        f"[Sync] Merging placeholder {asset_name} ({old_count} downloads) into {filename}"
                                    )
                                    await db.delete_release_asset(
                                        existing["id"], asset_name
                                    )
                                    await db.create_release_asset(
                                        release_id=existing["id"],
                                        filename=filename,
                                        size=file.stat().st_size,
                                        download_url=f"/api/releases/download/{version}/{filename}",
                                        download_count=old_count,
                                    )
                                    merged = True
                                    break

                        if not merged:
                            # New asset found
                            await db.create_release_asset(
                                release_id=existing["id"],
                                filename=filename,
                                size=file.stat().st_size,
                                download_url=f"/api/releases/download/{version}/{filename}",
                            )

                # Remove assets that are no longer in folder (only if download_count is 0)
            for asset_name, asset_data in existing_assets.items():
                if asset_name not in found_files:
                    # Preserve assets with download counts (user-set data)
                    if asset_data.get("download_count", 0) == 0:
                        print(
                            f"[Sync] Removing orphaned asset: {asset_name} from release {existing['id']}"
                        )
                        await db.delete_release_asset(existing["id"], asset_name)

    # Prune orphans: Delete releases from DB if folder missing (only if no download data)
    all_releases = await db.get_all_releases()
    for rel in all_releases:
        version = rel["version"]
        version_path = RELEASES_DIR / version

        if not version_path.exists() or not version_path.is_dir():
            # Check if release has any download data
            total_downloads = sum(
                a.get("download_count", 0) for a in rel.get("assets", [])
            )
            if total_downloads == 0:
                print(
                    f"[Sync] Pruning {version} - folder not found and no download data"
                )
                await db.delete_release(version)


@router.get("")
async def get_releases():
    """
    Get all releases from database
    Syncs with releases folder first
    """
    # Sync folder with DB
    await sync_releases_from_folder()

    # Get from database
    releases = await db.get_all_releases()
    stats = await db.get_download_stats()

    # Format response
    formatted_releases = []
    for release in releases:
        # Show all assets - let user choose which to download
        formatted_releases.append(
            {
                "tag_name": release["version"],
                "name": release["name"],
                "published_at": release["published_at"],
                "prerelease": release["prerelease"],
                "assets": [
                    {
                        "name": asset["filename"],
                        "size": asset["size"],
                        "download_count": asset["download_count"],
                        "download_url": asset["download_url"],
                    }
                    for asset in release.get("assets", [])
                    if asset.get("size", 0) > 0  # Only show files that exist
                ],
            }
        )
    return {
        "total_downloads": stats.get("total_downloads", 0),
        "releases": formatted_releases,
    }


@router.get("/download/{version}/{filename}")
async def download_file(version: str, filename: str):
    """
    Download a specific file from a version
    Increments download count automatically
    """
    file_path = RELEASES_DIR / version / filename

    if not file_path.exists():
        return {"error": "File not found"}

    # Increment download count in DB
    await db.increment_download_count(version, filename)

    return FileResponse(
        path=str(file_path), filename=filename, media_type="application/octet-stream"
    )


@router.post("/increment")
async def increment_download(version: str = "", asset_name: str = "FourT_Setup.exe"):
    """
    Increment download count for an asset
    Called by frontend when download button clicked
    """
    if not version:
        return {"success": False, "error": "Version required"}

    result = await db.increment_download_count(version, asset_name)
    return result


@router.post("/set-total")
async def set_total_downloads(total: int = 0):
    """
    Set total download count (admin only)
    """
    success = await db.set_total_downloads(total)
    stats = await db.get_download_stats()

    return {"success": success, "total_downloads": stats.get("total_downloads", 0)}


@router.post("/set-version-count")
async def set_version_download_count(
    version: str, asset_name: str = "FourT_Setup.exe", count: int = 0
):
    """
    Set download count for a specific version/asset (admin only)
    """
    success = await db.set_asset_download_count(version, asset_name, count)

    return {"success": success, "version": version, "asset": asset_name, "count": count}


@router.post("/add")
async def add_release(
    version: str,
    name: Optional[str] = None,
    prerelease: bool = False,
    changelog: Optional[str] = None,
):
    """
    Add a new release manually (admin only)
    """
    # Check if exists
    existing = await db.get_release_by_version(version)
    if existing:
        return {"success": False, "error": "Version already exists"}

    release_id = await db.create_release(
        version=version, name=name, prerelease=prerelease, changelog=changelog
    )

    if release_id:
        # Check for installer file
        installer_name = f"FourT_Setup_v{version}.exe"
        installer_path = RELEASES_DIR / version / installer_name

        # Check fallback
        if not installer_path.exists():
            fallback = RELEASES_DIR / version / "FourT_Setup.exe"
            if fallback.exists():
                installer_path = fallback
                installer_name = "FourT_Setup.exe"

        if installer_path.exists():
            await db.create_release_asset(
                release_id=release_id,
                filename=installer_name,
                size=installer_path.stat().st_size,
                download_url=f"/api/releases/download/{version}/{installer_name}",
            )

    return {"success": release_id is not None, "release_id": release_id}


@router.delete("/{version}")
async def delete_release(version: str):
    """
    Delete a release from DB and disk (admin only)
    """
    # Delete from DB
    success = await db.delete_release(version)

    # Delete from disk
    version_dir = RELEASES_DIR / version
    if version_dir.exists() and version_dir.is_dir():
        try:
            import shutil

            shutil.rmtree(version_dir)
        except Exception as e:
            print(f"Error deleting folder {version}: {e}")

    return {"success": success}
