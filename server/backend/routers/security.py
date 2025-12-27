"""
Security Admin API Router
Endpoints for managing IP blacklist/whitelist and security events
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.security.ip_manager import ip_manager
from backend import database as db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/security",
    tags=["security"]
)


# ============== Request/Response Models ==============

class IPBlockRequest(BaseModel):
    ip: str
    reason: Optional[str] = "Manual block"
    hours: Optional[int] = 24
    permanent: Optional[bool] = False


class IPWhitelistRequest(BaseModel):
    ip: str
    description: Optional[str] = ""


class IPResponse(BaseModel):
    success: bool
    message: str
    ip: Optional[str] = None


# ============== Blacklist Endpoints ==============

@router.get("/blacklist")
async def get_blacklist():
    """Get all blacklisted IPs"""
    blacklist = await ip_manager.get_blacklist()
    return {
        "count": len(blacklist),
        "blacklist": blacklist
    }


@router.post("/blacklist", response_model=IPResponse)
async def add_to_blacklist(request: IPBlockRequest):
    """Add IP to blacklist"""
    success = await ip_manager.add_to_blacklist(
        ip=request.ip,
        reason=request.reason,
        hours=request.hours,
        permanent=request.permanent
    )
    
    if success:
        # Log security event
        await db.log_security_event(
            event_type="IP_BLACKLISTED",
            ip_address=request.ip,
            details={
                "reason": request.reason,
                "permanent": request.permanent,
                "hours": request.hours
            }
        )
        
        return IPResponse(
            success=True,
            message=f"IP {request.ip} added to blacklist",
            ip=request.ip
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to add IP to blacklist")


@router.delete("/blacklist/{ip}")
async def remove_from_blacklist(ip: str):
    """Remove IP from blacklist"""
    success = await ip_manager.remove_from_blacklist(ip)
    
    if success:
        await db.log_security_event(
            event_type="IP_UNBLACKLISTED",
            ip_address=ip
        )
        
        return IPResponse(
            success=True,
            message=f"IP {ip} removed from blacklist",
            ip=ip
        )
    else:
        raise HTTPException(status_code=404, detail="IP not found in blacklist")


@router.post("/blacklist/cleanup")
async def cleanup_expired_blacklist():
    """Remove expired blacklist entries"""
    count = await ip_manager.clear_expired_blacklist()
    return {
        "success": True,
        "message": f"Removed {count} expired entries",
        "removed_count": count
    }


# ============== Whitelist Endpoints ==============

@router.get("/whitelist")
async def get_whitelist():
    """Get all whitelisted IPs"""
    whitelist = await ip_manager.get_whitelist()
    return {
        "count": len(whitelist),
        "whitelist": whitelist
    }


@router.post("/whitelist", response_model=IPResponse)
async def add_to_whitelist(request: IPWhitelistRequest):
    """Add IP to whitelist"""
    success = await ip_manager.add_to_whitelist(
        ip=request.ip,
        description=request.description
    )
    
    if success:
        await db.log_security_event(
            event_type="IP_WHITELISTED",
            ip_address=request.ip,
            details={"description": request.description}
        )
        
        return IPResponse(
            success=True,
            message=f"IP {request.ip} added to whitelist",
            ip=request.ip
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to add IP to whitelist")


@router.delete("/whitelist/{ip}")
async def remove_from_whitelist(ip: str):
    """Remove IP from whitelist"""
    success = await ip_manager.remove_from_whitelist(ip)
    
    if success:
        await db.log_security_event(
            event_type="IP_UNWHITELISTED",
            ip_address=ip
        )
        
        return IPResponse(
            success=True,
            message=f"IP {ip} removed from whitelist",
            ip=ip
        )
    else:
        raise HTTPException(status_code=404, detail="IP not found in whitelist")


# ============== IP Check & Stats ==============

@router.get("/ip/{ip}")
async def check_ip_status(ip: str):
    """Check status of a specific IP"""
    return await ip_manager.check_ip(ip)


@router.get("/stats")
async def get_security_stats():
    """Get security statistics"""
    ip_stats = await ip_manager.get_stats()
    
    # Get recent security events count
    events = await db.get_security_events(limit=100)
    
    # Count by type
    event_counts = {}
    for event in events:
        event_type = event.get("event_type", "UNKNOWN")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    return {
        "ip_management": ip_stats,
        "recent_events": {
            "total": len(events),
            "by_type": event_counts
        }
    }


# ============== Security Events ==============

@router.get("/events")
async def get_security_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get security events log"""
    events = await db.get_security_events(event_type=event_type, limit=limit)
    return {
        "count": len(events),
        "events": events
    }
