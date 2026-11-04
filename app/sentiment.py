import logging
from typing import Optional, Dict
from functools import lru_cache

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


RU_MODEL_NAME = "blanchefort/rubert-base-cased-sentiment"
EN_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

RU_LABELS = {0: "neutral", 1: "positive", 2: "negative"}
EN_LABELS = {0: "negative", 1: "neutral", 2: "positive"}

LABELS_HUMAN = {
    "positive": "позитивный",
    "negative": "негативный",
    "neutral": "нейтральный",
}


@lru_cache(maxsize=2)
def _load_model(lang: str):
    if lang == "ru":
        model_name = RU_MODEL_NAME
    elif lang == "en":
        model_name = EN_MODEL_NAME
    else:
        raise ValueError("Неподдерживаемый язык")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

def predict_sentiment(text: str, lang: str = "ru") -> Optional[Dict]:
    if not text or not text.strip():
        return None
    text = text.strip()[:2000]
    try:
        tokenizer, model = _load_model(lang)
    except Exception as e:
        logger.exception(f"Ошибка загрузки модели: {e}")
        return None
    try:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        pred_idx = int(torch.argmax(probs))
        confidence = float(probs[pred_idx])
        label_map = RU_LABELS if lang == "ru" else EN_LABELS
        label = label_map[pred_idx]
        return {
            "label": label,
            "label_human": LABELS_HUMAN[label],
            "confidence": round(confidence, 4),
            "confidence_percent": int(round(confidence * 100)),
        }
    except Exception as e:
        logger.exception(f"Ошибка предсказания: {e}")
        return None