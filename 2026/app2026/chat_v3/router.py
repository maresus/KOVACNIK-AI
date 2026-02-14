from __future__ import annotations

import copy
import json
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings
from app2026.brand.registry import get_brand
from app2026.chat import intent as v2_intent
from app2026.chat.state import get_session
from app2026.chat_v3 import config as v3_config
from app2026.chat_v3 import guards, interpreter, state_machine
from app2026.chat_v3.handlers import booking as booking_handler
from app2026.chat_v3.handlers import fallback as fallback_handler
from app2026.chat_v3.handlers import info as info_handler
from app2026.chat_v3.schemas import InterpretResult

router = APIRouter(prefix="/v3/chat", tags=["chat-v3"])
_settings = Settings()
_SHADOW_LOG_PATH = Path("data/shadow_intents.jsonl")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None


def _preview(text: str, limit: int = 100) -> str:
    value = (text or "").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def _mask_message(message: str) -> str:
    # Minimal PII masking for shadow logs.
    text = message or ""
    text = text.replace("@", "[at]")
    return text


async def _dispatch(result: InterpretResult, message: str, session, brand) -> dict[str, str]:
    if result.intent.startswith("INFO_"):
        return await info_handler.execute(result, message, session, brand)
    if result.intent in {"BOOKING_ROOM", "BOOKING_TABLE", "CONTINUE_FLOW", "CANCEL", "CONFIRM"}:
        return await booking_handler.execute(result, message, session, brand)
    return await fallback_handler.execute(result, message, session, brand)


async def handle_message(message: str, session_id: str, brand: Any) -> dict[str, Any]:
    session = get_session(session_id)
    guard_result = guards.check(message, session)
    if guard_result:
        if guard_result["action"] in {"continue_flow", "menu_detail"}:
            reply = await booking_handler.execute(
                InterpretResult(intent="CONTINUE_FLOW", entities=guard_result, confidence=1.0, continue_flow=True),
                message,
                session,
                brand,
            )
            return {"reply": reply["reply"], "session_id": session.session_id}

    history = session.history[-5:]
    result = interpreter.interpret(message, history, session.data)

    threshold = v3_config.get_confidence_threshold(result.intent)
    if result.confidence < threshold:
        reply = await fallback_handler.execute(result, message, session, brand)
        return {"reply": reply["reply"], "session_id": session.session_id}

    if result.needs_clarification and result.clarification_question:
        return {"reply": result.clarification_question, "session_id": session.session_id}

    session.active_flow = state_machine.transition(session.active_flow, result)
    reply = await _dispatch(result, message, session, brand)
    return {"reply": reply["reply"], "session_id": session.session_id}


async def build_shadow_record(message: str, session, brand: Any, v2_reply: str) -> dict[str, Any]:
    start = time.perf_counter()
    old_intent = v2_intent.detect_intent(message, brand)
    result = interpreter.interpret(message, session.history[-5:], session.data)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    # Predict v3 response in a deep-copied session snapshot.
    snapshot = copy.deepcopy(session)
    would = await _dispatch(result, message, snapshot, brand)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session.session_id,
        "message": _mask_message(message),
        "v2_intent": old_intent,
        "v3_intent": result.intent,
        "v3_confidence": result.confidence,
        "v3_entities": result.entities,
        "v3_needs_clarification": result.needs_clarification,
        "latency_ms": latency_ms,
        "v2_response_preview": _preview(v2_reply),
        "v3_would_respond": _preview(would.get("reply", "")),
        "final_handler": result.intent.lower(),
    }


def log_shadow_record(record: dict[str, Any]) -> None:
    try:
        _SHADOW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _SHADOW_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def build_shadow_record_sync(message: str, session, brand: Any, v2_reply: str) -> dict[str, Any]:
    return asyncio.run(build_shadow_record(message, session, brand, v2_reply))


@router.post("", response_model=ChatResponse)
async def chat_v3_endpoint(payload: ChatRequest) -> ChatResponse:
    # Disabled by default.
    if not _settings.v3_enabled or _settings.chat_engine != "v3":
        return ChatResponse(reply="V3 endpoint je izklopljen. Uporabite /v2/chat.", session_id=payload.session_id)
    brand = get_brand()
    result = await handle_message(payload.message, payload.session_id or "", brand)
    return ChatResponse(reply=str(result["reply"]), session_id=str(result["session_id"]))
