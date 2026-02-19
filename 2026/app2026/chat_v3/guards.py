from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[\d\s+()./-]{6,}$")
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?\b")
# Month-name pattern for Slovene/English dates: "15. avgusta", "julij 25", "August 10th"
_SL_MONTH_RE = re.compile(
    r"\b\d{1,2}\s*(?:ga|\.?)?\s*(?:januar|februar|marc|april|maja?|junij|julij|avgust|septemb|oktob|novemb|decemb)\w*\b"
    r"|\b(?:januar|februar|marc|april|maj|junij|julij|avgust|septemb|oktob|novemb|decemb)\w*\s+\d{1,2}\b"
    r"|\b\d{1,2}\s*(?:st|nd|rd|th)?\s*(?:january|february|march|april|may|june|july|august|september|october|november|december)\b"
    r"|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\b\d{1,3}\b")
TIME_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\b|\b\d{1,2}\s*(ura|h)\b", re.IGNORECASE)

YES_WORDS = {"da", "ja", "yes", "y", "potrjujem", "seveda"}
NO_WORDS = {"ne", "no", "n", "ne hvala"}

# Words that, when present in input, suggest an off-topic question (topic switch).
# We let the LLM + mid-booking continuation logic handle those.
_QUESTION_WORDS = frozenset({
    "kdo", "kje", "kaj", "kdaj", "kako", "kateri", "katero", "katerih",
    "zakaj", "ali imate", "imate", "ponujate", "povejte",
})

_STEP_TO_FIELD = {
    "awaiting_email": "email",
    "awaiting_phone": "phone",
    "awaiting_room_date": "date",
    "awaiting_table_date": "date",
    "awaiting_date": "date",
    "awaiting_people": "guests",
    "awaiting_table_people": "guests",
    "awaiting_confirmation": "confirm",
    # Steps that accept "ne" as valid in-flow answer — must NOT become CANCEL via LLM.
    "awaiting_note": "note",
    "awaiting_dinner": "dinner",
    "awaiting_dinner_count": "dinner_count",
    "awaiting_kids_info": "kids_info",
    # Numeric / pass-through steps also at risk of LLM misclassification.
    "awaiting_nights": "nights",
    "awaiting_kids_ages": "kids_ages",
    # Text-based steps where the booking flow must receive the raw input directly.
    "awaiting_room_location": "location",
    "awaiting_table_location": "location",
    "awaiting_name": "booking_name",
    "awaiting_table_time": "table_time",
    "awaiting_type": "booking_type",
    "awaiting_table_event_type": "event_type",
}


def _is_topic_switch(lowered: str) -> bool:
    """Return True if the input looks like an off-topic question during booking."""
    if "?" in lowered:
        return True
    tokens = set(re.findall(r"[a-zšžčćđ]+", lowered))
    return bool(tokens & _QUESTION_WORDS)


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

    active_flow, pending_field = _extract_pending(session)

    # ── Active booking flow ───────────────────────────────────────────────────
    # All known reservation steps are now in _STEP_TO_FIELD, so pending_field
    # is set for every booking step.  Handle each field type here before any
    # menu shortcut can fire.
    if active_flow and pending_field:

        # ── Pattern-specific matchers ─────────────────────────────────────────
        if pending_field == "email":
            if EMAIL_RE.fullmatch(text):
                return {"action": "continue_flow", "field": "email", "value": text}

        elif pending_field == "phone":
            if PHONE_RE.fullmatch(text):
                return {"action": "continue_flow", "field": "phone", "value": text}

        elif pending_field == "date":
            if DATE_RE.search(text) or _SL_MONTH_RE.search(text):
                return {"action": "continue_flow", "field": "date", "value": text}

        elif pending_field == "guests":
            m = NUMBER_RE.search(text)
            if m:
                return {"action": "continue_flow", "field": "guests", "value": int(m.group(0))}

        elif pending_field == "confirm":
            if lowered in YES_WORDS:
                return {"action": "continue_flow", "field": "confirm", "value": True}
            if lowered in NO_WORDS:
                return {"action": "continue_flow", "field": "confirm", "value": False}

        elif pending_field == "note":
            # Any text valid: booking flow handles "ne"/"nič" as skip.
            return {"action": "continue_flow", "field": "note", "value": text}

        elif pending_field == "dinner":
            if lowered in YES_WORDS:
                return {"action": "continue_flow", "field": "dinner", "value": True}
            if lowered in NO_WORDS:
                return {"action": "continue_flow", "field": "dinner", "value": False}

        elif pending_field == "dinner_count":
            m = NUMBER_RE.search(text)
            if m:
                return {"action": "continue_flow", "field": "dinner_count", "value": int(m.group(0))}

        elif pending_field == "kids_info":
            # "ne" / "brez" / numbers / ages — all valid; booking flow validates.
            return {"action": "continue_flow", "field": "kids_info", "value": text}

        elif pending_field == "nights":
            # "4 nočitve", "3", "dva" etc. — pass through; booking flow validates.
            # Topic-switch questions (? / question words) → let LLM + continuation handle.
            if not _is_topic_switch(lowered):
                return {"action": "continue_flow", "field": "nights", "value": text}

        elif pending_field == "kids_ages":
            return {"action": "continue_flow", "field": "kids_ages", "value": text}

        elif pending_field == "table_time":
            # Any time-like text; booking flow validates.
            return {"action": "continue_flow", "field": "table_time", "value": text}

        elif pending_field in ("location", "booking_name", "booking_type", "event_type"):
            # Text-based steps: pass through UNLESS it looks like an off-topic question.
            if not _is_topic_switch(lowered):
                return {"action": "continue_flow", "field": pending_field, "value": text}
            # Looks like a topic switch → return None → LLM + mid-booking continuation.

        # Field didn't match / question detected → do NOT fall through to menu shortcut.
        return None

    # ── Menu follow-up shortcut ───────────────────────────────────────────────
    # Only runs when there is NO active booking flow.
    history = getattr(session, "history", []) or []
    recent = " ".join(
        (item.get("content", "") for item in history[-3:] if isinstance(item, dict))
    ).lower()
    if any(k in recent for k in ("4-hodni", "5-hodni", "6-hodni", "7-hodni", "degustacijski meniji")):
        if lowered in {"4", "5", "6", "7"}:
            return {
                "action": "menu_detail",
                "field": "courses",
                "value": int(lowered),
            }

    return None
