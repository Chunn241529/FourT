"""
Translation Service
Provides text translation using Google Translate (free, no API key needed)
Uses googletrans library for translation
"""

import threading
from typing import Callable, Optional
from functools import lru_cache


class TranslationService:
    """
    Translation service using Google Translate

    Features:
    - Async translation to avoid blocking UI
    - Caching to reduce API calls
    - Language auto-detection
    """

    # Supported languages
    LANGUAGES = {
        "auto": "Auto Detect",
        "en": "English",
        "vi": "Vietnamese",
        "zh-CN": "Chinese (Simplified)",
        "zh-TW": "Chinese (Traditional)",
        "ja": "Japanese",
        "ko": "Korean",
        "th": "Thai",
        "id": "Indonesian",
        "ms": "Malay",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "ru": "Russian",
    }

    def __init__(self):
        self._translator = None
        self._cache = {}  # Simple LRU cache
        self._cache_max_size = 100

    def _get_translator(self):
        """Lazy init translator"""
        if self._translator is None:
            try:
                from googletrans import Translator

                self._translator = Translator()
            except ImportError:
                print("[TranslationService] googletrans not installed, using fallback")
                self._translator = None
        return self._translator

    def translate(
        self, text: str, dest: str = "vi", src: str = "auto"
    ) -> tuple[str, str]:
        """
        Translate text synchronously

        Args:
            text: Text to translate
            dest: Target language code
            src: Source language code ("auto" for auto-detect)

        Returns:
            tuple: (translated_text, detected_source_language)
        """
        if not text or not text.strip():
            return "", src

        # Check cache
        cache_key = f"{src}:{dest}:{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Create fresh translator each time to avoid session issues
            from googletrans import Translator

            translator = Translator()

            import asyncio

            # googletrans 4.0.0-rc1 is async, need to run in event loop
            async def do_translate():
                return await translator.translate(
                    text, dest=dest, src=src if src != "auto" else "auto"
                )

            # Run async in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(do_translate())
            finally:
                loop.close()

            if result is None or not hasattr(result, "text"):
                return text, src  # Return original on error

            translated = result.text
            detected = result.src if hasattr(result, "src") else src

            # Cache result
            if len(self._cache) >= self._cache_max_size:
                # Remove oldest entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = (translated, detected)

            return translated, detected

        except Exception as e:
            print(f"[TranslationService] Translation error: {e}")
            return text, src

    def translate_async(
        self,
        text: str,
        callback: Callable[[str, str], None],
        dest: str = "vi",
        src: str = "auto",
    ) -> None:
        """
        Translate text asynchronously (non-blocking)

        Args:
            text: Text to translate
            callback: Callback(translated_text, detected_source_language)
            dest: Target language code
            src: Source language code
        """

        def _do_translate():
            result = self.translate(text, dest, src)
            callback(result[0], result[1])

        thread = threading.Thread(target=_do_translate, daemon=True)
        thread.start()

    def clear_cache(self):
        """Clear translation cache"""
        self._cache.clear()

    def _get_system_prompt(self, style: str, source_lang: str, target_lang: str) -> str:
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
            return f"""You are a dedicated translator for a Wuxia (Võ Lâm) role-playing game.
Translate the input from {src_name} to {tgt_name} using authentic Wuxia/Kiem Hiep style.

CRITICAL RULES:
1. PRONOUNS (NATURAL & CONTEXTUAL):
   - **AVOID repetitive "Tại hạ / Các hạ"**. Only use for very formal strangers.
   - **"Ta / Ngươi"**: Standard/Default for combat, quests, neutral interactions.
   - **"Huynh / Đệ / Tỷ / Muội"**: For party members (Tổ đội) or friends.
   - **"Thiếu hiệp / Cô nương / Tiền bối"**: Politeness for strangers.
   - **OMIT pronouns** if subject is clear (Natural Vietnamese).

2. TERMINOLOGY (HÁN VIỆT):
   - Attack -> "Công kích"
   - Kill/Defeat -> "Tiêu diệt" / "Hạ gục"
   - Heal -> "Hồi phục" / "Trị liệu"
   - Party -> "Tổ đội" | Guild -> "Bang hội"
   - Exp -> "Kinh nghiệm" | Level -> "Cấp độ"

3. TONE:
   - Concise, Heroic (Hào sảng), not unnecessarily polite.
   - Example 1: "Need heal!" -> "Cần trị liệu!" (Natural) vs "Tại hạ cần trị liệu" (Robotic).
   - Example 2: "I will kill you" -> "Ta sẽ diệt ngươi!" (Heroic) vs "Tại hạ sẽ tiêu diệt các hạ" (Weird).

OUTPUT ONLY THE TRANSLATED TEXT.
"""
        else:
            return f"Bạn trả lời câu hỏi quizz giúp tôi, đưa ra câu trả lời, không thêm gì khác"

            # f"""You are a professional translator. Translate the text from {src_name} to {tgt_name}. Output ONLY the translated text. Do not add explanations."""

    def translate_smart(
        self,
        text: str,
        context: Optional[str] = None,
        dest: str = "vi",
        style: str = "volam",
        api_key: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Smart translate using Client-side Groq AI
        Falls back to Google Translate on error
        """
        if not text or not text.strip():
            return "", "ai"

        # Check cache
        cache_key = f"AI:{style}:{dest}:{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not api_key:
            print("[TranslationService] No API Key for smart translate")
            return self.translate(text, dest)

        try:
            from groq import Groq

            client = Groq(api_key=api_key)

            system_prompt = self._get_system_prompt(style, "auto", dest)

            # Construct User Message (Input -> Output pattern)
            if context:
                # Add context to help AI with pronouns
                user_content = f"Context:\n{context}\n\nTask:\nInput: {text}\nOutput:"
            else:
                user_content = f"Input: {text}\nOutput:"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use fast model
                messages=messages,
                temperature=0.3,
                max_completion_tokens=300,
                stream=False,
            )

            translated = completion.choices[0].message.content.strip()

            # Save to cache if successful
            if translated:
                self._cache[cache_key] = (translated, "ai")
                return translated, "ai"

            return self.translate(text, dest)

        except ImportError:
            print(
                "[TranslationService] 'groq' library not installed. Please install 'groq'."
            )
            return self.translate(text, dest)
        except Exception as e:
            print(f"[TranslationService] Smart translate failed: {e}")
            # Fallback
            result = self.translate(text, dest)
            return result

    def translate_smart_async(
        self,
        text: str,
        callback: Callable[[str, str], None],
        context: Optional[str] = None,
        dest: str = "vi",
        style: str = "volam",
        api_key: Optional[str] = None,
    ) -> None:
        """
        Smart translate asynchronously
        """

        def _do():
            result = self.translate_smart(text, context, dest, style, api_key)
            callback(result[0], result[1])

        thread = threading.Thread(target=_do, daemon=True)
        thread.start()

    @staticmethod
    def get_language_name(code: str) -> str:
        """Get language display name from code"""
        return TranslationService.LANGUAGES.get(code, code)

    @staticmethod
    def get_available_languages() -> dict:
        """Get all available languages"""
        return TranslationService.LANGUAGES.copy()


# Singleton instance
_service_instance: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get singleton translation service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = TranslationService()
    return _service_instance
