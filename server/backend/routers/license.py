from fastapi import APIRouter, HTTPException
from backend.schemas import (
    LicenseActivationRequest,
    LicenseVerifyRequest,
    LicenseResponse
)
from datetime import datetime, timedelta
import uuid
from core.config import DEMO_LICENSE_KEY, LICENSE_DURATION_DAYS
from backend import database as db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/license",
    tags=["license"]
)

@router.post("/verify", response_model=LicenseResponse)
async def verify_license(request: LicenseVerifyRequest):
    """Verify if a license key is valid and bound to the requesting device"""
    
    license_data = await db.get_license(request.license_key)
    
    if license_data:
        # Check device binding if device_id is provided
        if request.device_id and license_data.get("device_id"):
            if license_data["device_id"] != request.device_id:
                logger.warning(f"[License] Device mismatch for {request.license_key}: expected {license_data['device_id']}, got {request.device_id}")
                return LicenseResponse(
                    success=False,
                    message="License is bound to a different device"
                )
        
        # Check expiration
        if license_data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(license_data["expires_at"])
                if datetime.now() >= expires_at:
                    logger.info(f"[License] Expired license: {request.license_key}")
                    return LicenseResponse(
                        success=False,
                        message="License has expired"
                    )
            except Exception as e:
                logger.error(f"[License] Error parsing expiration: {e}")
        
        logger.info(f"[License] Valid verification for {request.license_key}")
        return LicenseResponse(
            success=True,
            message="License is valid",
            package=license_data["package"],
            expires_at=license_data["expires_at"],
            license_data=license_data
        )
    
    # For demo purposes, allow a specific key
    if request.license_key == DEMO_LICENSE_KEY:
        return LicenseResponse(
            success=True,
            message="Valid Demo License",
            package="premium",
            expires_at=(datetime.now() + timedelta(days=LICENSE_DURATION_DAYS)).isoformat()
        )
        
    return LicenseResponse(
        success=False,
        message="Invalid license key"
    )

@router.post("/activate", response_model=LicenseResponse)
async def activate_license(request: LicenseActivationRequest):
    """Activate a license key"""
    
    license_data = await db.get_license(request.license_key)
    
    # Check if license already exists in database (from payment or Admin)
    if license_data:
        # Check if license is already bound to a different device
        if license_data.get("device_id"):
            if request.device_id and license_data["device_id"] != request.device_id:
                logger.warning(f"[License] Attempted activation on different device: {request.license_key}")
                return LicenseResponse(
                    success=False,
                    message="License is already activated on another device"
                )
        
        # Update device_id and ipv4 if provided (for first-time activation or updates)
        updates = {}
        if request.device_id:
            updates["device_id"] = request.device_id
            updates["user_id"] = request.device_id
        if request.ipv4:
            updates["ipv4"] = request.ipv4
        
        if updates:
            await db.update_license(request.license_key, updates)
            # Refresh license data
            license_data = await db.get_license(request.license_key)
        
        logger.info(f"[License] Activated/updated {request.license_key} for device {request.device_id}")
        
        return LicenseResponse(
            success=True,
            message="License activated successfully",
            package=license_data["package"],
            expires_at=license_data["expires_at"],
            license_data=license_data
        )
    
    # Mock activation logic for VALID- keys
    if request.license_key.startswith("VALID-"):
        # Generate mock license data
        package = "pro"
        if "PREMIUM" in request.license_key:
            package = "premium"
            
        license_data = {
            "license_key": request.license_key,
            "package": package,
            "device_id": request.device_id,
            "ipv4": request.ipv4,
            "activated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=LICENSE_DURATION_DAYS)).isoformat(),
            "user_id": request.device_id if request.device_id else str(uuid.uuid4())
        }
        
        await db.create_license(license_data)
        
        return LicenseResponse(
            success=True,
            message="License activated successfully",
            package=package,
            expires_at=license_data["expires_at"],
            license_data=license_data
        )
    
    # Demo key support
    if request.license_key == DEMO_LICENSE_KEY:
         return LicenseResponse(
            success=True,
            message="Demo License Activated",
            package="premium",
            expires_at=(datetime.now() + timedelta(days=LICENSE_DURATION_DAYS)).isoformat()
        )

    return LicenseResponse(
        success=False,
        message="Invalid license key for activation"
    )

@router.post("/deactivate", response_model=LicenseResponse)
async def deactivate_license(request: LicenseVerifyRequest):
    """Deactivate a license"""
    license_data = await db.get_license(request.license_key)
    
    if license_data:
        await db.delete_license(request.license_key)
        return LicenseResponse(
            success=True,
            message="License deactivated successfully"
        )
        
    return LicenseResponse(
        success=False,
        message="License not found or already deactivated"
    )
