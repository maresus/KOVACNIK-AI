"""
Router V2 - klasifikacija sporočil v standardiziran JSON.
Ne izvaja FSM; samo ugotavlja intent in osnovne entitete.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _extract_date(text: str) -> Optional[str]:
    match = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b", text)
    if not match:
        return None
    day, month, year = match.groups()
    year = year if len(year) == 4 else f"20{year.zfill(2)}"
    return f"{day.zfill(2)}.{month.zfill(2)}.{year}"


def _extract_time(text: str) -> Optional[str]:
    match = re.search(r"\b(\d{1,2})[:.](\d{2})\b", text)
    if not match:
        return None
    hour, minute = match.groups()
    return f"{hour.zfill(2)}:{minute}"


def _extract_people(text: str) -> Optional[int]:
    nums = re.findall(r"\b(\d{1,2})\b", text)
    if nums:
        try:
            return int(nums[-1])
        except ValueError:
            return None
    return None


def _detect_info_intent(text: str) -> Optional[str]:
    if any(w in text for w in ["odpiralni", "kdaj ste odprti", "delovni čas", "odprti", "odprite"]):
        return "odpiralni_cas"
    if "zajtrk" in text and "večerj" not in text:
        return "zajtrk"
    if any(w in text for w in ["večerja", "vecerja", "cena večerje", "cena vecerje", "večerjo"]):
        return "vecerja"
    if any(w in text for w in ["cena sobe", "cenik", "koliko stane noč", "nočitev", "nocitev"]):
        return "cena_sobe"
    if any(w in text for w in ["klima", "klimatiz"]):
        return "klima"
    if any(w in text for w in ["wifi", "wi-fi", "internet"]):
        return "wifi"
    if any(w in text for w in ["prijava", "odjava", "check in", "check out"]):
        return "prijava_odjava"
    if any(w in text for w in ["parkir", "parking"]):
        return "parking"
    if any(w in text for w in ["pes", "mačk", "žival", "ljubljenč"]):
        return "zivali"
    if any(w in text for w in ["plačilo", "gotovina", "kartic"]):
        return "placilo"
    if any(w in text for w in ["minimal", "min nočit", "najmanj noč", "min noce"]):
        return "min_nocitve"
    if any(w in text for w in ["jedilnik", "menij", "meniju", "menu", "koslo", "kaj ponujate", "kaj strežete"]):
        return "jedilnik"
    if any(w in text for w in ["alergij", "gluten", "lakto", "vegan"]):
        return "alergije"
    if any(w in text for w in ["kmetij", "kmetijo"]):
        return "kmetija"
    if "gibanica" in text:
        return "gibanica"
    if any(w in text for w in ["marmelad", "liker", "bunka", "izdelek", "trgovin", "katalog"]):
        return "izdelki"
    return None


def _detect_product_intent(text: str) -> Optional[str]:
    if any(w in text for w in ["marmelad", "džem", "dzem", "jagod", "malin"]):
        return "marmelada"
    if any(w in text for w in ["liker", "žgan", "zgan", "borovnič", "orehov", "tepk"]):
        return "liker"
    if "bunka" in text:
        return "bunka"
    if any(w in text for w in ["izdelek", "trgovin", "katalog", "prodajate"]):
        return "izdelki_splosno"
    return None


def _detect_booking_intent(text: str, has_active_booking: bool) -> str:
    if has_active_booking:
        return "BOOKING_CONTINUE"

    booking_tokens = {
        "rezerv",
        "rezev",
        "rezer",
        "rezeriv",
        "rezerver",
        "rezerveru",
        "rezr",
        "rezrv",
        "rezrvat",
        "rezerveir",
        "reserv",
        "reservier",
        "book",
        "buking",
        "booking",
        "bukng",
    }
    room_tokens = {
        "soba",
        "sobe",
        "sobo",
        "room",
        "zimmer",
        "zimmern",
        "rum",
        "camer",
        "camera",
        "accom",
        "nocit",
        "nočit",
        "nočitev",
        "nocitev",
        "night",
    }
    table_tokens = {
        "miza",
        "mize",
        "mizo",
        "miz",
        "table",
        "tabl",
        "tabel",
        "tble",
        "tablle",
        "tafel",
        "tisch",
        "koslo",
        "kosilo",
        "vecerj",
        "veceja",
        "vecher",
        "dinner",
        "lunch",
    }

    has_booking = any(tok in text for tok in booking_tokens)
    has_room = any(tok in text for tok in room_tokens)
    has_table = any(tok in text for tok in table_tokens)

    if has_booking and has_room:
        return "BOOKING_ROOM"
    if has_booking and has_table:
        return "BOOKING_TABLE"
    if has_room and any(tok in text for tok in ["nocit", "noč", "night"]):
        return "BOOKING_ROOM"
    if has_table and any(tok in text for tok in ["oseb", "ob ", ":00"]):
        return "BOOKING_TABLE"
    return "GENERAL"


def route_message(
    message: str,
    has_active_booking: bool = False,
    booking_step: Optional[str] = None,
) -> Dict[str, Any]:
    text = message.lower()

    info_key = _detect_info_intent(text)
    product_key = _detect_product_intent(text)

    intent = _detect_booking_intent(text, has_active_booking)

    needs_soft_sell = info_key in {"sobe", "sobe_info", "vecerja", "cena_sobe", "min_nocitve", "kapaciteta_mize"}

    # is_interrupt: med aktivnim bookingom, a sprašuje info/product
    is_interrupt = False
    if has_active_booking and intent == "BOOKING_CONTINUE":
        pass
    elif has_active_booking and (info_key or product_key):
        is_interrupt = True
        intent = "INFO" if info_key else "PRODUCT"
    elif info_key or product_key:
        intent = "INFO" if info_key else "PRODUCT"

    entities: Dict[str, Any] = {}
    date = _extract_date(text)
    if date:
        entities["date"] = date
    time_val = _extract_time(text)
    if time_val:
        entities["time"] = time_val
    people = _extract_people(text)
    if people:
        entities["people_count"] = people
    if any(room in text for room in ["aljaz", "aljaž"]):
        entities["room_name"] = "ALJAZ"
    elif "julija" in text:
        entities["room_name"] = "JULIJA"
    elif "ana" in text:
        entities["room_name"] = "ANA"

    confidence = 0.9 if intent in {"INFO", "PRODUCT", "BOOKING_ROOM", "BOOKING_TABLE"} else 0.6

    return {
        "routing": {
            "intent": intent,
            "confidence": confidence,
            "is_interrupt": is_interrupt,
        },
        "context": {
            "info_key": info_key,
            "product_category": product_key,
            "needs_soft_sell": needs_soft_sell,
        },
        "entities": entities,
    }
