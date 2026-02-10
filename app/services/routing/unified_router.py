from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class SwitchAction(str, Enum):
    HARD_SWITCH = "HARD_SWITCH"
    SOFT_INTERRUPT = "SOFT_INTERRUPT"
    IGNORE = "IGNORE"


class IntentType(str, Enum):
    BOOKING_APPOINTMENT = "BOOKING_APPOINTMENT"
    SERVICE_INFO = "SERVICE_INFO"
    PRICE = "PRICE"
    INFO = "INFO"
    UNSUPPORTED_SYMPTOM = "UNSUPPORTED_SYMPTOM"
    URGENCY = "URGENCY"
    GREETING = "GREETING"
    GOODBYE = "GOODBYE"
    AFFIRMATIVE = "AFFIRMATIVE"
    NEGATIVE = "NEGATIVE"
    GENERAL = "GENERAL"


@dataclass
class Decision:
    primary_intent: IntentType
    confidence: float
    action: SwitchAction
    secondary_intent: IntentType | None = None
    service_type: str | None = None
    resume_prompt: str | None = None


AFFIRMATIVE_WORDS = {
    "da", "ja", "ok", "okej", "okay", "seveda", "vredu", "lahko", "prosim",
    "yes", "yep", "sure", "cool", "super", "odlično", "odlicno",
}

NEGATIVE_WORDS = {
    "ne", "no", "nope", "ne hvala", "hvala", "rajsi", "rajši", "ne zelim", "ne želim",
}

SERVICE_KEYWORDS = {
    "ORTOPED": ["ortoped", "ortopedski", "ortopedija"],
    "DERMATOLOG": ["dermatolog", "dermatološki", "dermatoloski", "koža", "koza", "izpuščaj", "izpuscaj", "akne"],
    "OKULIST": ["okulist", "okulistični", "okulisticni", "oftalmolog", "očesni", "ocesi", "vid"],
}


def _detect_affirmative_negative(message: str) -> IntentType | None:
    text = " ".join(message.lower().strip().split())
    cleaned = text.replace(".", "").replace(",", "").replace("!", "").replace("?", "")
    if cleaned in {"da", "ja", "ok", "okej", "okay", "ne", "no", "nope"}:
        return IntentType.NEGATIVE if cleaned in {"ne", "no", "nope"} else IntentType.AFFIRMATIVE
    negative_phrases = {"ne hvala", "ne zelim", "ne želim", "rajši", "rajsi"}
    if any(phrase in cleaned for phrase in negative_phrases):
        return IntentType.NEGATIVE
    tokens = cleaned.split()
    if tokens and all(word in AFFIRMATIVE_WORDS for word in tokens):
        return IntentType.AFFIRMATIVE
    if any(word in NEGATIVE_WORDS for word in tokens):
        return IntentType.NEGATIVE
    return None


def _detect_service_type(message: str) -> str | None:
    lowered = message.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            return service
    return None


def _has_any(message: str, tokens: set[str]) -> bool:
    lowered = message.lower()
    return any(tok in lowered for tok in tokens)


def _is_booking(message: str) -> bool:
    booking_tokens = {
        "naroči", "naročil", "naročila", "naroci", "termin", "rezerv", "rad bi", "rada bi", "želim", "zelim",
    }
    return _has_any(message, booking_tokens)


def _is_price(message: str) -> bool:
    price_tokens = {"cena", "cene", "cenik", "koliko", "stane"}
    return _has_any(message, price_tokens)


def _is_info(message: str) -> bool:
    info_tokens = {"kdaj", "odprti", "odprto", "delovni čas", "delovni cas", "kontakt", "telefon", "email"}
    return _has_any(message, info_tokens)


def _is_greeting(message: str) -> bool:
    return _has_any(message, {"pozdravljeni", "živjo", "zivjo", "zdravo", "dober dan", "hej", "hello", "hi"})


def _is_goodbye(message: str) -> bool:
    return _has_any(message, {"adijo", "nasvidenje", "hvala in adijo", "bye", "se vidimo"})


def _is_urgency(message: str) -> bool:
    return _has_any(message, {"nujno", "urgentno", "urgent", "takoj", "rešil", "resil", "pomoč"})


def decide_action(confidence: float) -> SwitchAction:
    if confidence >= 0.8:
        return SwitchAction.HARD_SWITCH
    if confidence >= 0.5:
        return SwitchAction.SOFT_INTERRUPT
    return SwitchAction.IGNORE


def route(message: str, unified_state: dict[str, Any]) -> Decision:
    affneg = _detect_affirmative_negative(message)
    if affneg:
        return Decision(primary_intent=affneg, confidence=1.0, action=SwitchAction.IGNORE)

    service_type = _detect_service_type(message)

    if _is_urgency(message):
        return Decision(primary_intent=IntentType.URGENCY, confidence=1.0, action=SwitchAction.HARD_SWITCH)

    if _is_greeting(message):
        return Decision(primary_intent=IntentType.GREETING, confidence=1.0, action=SwitchAction.IGNORE)

    if _is_goodbye(message):
        return Decision(primary_intent=IntentType.GOODBYE, confidence=1.0, action=SwitchAction.IGNORE)

    if _is_price(message):
        return Decision(primary_intent=IntentType.PRICE, confidence=0.9, action=SwitchAction.SOFT_INTERRUPT, service_type=service_type)

    if _is_info(message):
        return Decision(primary_intent=IntentType.INFO, confidence=0.8, action=SwitchAction.SOFT_INTERRUPT)

    if _is_booking(message):
        return Decision(primary_intent=IntentType.BOOKING_APPOINTMENT, confidence=0.9, action=SwitchAction.HARD_SWITCH, service_type=service_type)

    if service_type:
        return Decision(primary_intent=IntentType.SERVICE_INFO, confidence=0.7, action=SwitchAction.SOFT_INTERRUPT, service_type=service_type)

    return Decision(primary_intent=IntentType.GENERAL, confidence=0.4, action=SwitchAction.IGNORE)


def decide_route(message: str, unified_state: dict[str, Any]) -> Decision:
    """Backward-compatible alias."""
    return route(message, unified_state)
