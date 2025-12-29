from pydantic import BaseModel
from typing import Optional


class TrialCheckRequest(BaseModel):
    device_id: str
    ipv4: Optional[str] = None


class TrialCheckResponse(BaseModel):
    trial_active: bool
    trial_remaining_seconds: int
    first_seen: Optional[str] = None
    message: str
