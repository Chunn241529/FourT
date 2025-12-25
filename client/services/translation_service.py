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
