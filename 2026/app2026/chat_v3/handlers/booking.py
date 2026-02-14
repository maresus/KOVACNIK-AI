from __future__ import annotations

from typing import Any

from app2026.chat.flows import reservation as reservation_flow
from app2026.chat_v3.schemas import InterpretResult


async def execute(result: InterpretResult, message: str, session: Any, brand: Any) -> dict[str, str]:
    if result.intent in {"BOOKING_ROOM", "BOOKING_TABLE"}:
        return {"reply": reservation_flow.start(session, message, brand)}
    if result.intent == "CONTINUE_FLOW":
        return {"reply": reservation_flow.handle(session, message, brand)}
    if result.intent == "CANCEL":
        state = session.data.get("reservation")
        if isinstance(state, dict):
            reservation_flow.reset_reservation_state(state)
        session.active_flow = None
        session.step = None
        return {"reply": "Rezervacijo sem preklical. Kako vam lahko še pomagam?"}
    if result.intent == "CONFIRM":
        return {"reply": reservation_flow.handle(session, "da", brand)}
    return {"reply": reservation_flow.handle(session, message, brand)}
