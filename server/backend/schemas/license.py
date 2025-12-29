from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class LicenseActivationRequest(BaseModel):
    license_key: str
    device_id: Optional[str] = None
    ipv4: Optional[str] = None


class LicenseVerifyRequest(BaseModel):
    license_key: str
    device_id: Optional[str] = None
    ipv4: Optional[str] = None


class LicenseResponse(BaseModel):
    success: bool
    message: str
    package: Optional[str] = None
    expires_at: Optional[str] = None
    license_data: Optional[Dict[str, Any]] = None
