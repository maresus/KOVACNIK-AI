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
    "kaja": {
        "name": "Kaja",
        "role": "partnerica Aljaža",
        "notes": ["s svojo dobro voljo vedno razvedri goste"],
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

# Online shop / domači izdelki
SHOP = {
    "url": "https://kovacnik.com/kovacnikova-spletna-trgovina/",
    "katalog_url": "https://kovacnik.com/katalog/",
    "categories": {
        "marmelade": {
            "label": "Marmelade",
            "price_from": 5.50,
            "examples": ["Jagoda", "Malina", "Aronija", "Božična", "Stara brajda", "Jabolko & cimet"],
        },
        "namazi": {
            "label": "Namazi",
            "items": [
                {"name": "Bučni namaz, 212 ml", "price": 7.00, "url": "https://kovacnik.com/izdelek/bucni-namaz-212-ml/"},
                {"name": "Čemažev pesto, 212 ml", "price": 5.50, "url": "https://kovacnik.com/izdelek/cemazev-pesto-212-ml/"},
                {"name": "Jetrna paštetka, 212 ml", "price": 5.50, "url": "https://kovacnik.com/izdelek/jetrna-pastetka-212-ml/"},
            ],
        },
        "likerji": {
            "label": "Likerji in žganje",
            "items": [
                {"name": "Borovničev liker, 350 ml", "price": 13.00, "url": "https://kovacnik.com/izdelek/borovnicev-liker-350-ml/"},
                {"name": "Žajbljev liker, 350 ml", "price": 13.00, "url": "https://kovacnik.com/izdelek/zajbljev-liker-350-ml/"},
                {"name": "Tepkovec, 350 ml", "price": 15.00, "url": "https://kovacnik.com/izdelek/tepkovec-350-ml/"},
            ],
        },
        "sirupi": {
            "label": "Sokovi in sirupi",
            "items": [
                {"name": "Bezgov sirup, 500 ml", "price": 6.50, "url": "https://kovacnik.com/izdelek/bezgov-sirup-500-ml/"},
                {"name": "Metin sirup, 500 ml", "price": 6.50, "url": "https://kovacnik.com/izdelek/metin-sirup-500-ml/"},
            ],
        },
        "mesni_izdelki": {
            "label": "Mesni izdelki",
            "items": [
                {"name": "Pohorska bunka (500 g)", "price_range": "18–21 €", "url": "https://kovacnik.com/izdelek/pohorska-bunka-500-g/"},
                {"name": "Suha salama, 650 g", "price": 16.00, "url": "https://kovacnik.com/izdelek/suha-salama-200-g/"},
                {"name": "Hišna suha klobasa, 180 g", "price": 7.00, "url": "https://kovacnik.com/izdelek/hisna-suha-klobasa/"},
            ],
        },
        "darilni_paketi": {
            "label": "Darilni paketi",
            "items": [
                {"name": "Paket babice Angelce", "price": 19.50, "url": "https://kovacnik.com/izdelek/paket-babice-angelce-zeliscni-c/"},
                {"name": "Paket gospodarja Danila (bunka, tepkovec)", "price": 43.50, "url": "https://kovacnik.com/izdelek/paket-gospodarja-danila-tepkovec/"},
                {"name": "Kajin paket (sirup, čaj, marmelada)", "price": 17.50, "url": "https://kovacnik.com/izdelek/paket-tete-barbke-na-slano-bucn/"},
                {"name": "Aljažev paket", "price": 22.00, "url": "https://kovacnik.com/izdelek/aljazev-paket-jabolcni-sok-marmelada-suha-klobasa/"},
                {"name": "Anin paket (tris marmelad)", "price": 18.00, "url": "https://kovacnik.com/izdelek/anin-paket-3-marmelade/"},
                {"name": "Julijin paket", "price": 19.00, "url": "https://kovacnik.com/izdelek/julijin-paket-metin-sirup-marmelada-bucni-namaz/"},
                {"name": "Vaš Kovačnikov paket (po meri)", "price_from": 10.50, "url": "https://kovacnik.com/izdelek/sestavi-svoj-kovacnikov-paket/"},
            ],
        },
        "darilni_boni": {
            "label": "Darilni boni",
            "items": [
                {"name": "Darilni bon 10 €", "price": 10.00, "url": "https://kovacnik.com/izdelek/darilni-bon-10-eur/"},
                {"name": "Darilni bon 20 €", "price": 20.00, "url": "https://kovacnik.com/izdelek/darilni-bon-20-eur/"},
                {"name": "Darilni bon 50 €", "price": 50.00, "url": "https://kovacnik.com/izdelek/darilni-bon-50-eur/"},
            ],
        },
        "sladke_dobrote": {
            "label": "Sladke dobrote",
            "items": [
                {"name": "Piškoti gospodinje Barbare, 250 g", "price": 8.00, "url": "https://kovacnik.com/izdelek/piskoti-tete-barbke-250-g/"},
                {"name": "Pohorska gibanica babice Angelce (10 kosov)", "price": 40.00, "url": "https://kovacnik.com/izdelek/pohorska-gibanica-babice-angelc/"},
                {"name": "Orehova potica, 1 kg", "price": 30.00, "url": "https://kovacnik.com/izdelek/slovenska-orehova-potica-1-kg/"},
            ],
        },
        "caji": {
            "label": "Čaji",
            "items": [
                {"name": "Zeliščni čaj babice Angelce, 20 g", "price": 4.00, "url": "https://kovacnik.com/izdelek/zeliscni-caj-babice-angelce-20-/"},
                {"name": "Božični čaj babice Angelce, 60 g", "price": 4.00, "url": "https://kovacnik.com/izdelek/bozicni-caj-babice-angelce/"},
            ],
        },
    },
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

