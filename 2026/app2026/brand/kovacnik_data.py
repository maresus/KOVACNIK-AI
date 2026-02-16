from __future__ import annotations

from typing import Any

from app2026.brand.kovacnik import (
    DISPLAY_NAME,
    FARM_INFO,
    ROOM_PRICING,
    SEASONAL_MENUS,
    WEEKLY_INFO,
    WEEKLY_MENUS,
    WINE_LIST,
)


BRAND = {
    "id": "kovacnik",
    "display_name": DISPLAY_NAME,
}

CONTACT = {
    "name": FARM_INFO.get("name"),
    "address": FARM_INFO.get("address"),
    "phone": FARM_INFO.get("phone"),
    "mobile": FARM_INFO.get("mobile"),
    "email": FARM_INFO.get("email"),
    "website": FARM_INFO.get("website"),
    "coordinates": (FARM_INFO.get("directions") or {}).get("coordinates"),
}

HOURS = {
    "restaurant": (FARM_INFO.get("opening_hours") or {}).get("restaurant"),
    "rooms": (FARM_INFO.get("opening_hours") or {}).get("rooms"),
    "shop": (FARM_INFO.get("opening_hours") or {}).get("shop"),
    "closed": (FARM_INFO.get("opening_hours") or {}).get("closed"),
}

POLICIES = {
    "check_in": ROOM_PRICING.get("check_in"),
    "check_out": ROOM_PRICING.get("check_out"),
    "breakfast_time": ROOM_PRICING.get("breakfast_time"),
    "dinner_time": ROOM_PRICING.get("dinner_time"),
    "min_nights_summer": ROOM_PRICING.get("min_nights_summer"),
    "min_nights_other": ROOM_PRICING.get("min_nights_other"),
    "breakfast_included": ROOM_PRICING.get("breakfast_included"),
}

ROOMS = {
    "aljaz": {
        "name": "ALJAŽ",
        "type": "soba",
        "capacity": "2+2",
        "price_per_person_eur": ROOM_PRICING.get("base_price"),
        "features": ["balkon", "klima", "wifi", "satelitska tv", "kopalnica s tušem"],
    },
    "julija": {
        "name": "JULIJA",
        "type": "soba",
        "capacity": "2+2",
        "price_per_person_eur": ROOM_PRICING.get("base_price"),
        "features": ["balkon", "klima", "wifi", "satelitska tv", "kopalnica s tušem"],
    },
    "ana": {
        "name": "ANA",
        "type": "soba",
        "capacity": "2+2",
        "price_per_person_eur": ROOM_PRICING.get("base_price"),
        "features": ["dve spalnici", "klima", "wifi", "satelitska tv", "kopalnica s tušem"],
    },
}

PERSONS = {
    "danilo": {
        "name": "Danilo Štern",
        "role": "gospodar",
        "phone": "041 878 474",
    },
    "barbara": {
        "name": "Barbara Štern",
        "role": "nosilka dopolnilne dejavnosti",
        "phone": "031 330 113",
    },
    "aljaz": {
        "name": "Aljaž",
        "role": "sin",
        "notes": ["mladi gospodar", "igra diatonično harmoniko"],
    },
    "julija": {
        "name": "Julija",
        "role": "hči",
        "notes": ["skrbi za živali", "animatorka na kmetiji"],
    },
    "angelca": {
        "name": "Angelca",
        "role": "babica / gospodinja",
    },
    "ana": {
        "name": "Ana",
        "role": "hči",
        "notes": ["najmlajša članica družine"],
    },
}

ANIMALS = {
    "malajka": {"name": "Malajka", "type": "konjiček"},
    "marsi": {"name": "Marsi", "type": "konjiček"},
    "pepa": {"name": "Pepa", "type": "pujska"},
    "carli": {"name": "Čarli", "type": "oven"},
    "luna": {"name": "Luna", "type": "psička"},
    "mucke": {"name": "Mucke", "type": "mačke"},
    "govedo": {"name": "Goveja čreda", "type": "govedo", "count": "okoli 40 glav"},
    "svinje": {"name": "Svinje", "type": "domače živali"},
    "racke": {"name": "Račke", "type": "domače živali"},
    "kokosi": {"name": "Kokoši", "type": "domače živali"},
}

WINES = {
    "sparkling": WINE_LIST.get("penece", []),
    "white": WINE_LIST.get("bela", []),
    "red": WINE_LIST.get("rdeca", []),
}

SEASONAL_WEEKEND_MENUS = {
    # Each entry keeps original normalized textual lines from brand config.
    (entry.get("label") or f"season_{idx}"): {
        "label": entry.get("label"),
        "months": sorted(list(entry.get("months") or [])),
        "items": list(entry.get("items") or []),
    }
    for idx, entry in enumerate(SEASONAL_MENUS, start=1)
}

WEEKDAY_DEGUSTATION = {
    "rules": {
        "days": WEEKLY_INFO.get("days"),
        "time": WEEKLY_INFO.get("time"),
        "min_people": WEEKLY_INFO.get("min_people"),
        "contact": WEEKLY_INFO.get("contact"),
    },
    "menus": {
        f"{courses}-hodni": {
            "name": menu.get("name"),
            "price_eur": menu.get("price"),
            "wine_pairing_eur": menu.get("wine_pairing"),
            "wine_glasses": menu.get("wine_glasses"),
            "courses": list(menu.get("courses") or []),
        }
        for courses, menu in WEEKLY_MENUS.items()
    },
}


# Deterministic disambiguation index:
# keys existing in both ROOMS and PERSONS must trigger clarification.
AMBIGUOUS_ENTITIES = sorted(set(ROOMS.keys()) & set(PERSONS.keys()))


def resolve_entity(name: str) -> dict[str, Any]:
    key = (name or "").strip().lower()
    in_rooms = key in ROOMS
    in_persons = key in PERSONS

    if in_rooms and in_persons:
        return {
            "action": "clarify",
            "question": f"Ali vas zanima soba {ROOMS[key]['name']} ali {PERSONS[key]['name']} iz družine?",
            "options": ["room", "person"],
        }
    if in_rooms:
        return {"type": "room", "data": ROOMS[key]}
    if in_persons:
        return {"type": "person", "data": PERSONS[key]}
    if key in ANIMALS:
        return {"type": "animal", "data": ANIMALS[key]}
    return {"type": "unknown"}

