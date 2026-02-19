from __future__ import annotations

import re
import threading
from datetime import datetime
from typing import Any, Optional

from app.services.email_service import send_admin_notification, send_guest_confirmation
from app2026.chat.flows.booking_flow import handle_reservation_flow as legacy_handle_reservation_flow
from app.services.reservation_service import ReservationService


RESERVATION_PENDING_MESSAGE = """
✅ **Vaše povpraševanje je PREJETO** in čaka na potrditev.

📧 Potrditev boste prejeli po e-pošti.
⏳ Odgovorili vam bomo v najkrajšem možnem času.

⚠️ Preverite tudi **SPAM/VSILJENO POŠTO**.
"""

EXIT_KEYWORDS = {
    "konec",
    "stop",
    "prekini",
    "nehaj",
    "pustimo",
    "pozabi",
    "ne rabim",
    "ni treba",
    "drugič",
    "drugic",
    "cancel",
    "quit",
    "exit",
    "pusti",
}


def _blank_reservation_state() -> dict[str, Optional[str | int]]:
    return {
        "step": None,
        "type": None,
        "date": None,
        "time": None,
        "nights": None,
        "rooms": None,
        "people": None,
        "adults": None,
        "kids": None,
        "kids_ages": None,
        "name": None,
        "phone": None,
        "email": None,
        "location": None,
        "available_locations": None,
        "language": None,
        "dinner_people": None,
        "note": None,
        "availability": None,
        "session_id": None,
    }


_reservation_service = ReservationService()


def _send_reservation_emails_async(payload: dict) -> None:
    def _worker() -> None:
        try:
            send_guest_confirmation(payload)
            send_admin_notification(payload)
        except Exception as exc:
            print(f"[EMAIL] Async send failed: {exc}")

    threading.Thread(target=_worker, daemon=True).start()


def start(session: Any, message: str, brand: Any) -> str:
    session.active_flow = "reservation"
    return handle(session, message, brand)


def handle(session: Any, message: str, brand: Any) -> str:
    state = session.data.get("reservation")
    if not isinstance(state, dict):
        state = _blank_reservation_state()
        session.data["reservation"] = state
    state["session_id"] = session.session_id
    if not state.get("language"):
        state["language"] = detect_language(message)

    reply = legacy_handle_reservation_flow(
        message=message,
        state=state,
        detect_language=detect_language,
        translate_response=translate_response,
        parse_reservation_type=parse_reservation_type,
        room_intro_text=lambda: room_intro_text(brand),
        table_intro_text=lambda: table_intro_text(brand),
        reset_reservation_state=reset_reservation_state,
        is_affirmative=is_affirmative,
        reservation_service=_reservation_service,
        validate_reservation_rules_fn=validate_reservation_rules_bound,
        advance_after_room_people_fn=advance_after_room_people_bound,
        handle_room_reservation_fn=handle_room_reservation_bound,
        handle_table_reservation_fn=handle_table_reservation_bound,
        exit_keywords=EXIT_KEYWORDS,
        detect_reset_request=detect_reset_request,
        send_reservation_emails_async=_send_reservation_emails_async,
        reservation_pending_message=RESERVATION_PENDING_MESSAGE,
    )

    session.step = state.get("step")
    if state.get("step") is None:
        session.active_flow = None
    return reply


def reset_reservation_state(state: dict[str, Optional[str | int]]) -> None:
    state.clear()
    state.update(_blank_reservation_state())


def detect_language(message: str) -> str:
    lowered = message.lower()
    german_words = [
        "ich",
        "sie",
        "wir",
        "haben",
        "möchte",
        "möchten",
        "können",
        "bitte",
        "zimmer",
        "tisch",
        "reservierung",
        "reservieren",
        "buchen",
        "wann",
        "wie",
        "was",
        "wo",
        "gibt",
        "guten tag",
        "hallo",
        "danke",
        "preis",
        "kosten",
        "essen",
        "trinken",
        "wein",
        "frühstück",
        "abendessen",
        "mittag",
        "nacht",
        "übernachtung",
    ]
    german_count = sum(1 for word in german_words if word in lowered)
    english_pronoun = 1 if re.search(r"\bi\b", lowered) else 0
    english_words = [
        " we ",
        "you",
        "have",
        "would",
        " like ",
        "want",
        "can",
        "room",
        "table",
        "reservation",
        "reserve",
        "book",
        "booking",
        "when",
        "how",
        "what",
        "where",
        "there",
        "hello",
        "hi ",
        "thank",
        "price",
        "cost",
        "food",
        "drink",
        "wine",
        "menu",
        "breakfast",
        "dinner",
        "lunch",
        "night",
        "stay",
        "please",
    ]
    english_count = english_pronoun + sum(1 for word in english_words if word in lowered)
    if german_count >= 2:
        return "de"
    if english_count >= 2:
        return "en"
    if german_count == 1 and english_count == 0:
        return "de"
    if english_count == 1 and german_count == 0:
        return "en"
    return "si"


def translate_response(text: str, target_lang: str) -> str:
    # Keep v2 deterministic for now; no translation in flow.
    return text


def is_affirmative(message: str) -> bool:
    lowered = message.strip().lower()
    return lowered in {
        "da",
        "ja",
        "seveda",
        "potrjujem",
        "potrdim",
        "potrdi",
        "zelim",
        "želim",
        "zelimo",
        "želimo",
        "rad bi",
        "rada bi",
        "bi",
        "yes",
        "oui",
        "ok",
        "okej",
        "okey",
        "sure",
        "yep",
        "yeah",
    }


def detect_reset_request(message: str) -> bool:
    lowered = message.lower()
    reset_words = [
        "reset",
        "začni znova",
        "zacni znova",
        "od začetka",
        "od zacetka",
        "zmota",
        "zmoto",
        "zmotu",
        "zmotil",
        "zmotila",
        "zgresil",
        "zgrešil",
        "zgrešila",
        "zgresila",
        "napačno",
        "narobe",
        "popravi",
        "nova rezervacija",
    ]
    exit_words = [
        "konec",
        "stop",
        "prekini",
        "nehaj",
        "pustimo",
        "pozabi",
        "ne rabim",
        "ni treba",
        "drugič",
        "drugic",
        "cancel",
        "quit",
        "exit",
        "pusti",
    ]
    return any(word in lowered for word in reset_words + exit_words)


def parse_reservation_type(message: str) -> Optional[str]:
    lowered = message.lower()

    def _has_term(term: str) -> bool:
        if " " in term:
            return term in lowered
        return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered) is not None

    room_keywords = [
        "soba",
        "sobe",
        "sobo",
        "sobi",
        "sob",
        "nočitev",
        "nocitev",
        "nocitiv",
        "nocitiva",
        "prenocitev",
        "noč",
        "prenočiti",
        "prespati",
        "prisel",
        "prišel",
        "ostali",
        "ostala",
        "vikend",
        "room",
        "rooms",
        "stay",
        "overnight",
        "night",
        "nights",
        "accommodation",
        "sleep",
        "zimmer",
        "übernachtung",
        "übernachten",
        "nacht",
        "schlafen",
        "unterkunft",
    ]
    if any(_has_term(word) for word in room_keywords):
        return "room"

    table_keywords = [
        "miza",
        "mizo",
        "mize",
        "rezervacija mize",
        "kosilo",
        "večerja",
        "kosilu",
        "mizico",
        "jest",
        "jesti",
        "table",
        "lunch",
        "dinner",
        "meal",
        "eat",
        "dining",
        "restaurant",
        "tisch",
        "mittagessen",
        "abendessen",
        "essen",
        "speisen",
        "restaurant",
    ]
    if any(_has_term(word) for word in table_keywords):
        return "table"
    return None


def room_intro_text(brand: Any) -> str:
    return (
        "Sobe: ALJAŽ (2+2), JULIJA (2+2), ANA (2+2).\n\n"
        "Minimalno 3 nočitve v juniju/juliju/avgustu, 2 nočitvi v ostalih mesecih.\n\n"
        "Prijava 14:00, odjava 10:00, zajtrk 8:00–9:00, večerja 18:00 "
        "(pon/torki brez večerij).\n\n"
        "Sobe so klimatizirane, Wi-Fi je brezplačen, zajtrk je vključen."
    )


def table_intro_text(brand: Any) -> str:
    return (
        "Kosila ob sobotah in nedeljah med 12:00 in 20:00.\n\n"
        "Zadnji prihod na kosilo je ob 15:00.\n\n"
        "Jedilnici: 'Pri peči' (15 oseb) in 'Pri vrtu' (35 oseb)."
    )


def validate_reservation_rules_bound(arrival_date_str: str, nights: int):
    from app2026.chat.flows.booking_flow import validate_reservation_rules

    return validate_reservation_rules(arrival_date_str, nights, _reservation_service)


def advance_after_room_people_bound(reservation_state: dict[str, Optional[str | int]], _service: Any = None) -> str:
    from app2026.chat.flows.booking_flow import advance_after_room_people

    return advance_after_room_people(reservation_state, _reservation_service)


def handle_room_reservation_bound(
    message: str,
    state: dict[str, Optional[str | int]],
    translate_response: Any,
    reservation_service: Any,
    is_affirmative: Any,
    validate_reservation_rules_fn: Any,
    advance_after_room_people_fn: Any,
    reset_reservation_state: Any,
    send_reservation_emails_async: Any,
    reservation_pending_message: str,
) -> str:
    from app2026.chat.flows.booking_flow import handle_room_reservation

    return handle_room_reservation(
        message,
        state,
        translate_response,
        reservation_service,
        is_affirmative,
        validate_reservation_rules_fn,
        advance_after_room_people_fn,
        reset_reservation_state,
        send_reservation_emails_async,
        reservation_pending_message,
    )


def handle_table_reservation_bound(
    message: str,
    state: dict[str, Optional[str | int]],
    translate_response: Any,
    reservation_service: Any,
    reset_reservation_state: Any,
    is_affirmative: Any,
    send_reservation_emails_async: Any,
    reservation_pending_message: str,
) -> str:
    from app2026.chat.flows.booking_flow import handle_table_reservation

    return handle_table_reservation(
        message,
        state,
        translate_response,
        reservation_service,
        reset_reservation_state,
        is_affirmative,
        send_reservation_emails_async,
        reservation_pending_message,
    )
