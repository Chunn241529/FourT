from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
import os
import json

router = APIRouter(prefix="/update", tags=["update"])


# Get path to dist folder
def get_dist_path():
    """Get path to dist folder containing FourT_Setup.exe"""
    # Try multiple locations
    possible_paths = []

    # Relative to this file -> client/dist
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))  # server/
    project_root = os.path.dirname(root_dir)  # FourT/
    possible_paths.append(os.path.join(project_root, "client", "dist"))

    # Also try in server/ for backward compatibility
    possible_paths.append(os.path.join(root_dir, "dist"))

    # Current working directory
    possible_paths.append(os.path.join(os.getcwd(), "dist"))

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return os.path.join(os.getcwd(), "dist")


@router.get("/download")
async def download_installer():
    """Download the latest FourT_Setup.exe installer"""
    dist_path = get_dist_path()
    installer_path = os.path.join(dist_path, "FourT_Setup.exe")

    if not os.path.exists(installer_path):
        raise HTTPException(
            status_code=404, detail="Installer not found. Please build first."
        )

    return FileResponse(
        path=installer_path,
        filename="FourT_Setup.exe",
        media_type="application/octet-stream",
    )


@router.get("/info")
async def get_update_info(request: Request):
    """Get update information (version, installer_url, changelog)"""
    try:
        # Try multiple locations for update_info.json
        possible_paths = []

        # Path 1: Relative to this file -> client/update_info.json
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))  # server/
            project_root = os.path.dirname(root_dir)  # FourT/
            possible_paths.append(
                os.path.join(project_root, "client", "update_info.json")
            )
            # Also try in server/ for backward compatibility
            possible_paths.append(os.path.join(root_dir, "update_info.json"))
        except:
            pass

        # Path 2: Current working directory
        possible_paths.append(os.path.join(os.getcwd(), "update_info.json"))

        # Path 3: Just the filename (current directory)
        possible_paths.append("update_info.json")

        # Find the first existing path
        update_file_path = None
        for path in possible_paths:
            print(f"[Update Router] Trying path: {path}")
            if os.path.exists(path):
                update_file_path = path
                print(f"[Update Router] Found update_info.json at: {path}")
                break

        if update_file_path:
            with open(update_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Rewrite download URLs to use current server
            base_url = str(request.base_url).rstrip("/")

            if "download_url" in data and not data["download_url"].startswith("http"):
                data["download_url"] = f"{base_url}/{data['download_url']}"

            if "download_url_exe" in data and not data["download_url_exe"].startswith(
                "http"
            ):
                data["download_url_exe"] = f"{base_url}/{data['download_url_exe']}"

            return data
        else:
            raise HTTPException(status_code=404, detail="Update info file not found")

    except Exception as e:
        import traceback

        error_detail = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"[Update Router] Exception caught: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)
