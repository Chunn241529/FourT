from pydantic import BaseModel
from typing import List, Dict, Any


class FeatureCheckRequest(BaseModel):
    package: str


class FeatureResponse(BaseModel):
    package: str
    features: List[str]
    limits: Dict[str, Any]
