from __future__ import annotations

from typing import Any

from app2026.chat.flows import reservation as reservation_flow
from app2026.chat_v3.schemas import InterpretResult


def _prefill_state_from_entities(session: Any, intent: str, entities: dict) -> None:
    """Prednapolni reservation state z entitetami ki jih je interpreter že ekstrahiral."""
    state = session.data.get("reservation")
    if not isinstance(state, dict):
        from app2026.chat.flows.reservation import _blank_reservation_state
        state = _blank_reservation_state()
        session.data["reservation"] = state

    # Tip rezervacije
    if intent == "BOOKING_ROOM" and not state.get("type"):
        state["type"] = "room"
    elif intent == "BOOKING_TABLE" and not state.get("type"):
        state["type"] = "table"

    # Entitete iz interpreterja
    if entities.get("date") and not state.get("date"):
        state["date"] = entities["date"]
    if entities.get("month") and not state.get("date"):
        state["date"] = entities["month"]
    if entities.get("people") and not state.get("people"):
        try:
            state["people"] = int(entities["people"])
        except (ValueError, TypeError):
            pass
    if entities.get("nights") and not state.get("nights"):
        try:
            state["nights"] = int(entities["nights"])
        except (ValueError, TypeError):
            pass
    if entities.get("time") and not state.get("time"):
        state["time"] = entities["time"]


async def execute(result: InterpretResult, message: str, session: Any, brand: Any) -> dict[str, str]:
    if result.intent in {"BOOKING_ROOM", "BOOKING_TABLE"}:
        _prefill_state_from_entities(session, result.intent, result.entities or {})
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
