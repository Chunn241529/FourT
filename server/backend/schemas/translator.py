from pydantic import BaseModel
from typing import Optional


class TranslationRequest(BaseModel):
    text: str
    source_lang: Optional[str] = "auto"
    target_lang: Optional[str] = "vi"
    context: Optional[str] = None  # Previous dialogue lines for context
    style: Optional[str] = "volam"  # "volam", "normal"
    api_key: Optional[str] = None  # User provided Groq API Key


class TranslationResponse(BaseModel):
    translated_text: str
    detected_lang: str
    used_cache: bool = False
