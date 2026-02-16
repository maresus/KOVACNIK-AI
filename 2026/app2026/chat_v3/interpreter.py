from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.llm_client import get_llm_client
from app2026.chat_v3 import config as v3_config
from app2026.chat_v3.schemas import InterpretResult

_PROMPT_PATH = Path(__file__).with_name("prompts") / "interpreter.txt"
_AMBIGUOUS_NAMES = {"aljaž", "aljaz", "julija", "ana"}  # all three are both rooms and family members


def _system_prompt() -> str:
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8").strip()
    return "Return strict JSON with keys: intent, entities, confidence, continue_flow, needs_clarification, clarification_question."


def _extract_text_from_response(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()
    outputs: list[str] = []
    for block in getattr(response, "output", []) or []:
        for content in getattr(block, "content", []) or []:
            chunk = getattr(content, "text", None)
            if chunk:
                outputs.append(chunk)
    return "\n".join(outputs).strip()


def _fallback_unclear() -> InterpretResult:
    return InterpretResult(intent="UNCLEAR", entities={}, confidence=0.0, continue_flow=False)


def _strict_from_raw(raw: str) -> InterpretResult:
    try:
        payload = json.loads(raw)
    except Exception:
        return _fallback_unclear()
    if not isinstance(payload, dict):
        return _fallback_unclear()

    required = {"intent", "entities", "confidence", "continue_flow", "needs_clarification", "clarification_question"}
    if not required.issubset(set(payload.keys())):
        return _fallback_unclear()

    try:
        return InterpretResult(**payload)
    except Exception:
        return _fallback_unclear()


def _apply_disambiguation(message: str, result: InterpretResult) -> InterpretResult:
    if result.intent not in {"INFO_PERSON", "INFO_ROOM"}:
        return result
    name = str((result.entities or {}).get("name", "")).strip().lower()
    if not name:
        return result
    if name not in _AMBIGUOUS_NAMES:
        return result
    msg = (message or "").lower()
    person_hints = ("kdo", "oseba", "gospodar", "sin", "hči", "hci")
    room_hints = ("soba", "nastanitev", "nocitev", "nočitev", "rezervacija sobe")
    if any(h in msg for h in person_hints) and not any(h in msg for h in room_hints):
        return result.model_copy(update={"intent": "INFO_PERSON"})
    if any(h in msg for h in room_hints) and not any(h in msg for h in person_hints):
        return result.model_copy(update={"intent": "INFO_ROOM"})
    question = (
        f"Ali vas zanima soba {name.title()} ali informacije o {name.title()}, članu družine?"
    )
    return result.model_copy(
        update={
            "needs_clarification": True,
            "clarification_question": question,
            "confidence": min(result.confidence, 0.79),
        }
    )


def interpret(message: str, history: list[dict[str, str]] | None, session: dict[str, Any] | None) -> InterpretResult:
    context = (history or [])[-5:]
    state_snapshot = session or {}
    user_payload = {"message": message, "history": context, "state": state_snapshot}

    try:
        client = get_llm_client()
        response = client.responses.create(
            model=v3_config.V3_INTENT_MODEL,
            input=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            max_output_tokens=260,
            temperature=0.0,
            text={"format": {"type": "json_object"}},
        )
        raw = _extract_text_from_response(response)
        if not raw:
            return _fallback_unclear()
        parsed = _strict_from_raw(raw)
        return _apply_disambiguation(message, parsed)
    except Exception:
        return _fallback_unclear()


# Backward compatibility for v2 shadow hook.
def parse_intent(message: str, history: list[dict[str, str]], state: dict[str, Any]) -> InterpretResult:
    return interpret(message=message, history=history, session=state)
