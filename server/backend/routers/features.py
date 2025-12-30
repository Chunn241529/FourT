from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import json
import os
from pathlib import Path

from backend.package_config import (
    get_package_definitions,
    get_all_features,
    get_package_features,
    get_package_limits,
    DEFAULT_PACKAGE_DEFINITIONS,
)

router = APIRouter(prefix="/features", tags=["features"])

# File path for persistent storage
DATA_DIR = Path(__file__).parent.parent / "data"
PACKAGES_FILE = DATA_DIR / "packages.json"
MENU_ITEMS_FILE = DATA_DIR / "menu_items.json"

# Default menu items config
DEFAULT_MENU_ITEMS = {
    "midi_playback": {"visible": True, "label": "auto_play_midi"},
    "quest_video_helper": {"visible": True, "label": "quest_video_helper"},
    "screen_translator": {"visible": True, "label": "screen_translator"},
    "ping_optimizer": {"visible": True, "label": "ping_optimizer"},
    "macro_recorder": {"visible": True, "label": "macro_recorder"},
    "wwm_combo": {"visible": True, "label": "macro_combo"},
}


def _load_menu_items() -> Dict[str, Dict[str, Any]]:
    """Load menu items config from JSON file"""
    if MENU_ITEMS_FILE.exists():
        try:
            with open(MENU_ITEMS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_MENU_ITEMS


def _save_menu_items(menu_items: Dict[str, Dict[str, Any]]):
    """Save menu items to JSON file"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(MENU_ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump(menu_items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Features] Error saving menu items: {e}")


class FeatureResponse(BaseModel):
    package: str
    features: List[str]
    limits: Dict[str, Any]


class PackageUpdate(BaseModel):
    name: str
    description: str
    price: int
    duration_days: int = 30
    order: int = 99
    features: List[str]
    feature_display: List[str] = []
    limits: Dict[str, Any]
    color: str
    recommended: bool = False


def _load_saved_packages() -> Dict[str, Dict[str, Any]]:
    """Load packages from JSON file"""
    if PACKAGES_FILE.exists():
        try:
            with open(PACKAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def _save_packages(packages: Dict[str, Dict[str, Any]]):
    """Save packages to JSON file"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Allow exception to propagate so caller knows if save failed
    with open(PACKAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(packages, f, ensure_ascii=False, indent=2)


def _get_all_packages() -> Dict[str, Dict[str, Any]]:
    """Get all packages (defaults + saved overrides)"""
    result = dict(DEFAULT_PACKAGE_DEFINITIONS)
    saved = _load_saved_packages()
    result.update(saved)

    # Filter out soft-deleted packages
    return {k: v for k, v in result.items() if not v.get("_deleted", False)}


@router.get("/check/{package}", response_model=FeatureResponse)
async def check_features(package: str):
    """Get enabled features and limits for a package"""
    package = package.lower()

    all_packages = _get_all_packages()
    if package not in all_packages:
        raise HTTPException(status_code=404, detail="Package not found")

    pkg = all_packages[package]
    return FeatureResponse(
        package=package, features=pkg.get("features", []), limits=pkg.get("limits", {})
    )


@router.get("/config")
async def get_package_config():
    """Return full package configuration for client"""
    return {
        "packages": _get_all_packages(),
        "features": get_all_features(),
        "menu_items": _load_menu_items(),
        "cache_ttl": 3600,  # Client should cache for 1 hour
    }


@router.get("/packages")
async def get_all_packages_endpoint():
    """Get info about all packages"""
    all_packages = _get_all_packages()
    return {"packages": list(all_packages.keys()), "details": all_packages}


@router.get("/all-features")
async def get_features_list():
    """Get list of all available features"""
    return {"features": get_all_features()}


# ============ Admin CRUD Endpoints ============


@router.get("/admin/packages")
async def admin_get_packages():
    """Admin: Get all packages (default + saved)"""
    return {"packages": _get_all_packages()}


@router.post("/admin/packages/{package_id}")
async def admin_create_or_update_package(package_id: str, data: PackageUpdate):
    """Admin: Create or update a package (persisted to file)"""
    package_id = package_id.lower()

    # Load existing saved packages
    saved_packages = _load_saved_packages()

    # Update/add package
    saved_packages[package_id] = {
        "name": data.name,
        "description": data.description,
        "price": data.price,
        "duration_days": data.duration_days,
        "order": data.order,
        "features": data.features,
        "feature_display": data.feature_display,
        "limits": data.limits,
        "color": data.color,
        "recommended": data.recommended,
    }

    # Persist to file
    try:
        _save_packages(saved_packages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save package: {str(e)}")

    return {
        "success": True,
        "package_id": package_id,
        "data": saved_packages[package_id],
    }


@router.delete("/admin/packages/{package_id}")
async def admin_delete_package(package_id: str):
    """Admin: Delete a saved package (soft delete for defaults)"""
    package_id = package_id.lower()

    saved_packages = _load_saved_packages()

    # Case 1: Package is a default package -> Soft delete (hide it)
    if package_id in DEFAULT_PACKAGE_DEFINITIONS:
        saved_packages[package_id] = {"_deleted": True}
        try:
            _save_packages(saved_packages)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete package: {str(e)}"
            )
        return {
            "success": True,
            "message": f"Package {package_id} hidden (soft deleted)",
        }

    # Case 2: Package is NOT default but exists in saved -> Hard delete
    if package_id in saved_packages:
        del saved_packages[package_id]

        try:
            _save_packages(saved_packages)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete package: {str(e)}"
            )

        return {"success": True, "message": f"Package {package_id} deleted"}

    # Case 3: Package not found anywhere
    raise HTTPException(status_code=404, detail="Package not found")


# ============ Admin Menu Items Endpoints ============


@router.get("/admin/menu-items")
async def admin_get_menu_items():
    """Admin: Get all menu items config"""
    return {"menu_items": _load_menu_items()}


class MenuItemUpdate(BaseModel):
    visible: bool = True
    label: str = ""


@router.post("/admin/menu-items/{item_id}")
async def admin_update_menu_item(item_id: str, data: MenuItemUpdate):
    """Admin: Update a menu item visibility"""
    menu_items = _load_menu_items()

    if item_id not in menu_items:
        # Create new item
        menu_items[item_id] = {"visible": data.visible, "label": data.label}
    else:
        menu_items[item_id]["visible"] = data.visible
        if data.label:
            menu_items[item_id]["label"] = data.label

    _save_menu_items(menu_items)
    return {"success": True, "item_id": item_id, "data": menu_items[item_id]}


@router.put("/admin/menu-items")
async def admin_update_all_menu_items(menu_items: Dict[str, Dict[str, Any]]):
    """Admin: Update all menu items at once"""
    _save_menu_items(menu_items)
    return {"success": True, "menu_items": menu_items}
