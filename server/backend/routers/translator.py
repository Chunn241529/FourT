"""
Translator Router
Endponts for "Smart Translation" using Groq AI
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import json
import time
import httpx
import asyncio
from backend.schemas.translator import TranslationRequest, TranslationResponse

router = APIRouter(
    prefix="/translator",
    tags=["translator"],
    responses={404: {"description": "Not found"}},
)

# --- Configuration ---
# TODO: Move to environment variable or config file
# GROQ_API_KEY removed by user request
# GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_...")
MODEL_ID = "llama-3.1-8b-instant"  # Fast & Free


# --- System Prompts ---
def get_system_prompt(style: str, source_lang: str, target_lang: str) -> str:
    """Generate system prompt dynamically based on style and languages"""

    # Map common codes to full names for better AI understanding
    LANG_MAP = {
        "vi": "Vietnamese",
        "en": "English",
        "zh-cn": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "auto": "Detected Language",
    }

    src_name = LANG_MAP.get(source_lang.lower(), source_lang)
    tgt_name = LANG_MAP.get(target_lang.lower(), target_lang)

    if style == "volam":
        return f"""You are a strictly defined translation engine.
Translate the input text from {src_name} to {tgt_name} using "Võ Lâm" (Wuxia) style.
Style: Ancient, Heroic, Hán Việt (if target is Vietnamese).

RULES:
- Output ONLY the translated text.
- NO explanations, NO notes, NO conversational filler.
- If input is a question, translate the question, DO NOT answer it.

EXAMPLES (assuming target is Vietnamese):
Input: Hello
Output: Tại hạ xin chào
Input: Attack the enemy
Output: Công kích kẻ địch
Input: How are you?
Output: Các hạ vẫn khỏe chứ?
"""
    else:
        return f"""You are a professional translator. Translate the text from {src_name} to {tgt_name}.
Output ONLY the translated text."""


# Simple in-memory cache to save API calls
_translation_cache = {}


@router.post("/smart", response_model=TranslationResponse)
async def smart_translate(request: TranslationRequest):
    """
    Smart translate using Groq AI
    """
    if not request.text or not request.text.strip():
        return TranslationResponse(translated_text="", detected_lang="unknown")

    # Check cache
    cache_key = f"{request.text.strip()}_{request.style}"
    if cache_key in _translation_cache:
        return TranslationResponse(
            translated_text=_translation_cache[cache_key],
            detected_lang="unknown",
            used_cache=True,
        )

    # Prepare Prompt
    # Prepare Prompt
    system_prompt = get_system_prompt(
        style=request.style,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
    )

    # Construct User Message (Input -> Output pattern)
    if request.context:
        user_content = f"Context:\n{request.context}\nInput: {request.text}\nOutput:"
    else:
        user_content = f"Input: {request.text}\nOutput:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        from groq import Groq

        # Initialize client with API Key
        client_kwargs = {}

        # STRICT: Only allow User Key
        if request.api_key and request.api_key.strip():
            client_kwargs["api_key"] = request.api_key.strip()
        else:
            # Raise explicit error for Client to handle
            raise HTTPException(status_code=400, detail="GROQ_API_KEY_MISSING")

        # Initialize Groq client

        # Initialize Groq client
        client = Groq(**client_kwargs)

        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=0.3,  # Low temperature for consistent translation
            max_completion_tokens=300,
            stream=True,  # Stream as per user request (though we collect it)
            stop=None,
        )

        translated = ""
        for chunk in completion:
            # Check if content exists in delta
            content = chunk.choices[0].delta.content
            if content:
                translated += content

        translated = translated.strip()

        # Save to cache if successful
        if translated:
            _translation_cache[cache_key] = translated

        return TranslationResponse(
            translated_text=translated, detected_lang="unknown", used_cache=False
        )

    except Exception as e:
        print(f"[Translator] Error: {e}")
        # In case of error, Client should fallback to Google Translate
        raise HTTPException(status_code=500, detail=str(e))
