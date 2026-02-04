from __future__ import annotations

import json
from typing import Dict

from app.services.intent_helpers import (
    detect_info_intent,
    detect_product_intent,
    is_inquiry_trigger,
    is_reservation_related,
    is_reservation_typo,
)


INTENTS = [
    "BOOKING_TABLE",
    "BOOKING_ROOM",
    "INFO",
    "PRODUCT",
    "INQUIRY",
    "GREETING",
    "GOODBYE",
    "GENERAL",
]

EXACT_KEYWORD_RULES = {
    "BOOKING_TABLE": {
        "rezerviram mizo",
        "rezerviral bi mizo",
        "book table",
        "table reservation",
    },
    "BOOKING_ROOM": {
        "rezerviram sobo",
        "rezerviral bi sobo",
        "book room",
        "room reservation",
    },
    "INFO": {
        "odpiralni cas",
        "delovni cas",
        "kontakt",
        "telefon",
        "parking",
        "parkirisce",
    },
    "PRODUCT": {
        "seznam izdelkov",
        "katalog izdelkov",
        "narocilo izdelkov",
        "spletna trgovina",
    },
    "INQUIRY": {
        "povprasevanje",
        "poslji ponudbo",
        "teambuilding",
        "organizacija poroke",
        "catering ponudba",
    },
    "GREETING": {"zdravo", "živjo", "dober dan", "hello", "hi"},
    "GOODBYE": {"adijo", "nasvidenje", "hvala in adijo", "bye"},
}


def _has_any(text: str, tokens: set[str]) -> bool:
    return any(tok in text for tok in tokens)


def _greeting_score(text: str) -> float:
    greetings = {"zdravo", "živjo", "pozdrav", "dober dan", "hello", "hi"}
    return 1.0 if _has_any(text, greetings) else 0.0


def _goodbye_score(text: str) -> float:
    goodbyes = {"adijo", "nasvidenje", "hvala", "lep dan", "bye", "se vidimo", "lp"}
    return 1.0 if _has_any(text, goodbyes) else 0.0


def _booking_room_score(text: str) -> float:
    if not is_reservation_related(text):
        return 0.0
    room_tokens = {"soba", "sobo", "sobe", "room", "zimmer", "nočitev", "nocitev", "nastanitev", "preno"}
    if _has_any(text, room_tokens):
        return 0.9
    if is_reservation_typo(text):
        return 0.6
    return 0.5


def _booking_table_score(text: str) -> float:
    if not is_reservation_related(text):
        return 0.0
    table_tokens = {"miza", "mizo", "mize", "kosilo", "večerja", "vecerja", "table"}
    if _has_any(text, table_tokens):
        return 0.9
    if is_reservation_typo(text):
        return 0.6
    return 0.5


def _info_score(text: str) -> float:
    if detect_info_intent(text):
        return 0.8
    info_words = {"kdaj", "kje", "kako", "koliko", "kakšne", "kakšen", "ali imate", "a imate"}
    return 0.5 if _has_any(text, info_words) else 0.0


def _product_score(text: str) -> float:
    if detect_product_intent(text):
        return 0.8
    product_words = {"izdelek", "katalog", "trgovina", "pesto", "marmelada", "namaz", "paket"}
    return 0.5 if _has_any(text, product_words) else 0.0


def _inquiry_score(text: str) -> float:
    if is_inquiry_trigger(text):
        return 0.9
    inquiry_words = {"povpraš", "ponudb", "poroka", "teambuilding", "catering"}
    return 0.6 if _has_any(text, inquiry_words) else 0.0


def _exact_scores(text: str) -> Dict[str, float]:
    scores: Dict[str, float] = {intent: 0.0 for intent in INTENTS}
    for intent, tokens in EXACT_KEYWORD_RULES.items():
        if _has_any(text, tokens):
            scores[intent] = 1.0
    return scores


def _llm_fallback_scores(message: str) -> Dict[str, float]:
    try:
        from app.core.config import Settings
        from app.core.llm_client import get_llm_client

        client = get_llm_client()
        settings = Settings()
    except Exception:
        return {}

    tools = [
        {
            "type": "function",
            "name": "intent_scores",
            "description": "Oceni confidence za vsak intent od 0.0 do 1.0.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scores": {
                        "type": "object",
                        "properties": {
                            "BOOKING_TABLE": {"type": "number"},
                            "BOOKING_ROOM": {"type": "number"},
                            "INFO": {"type": "number"},
                            "PRODUCT": {"type": "number"},
                            "INQUIRY": {"type": "number"},
                            "GREETING": {"type": "number"},
                            "GOODBYE": {"type": "number"},
                            "GENERAL": {"type": "number"},
                        },
                        "required": INTENTS,
                    }
                },
                "required": ["scores"],
            },
        }
    ]
    try:
        response = client.responses.create(
            model=getattr(settings, "openai_model", "gpt-4.1-mini"),
            input=[
                {
                    "role": "system",
                    "content": (
                        "Classify user message into intents and return only confidence scores "
                        "between 0.0 and 1.0 for all intents."
                    ),
                },
                {"role": "user", "content": message},
            ],
            tools=tools,
            tool_choice={"type": "function", "name": "intent_scores"},
            temperature=0.0,
            max_output_tokens=180,
        )
    except Exception:
        return {}

    for block in getattr(response, "output", []) or []:
        for content in getattr(block, "content", []) or []:
            content_type = getattr(content, "type", "")
            if content_type not in {"tool_call", "function_call"}:
                continue
            name = getattr(content, "name", "") or getattr(getattr(content, "function", None), "name", "")
            if name != "intent_scores":
                continue
            args = getattr(content, "arguments", None)
            if args is None and getattr(content, "function", None):
                args = getattr(content.function, "arguments", None)
            try:
                payload = json.loads(args or "{}")
            except json.JSONDecodeError:
                return {}
            raw_scores = payload.get("scores", {})
            parsed: Dict[str, float] = {}
            for intent in INTENTS:
                value = raw_scores.get(intent)
                try:
                    parsed[intent] = max(0.0, min(1.0, float(value)))
                except (TypeError, ValueError):
                    parsed[intent] = 0.0
            return parsed
    return {}


def score_intent_confidence(message: str) -> Dict[str, float]:
    text = message.lower().strip()
    exact_scores = _exact_scores(text)
    if any(value >= 1.0 for value in exact_scores.values()):
        return {**{intent: 0.0 for intent in INTENTS}, **exact_scores}

    scores = {
        "BOOKING_TABLE": _booking_table_score(text),
        "BOOKING_ROOM": _booking_room_score(text),
        "INFO": _info_score(text),
        "PRODUCT": _product_score(text),
        "INQUIRY": _inquiry_score(text),
        "GREETING": _greeting_score(text),
        "GOODBYE": _goodbye_score(text),
        "GENERAL": 0.1,
    }
    if max(scores.values(), default=0.0) < 0.5:
        llm_scores = _llm_fallback_scores(message)
        if llm_scores:
            scores.update({intent: llm_scores.get(intent, scores[intent]) for intent in INTENTS})
    return scores
