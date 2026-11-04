import logging
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)
def detect_language(text):
    if not text or not text.strip():
        return None
    if len(text.strip()) < 3:
        return None
    try:
        lang = detect(text)
    except LangDetectException:
        logger.warning("Не удалось определить язык")
        return None

    if lang in ("ru", "en"):
        return lang
    return None
def language_to_human(lang):
    return {"ru": "русский", "en": "английский"}.get(lang, "Неизвестен")