from __future__ import annotations

from app2026.chat_v3.schemas import InterpretResult


def transition(current_flow: str | None, result: InterpretResult) -> str | None:
    if result.intent in {"BOOKING_ROOM", "BOOKING_TABLE", "CONTINUE_FLOW", "CONFIRM"}:
        return "reservation"
    if result.intent == "CANCEL":
        return None
    return current_flow
