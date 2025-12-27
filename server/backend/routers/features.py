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
    DEFAULT_PACKAGE_DEFINITIONS
)

router = APIRouter(
    prefix="/features",
    tags=["features"]
)

# File path for persistent storage
DATA_DIR = Path(__file__).parent.parent / "data"
PACKAGES_FILE = DATA_DIR / "packages.json"


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
            with open(PACKAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def _save_packages(packages: Dict[str, Dict[str, Any]]):
    """Save packages to JSON file"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(PACKAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(packages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Features] Error saving packages: {e}")


def _get_all_packages() -> Dict[str, Dict[str, Any]]:
    """Get all packages (defaults + saved overrides)"""
    result = dict(DEFAULT_PACKAGE_DEFINITIONS)
    saved = _load_saved_packages()
    result.update(saved)
    return result


@router.get("/check/{package}", response_model=FeatureResponse)
async def check_features(package: str):
    """Get enabled features and limits for a package"""
    package = package.lower()
    
    all_packages = _get_all_packages()
    if package not in all_packages:
        raise HTTPException(status_code=404, detail="Package not found")
    
    pkg = all_packages[package]
    return FeatureResponse(
        package=package,
        features=pkg.get("features", []),
        limits=pkg.get("limits", {})
    )


@router.get("/config")
async def get_package_config():
    """Return full package configuration for client"""
    return {
        "packages": _get_all_packages(),
        "features": get_all_features(),
        "cache_ttl": 3600  # Client should cache for 1 hour
    }


@router.get("/packages")
async def get_all_packages_endpoint():
    """Get info about all packages"""
    all_packages = _get_all_packages()
    return {
        "packages": list(all_packages.keys()),
        "details": all_packages
    }


@router.get("/all-features")
async def get_features_list():
    """Get list of all available features"""
    return {
        "features": get_all_features()
    }


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
        "recommended": data.recommended
    }
    
    # Persist to file
    _save_packages(saved_packages)
    
    return {"success": True, "package_id": package_id, "data": saved_packages[package_id]}


@router.delete("/admin/packages/{package_id}")
async def admin_delete_package(package_id: str):
    """Admin: Delete a saved package (cannot delete defaults)"""
    package_id = package_id.lower()
    
    saved_packages = _load_saved_packages()
    
    if package_id in saved_packages:
        del saved_packages[package_id]
        _save_packages(saved_packages)
        return {"success": True, "message": f"Package {package_id} deleted"}
    
    if package_id in DEFAULT_PACKAGE_DEFINITIONS:
        raise HTTPException(status_code=400, detail="Cannot delete default package")
    
    raise HTTPException(status_code=404, detail="Package not found")
