from fastapi import APIRouter, Request
from backend.schemas import TrialCheckRequest, TrialCheckResponse
from datetime import datetime, timedelta
from backend import database as db
from backend.routers.features import _get_all_packages
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/trial",
    tags=["trial"]
)

def get_client_ip(request: Request) -> str:
    """Get real client IP from request headers (supports proxy)"""
    # Check X-Forwarded-For first (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, first one is the client
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP (common proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return ""

def get_trial_duration_minutes() -> int:
    """Get trial duration from package config (supports minutes or days)"""
    try:
        packages = _get_all_packages()
        trial_pkg = packages.get("trial", {})
        
        # Check for duration_minutes first (more precise for trial)
        if trial_pkg.get("duration_minutes"):
            return int(trial_pkg["duration_minutes"])
        
        # Fallback to duration_days
        duration_days = trial_pkg.get("duration_days", 0)
        if duration_days > 0:
            return int(duration_days * 24 * 60)  # Convert days to minutes
        
        # Default fallback
        return 30
    except Exception as e:
        logger.error(f"Error getting trial duration: {e}")
        return 30  # Default 30 minutes

@router.post("/check", response_model=TrialCheckResponse)
async def check_trial(request: Request, trial_request: TrialCheckRequest):
    """
    Check if a device has an active trial.
    If device is new, register it and start trial.
    If device exists, return remaining trial time.
    """
    device_id = trial_request.device_id
    
    # Get real client IP from request (public IP)
    client_ip = get_client_ip(request)
    logger.info(f"[Trial] Client IP: {client_ip}")
    
    # Check if device already exists
    device_data = await db.get_device(device_id)
    
    if device_data is None:
        # New device - register and start trial
        now = datetime.now()
        trial_duration = get_trial_duration_minutes()
        trial_expires = now + timedelta(minutes=trial_duration)
        
        new_device = {
            "device_id": device_id,
            "first_seen": now.isoformat(),
            "last_seen": now.isoformat(),
            "trial_started_at": now.isoformat(),
            "trial_expires_at": trial_expires.isoformat(),
            "ip_addresses": [client_ip] if client_ip else []
        }
        await db.create_device(new_device)
        
        logger.info(f"[Trial] New device registered: {device_id}")
        
        return TrialCheckResponse(
            trial_active=True,
            trial_remaining_seconds=trial_duration * 60,
            first_seen=now.isoformat(),
            message="Trial started successfully"
        )
    
    # Existing device - check trial status
    now = datetime.now()
    
    # Update last_seen and ip_addresses
    updates = {"last_seen": now.isoformat()}
    
    ip_addresses = device_data.get("ip_addresses", [])
    if client_ip and client_ip not in ip_addresses:
        ip_addresses.append(client_ip)
        updates["ip_addresses"] = ip_addresses
    
    await db.update_device(device_id, updates)
    
    # Check if trial is still active
    trial_expires = datetime.fromisoformat(device_data["trial_expires_at"])
    
    if now < trial_expires:
        # Trial still active
        remaining_seconds = int((trial_expires - now).total_seconds())
        logger.info(f"[Trial] Device {device_id} has {remaining_seconds}s remaining")
        
        return TrialCheckResponse(
            trial_active=True,
            trial_remaining_seconds=remaining_seconds,
            first_seen=device_data["first_seen"],
            message=f"Trial active with {remaining_seconds} seconds remaining"
        )
    else:
        # Trial expired
        logger.info(f"[Trial] Device {device_id} trial expired")
        
        return TrialCheckResponse(
            trial_active=False,
            trial_remaining_seconds=0,
            first_seen=device_data["first_seen"],
            message="Trial period has expired. Please upgrade to continue using features."
        )
