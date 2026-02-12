from __future__ import annotations

import json
import os
from typing import Any

from app.core.llm_client import get_llm_client

from app2026.chat.flows import info as info_flow


INTENT_LLM_ENABLED = os.getenv("V2_INTENT_LLM", "true").strip().lower() in {"1", "true", "yes", "on"}


def detect_intent(message: str, brand: Any) -> str:
    lowered = (message or "").lower()

    if any(tok in lowered for tok in ["živjo", "zdravo", "hej", "hello", "dober dan", "pozdravljeni"]):
        return "greeting"
    if any(tok in lowered for tok in ["pomoč", "help", "kaj znaš", "kaj znate", "kaj lahko"]):
        return "help"
    if info_flow.detect_info_key(message, brand):
        return "info"
    if any(tok in lowered for tok in ["rezerv", "soba", "sobe", "sobo", "miza", "mizo", "table", "room", "booking", "reserve"]):
        return "reservation"
    question_like_info = (
        "?" in lowered
        or lowered.startswith(("kaj", "kdo", "kje", "kak", "ali", "imate", "a imate"))
    )
    if question_like_info:
        return "info"
    if any(tok in lowered for tok in ["povpraš", "ponudb", "naročilo", "narocilo", "količin", "rok"]):
        return "inquiry"

    if not INTENT_LLM_ENABLED:
        return "fallback"

    return _detect_intent_llm(message)


def _detect_intent_llm(message: str) -> str:
    prompt = (
        "Odgovori SAMO z enim od: greeting, help, info, reservation, inquiry, fallback.\n"
        "Uporabi samo to sporočilo uporabnika.\n"
        f"Sporočilo: {message}\n"
        "Odgovor:"
    )
    try:
        client = get_llm_client()
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[{"role": "user", "content": prompt}],
            max_output_tokens=30,
            temperature=0.0,
        )
        answer = getattr(response, "output_text", None)
        if not answer:
            outputs = []
            for block in getattr(response, "output", []) or []:
                for content in getattr(block, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        outputs.append(text)
            answer = "\n".join(outputs).strip()
        if not answer:
            return "fallback"
        intent = answer.strip().split()[0].lower()
        if intent in {"greeting", "help", "info", "reservation", "inquiry", "fallback"}:
            return intent
    except Exception:
        return "fallback"
    return "fallback"
