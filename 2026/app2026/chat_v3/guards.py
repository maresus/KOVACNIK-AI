from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[\d\s+()./-]{6,}$")
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?\b")
NUMBER_RE = re.compile(r"\b\d{1,3}\b")

YES_WORDS = {"da", "ja", "yes", "y", "potrjujem", "seveda"}
NO_WORDS = {"ne", "no", "n", "ne hvala"}

_STEP_TO_FIELD = {
    "awaiting_email": "email",
    "awaiting_phone": "phone",
    "awaiting_room_date": "date",
    "awaiting_table_date": "date",
    "awaiting_date": "date",
    "awaiting_people": "guests",
    "awaiting_table_people": "guests",
    "awaiting_confirmation": "confirm",
}


def _extract_pending(session: Any) -> tuple[str | None, str | None]:
    active_flow = getattr(session, "active_flow", None)
    pending_field = None
    step = getattr(session, "step", None)

    data = getattr(session, "data", {}) or {}
    if isinstance(data, dict):
        pending_field = data.get("pending_field")
        if not step:
            reservation = data.get("reservation")
            if isinstance(reservation, dict):
                step = reservation.get("step")
                if not active_flow:
                    active_flow = "reservation"

    if not pending_field and step:
        pending_field = _STEP_TO_FIELD.get(step)
    return active_flow, pending_field


def check(message: str, session: Any) -> dict[str, Any] | None:
    text = (message or "").strip()
    lowered = text.lower()

    # Menu follow-up: after a menu summary, plain number means menu detail.
    # This check runs regardless of active_flow so it always works.
    history = getattr(session, "history", []) or []
    recent = " ".join((item.get("content", "") for item in history[-3:] if isinstance(item, dict))).lower()
    if any(k in recent for k in ("4-hodni", "5-hodni", "6-hodni", "7-hodni", "degustacijski meniji")):
        if lowered in {"4", "5", "6", "7"}:
            return {
                "action": "menu_detail",
                "field": "courses",
                "value": int(lowered),
            }

    active_flow, pending_field = _extract_pending(session)

    if not active_flow or not pending_field:
        return None

    if pending_field == "email" and EMAIL_RE.fullmatch(text):
        return {"action": "continue_flow", "field": "email", "value": text}
    if pending_field == "phone" and PHONE_RE.fullmatch(text):
        return {"action": "continue_flow", "field": "phone", "value": text}
    if pending_field == "date" and DATE_RE.search(text):
        return {"action": "continue_flow", "field": "date", "value": text}
    if pending_field == "guests":
        match = NUMBER_RE.search(text)
        if match:
            return {"action": "continue_flow", "field": "guests", "value": int(match.group(0))}
    if pending_field == "confirm":
        if lowered in YES_WORDS:
            return {"action": "continue_flow", "field": "confirm", "value": True}
        if lowered in NO_WORDS:
            return {"action": "continue_flow", "field": "confirm", "value": False}

    return None
