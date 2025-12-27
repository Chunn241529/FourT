from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# --- License Schemas ---

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

# --- Feature Schemas ---

class FeatureCheckRequest(BaseModel):
    package: str

class FeatureResponse(BaseModel):
    package: str
    features: List[str]
    limits: Dict[str, Any]

# --- Trial Schemas ---

class TrialCheckRequest(BaseModel):
    device_id: str
    ipv4: Optional[str] = None

class TrialCheckResponse(BaseModel):
    trial_active: bool
    trial_remaining_seconds: int
    first_seen: Optional[str] = None
    message: str
