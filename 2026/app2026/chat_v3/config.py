from __future__ import annotations

from app.core.config import Settings

_settings = Settings()

INTENT_CONFIDENCE_MIN = float(_settings.intent_confidence_min)
V3_INTENT_MODEL = _settings.v3_intent_model
V3_SHADOW_MODE = bool(_settings.v3_shadow_mode)

INTENT_CONFIDENCE_OVERRIDES: dict[str, float] = {
    "BOOKING_ROOM": 0.88,
    "BOOKING_TABLE": 0.88,
    "CANCEL": 0.90,
    "CONFIRM": 0.90,
    "INFO_PERSON": 0.82,
    "INFO_ROOM": 0.82,
    "INFO_MENU": 0.80,
    "GREETING": 0.70,
    "THANKS": 0.70,
    "SMALLTALK": 0.70,
}


def get_confidence_threshold(intent: str) -> float:
    return float(INTENT_CONFIDENCE_OVERRIDES.get(intent, INTENT_CONFIDENCE_MIN))
