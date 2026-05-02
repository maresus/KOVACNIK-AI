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


_SUGGEST_FORM_REPLY = {
    "room": (
        "Seveda, sobe so na voljo tudi med tednom! 😊\n\n"
        "Najhitreje je, če izpolnite **rezervacijski obrazec** (gumb spodaj) — "
        "po oddaji vas kontaktiramo in potrdimo termin.\n\n"
        "Če raje nadaljujete v pogovoru, mi sporočite datum prihoda, število oseb in kontaktne podatke."
    ),
    "table": (
        "Seveda! 😊 Najhitreje je, če izpolnite **rezervacijski obrazec** (gumb spodaj) — "
        "po oddaji vas kontaktiramo in potrdimo termin.\n\n"
        "Če raje nadaljujete v pogovoru, mi sporočite datum (sob/ned), uro in število oseb."
    ),
}

_PREFILL_FORM_REPLY = {
    "room": "Odlično! Odprl sem rezervacijski obrazec in že vpisal podatke ki ste jih navedli. Preverite, dopolnite kontakt in oddate. 😊",
    "table": "Odlično! Odprl sem rezervacijski obrazec in že vpisal podatke ki ste jih navedli. Preverite, dopolnite kontakt in oddate. 😊",
}


def _build_prefill(entities: dict) -> dict | None:
    """Iz entitet sestavi prefill slovar za widget formo."""
    if not entities.get("_has_date"):
        return None
    prefill: dict = {}
    if entities.get("date"):
        # Pretvori v ISO obliko za date input (YYYY-MM-DD)
        from datetime import datetime as _dt
        raw = entities["date"]
        for fmt in ("%d.%m.%Y", "%d.%m."):
            try:
                d = _dt.strptime(raw, fmt)
                if fmt == "%d.%m.":
                    d = d.replace(year=_dt.now().year)
                prefill["date"] = d.strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
    if entities.get("nights"):
        prefill["nights"] = int(entities["nights"])
    adults = entities.get("adults")
    kids = entities.get("kids") or 0
    if adults:
        prefill["adults"] = int(adults)
    if kids:
        prefill["children"] = int(kids)
        if entities.get("kids_ages"):
            prefill["children_ages"] = str(entities["kids_ages"])
    return prefill if prefill else None


async def execute(result: InterpretResult, message: str, session: Any, brand: Any) -> dict[str, str]:
    if result.intent in {"BOOKING_ROOM", "BOOKING_TABLE"}:
        res_type = "room" if result.intent == "BOOKING_ROOM" else "table"
        entities = result.entities or {}

        # Already mid-flow: continue step-by-step.
        if session.active_flow == "reservation":
            _prefill_state_from_entities(session, result.intent, entities)
            return {"reply": reservation_flow.start(session, message, brand)}

        # Inquiry only (no specific date) → suggest form in text, don't auto-open
        if entities.get("_inquiry_only"):
            return {"reply": _SUGGEST_FORM_REPLY[res_type]}

        # Has concrete date/people → open form and pre-fill
        prefill = _build_prefill(entities)
        if prefill:
            _prefill_state_from_entities(session, result.intent, entities)
            return {
                "reply": _PREFILL_FORM_REPLY[res_type],
                "action": "open_booking_form",
                "booking_type_hint": res_type,
                "booking_prefill": prefill,
            }

        # Has booking intent but no extractable date → suggest form
        return {"reply": _SUGGEST_FORM_REPLY[res_type]}
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
