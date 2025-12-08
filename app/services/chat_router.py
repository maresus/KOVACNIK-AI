import re
import random
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple
import uuid

from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.product_service import find_products
from app.services.reservation_service import ReservationService
from app.rag.rag_engine import rag_engine
from app.rag.knowledge_base import (
    CONTACT,
    KNOWLEDGE_CHUNKS,
    generate_llm_answer,
    search_knowledge,
)
from app.rag.chroma_service import answer_tourist_question, is_tourist_query

router = APIRouter(prefix="/chat", tags=["chat"])

last_wine_query: Optional[str] = None
PRODUCT_STEMS = {
    "salam",
    "klobas",
    "sir",
    "izdelek",
    "paket",
    "marmelad",
    "džem",
    "dzem",
    "liker",
    "namaz",
    "bunk",
}
RESERVATION_START_PHRASES = {
    # slovensko
    "rad bi rezerviral",
    "rad bi rezervirala",
    "želim rezervirati",
    "bi rezerviral",
    "bi rezervirala",
    "prosim rezervacijo",
    "prosim rezervirajte",
    "booking",
    "rezervacija mize",
    "rezervacija sobe",
    "rezervacija nočitve",
    "mizo bi",
    "sobo bi",
    "rezerviram mizo",
    "rezerviram sobo",
    "rezerviral bi mizo",
    "rezervirala bi mizo",
    # angleško
    "i want to book",
    "i would like to book",
    "i'd like to book",
    "book a room",
    "book a table",
    "reserve a room",
    "reserve a table",
    "reservation please",
    "make a reservation",
    "can i book",
    "can i reserve",
    "do you have rooms",
    "do you have a table",
    "available rooms",
    "room available",
    "table for",
    # nemško
    "ich möchte buchen",
    "ich möchte reservieren",
    "ich will buchen",
    "ich will reservieren",
    "zimmer buchen",
    "zimmer reservieren",
    "tisch buchen",
    "tisch reservieren",
    "reservierung bitte",
    "eine reservierung",
    "haben sie zimmer",
    "haben sie einen tisch",
    "zimmer frei",
    "tisch frei",
}
INFO_KEYWORDS = {
    "kje",
    "lokacija",
    "naslov",
    "kosilo",
    "vikend kosilo",
    "vikend",
    "hrana",
    "sob",
    "soba",
    "sobe",
    "nočitev",
    "nočitve",
    "zajtrk",
    "večerja",
    "otroci",
    "popust",
}
GREETING_KEYWORDS = {"živjo", "zdravo", "hej", "hello", "dober dan", "pozdravljeni"}
GOODBYE_KEYWORDS = {
    "hvala",
    "najlepša hvala",
    "hvala lepa",
    "adijo",
    "nasvidenje",
    "na svidenje",
    "čao",
    "ciao",
    "bye",
    "goodbye",
    "lp",
    "lep pozdrav",
    "se vidimo",
    "vidimo se",
    "srečno",
    "vse dobro",
    "lahko noč",
}
GREETINGS = [
    "Pozdravljeni! 😊 Kako vam lahko pomagam?",
    "Lepo pozdravljeni s Pohorja! Kako vam lahko pomagam danes?",
    "Dober dan! Vesela sem, da ste nas obiskali. S čim vam lahko pomagam?",
    "Pozdravljeni pri Kovačniku! 🏔️ Kaj vas zanima?",
]
THANKS_RESPONSES = [
    "Ni za kaj! Če boste imeli še kakšno vprašanje, sem tu. 😊",
    "Z veseljem! Lep pozdrav s Pohorja! 🏔️",
    "Ni problema! Vesela sem, če sem vam lahko pomagala.",
    "Hvala vam! Se vidimo pri nas! 😊",
]
UNKNOWN_RESPONSES = [
    "Ojoj, tega žal ne vem točno. 🤔 Lahko pa povprašam in vam sporočim - mi zaupate vaš email?",
    "Hmm, tega nimam v svojih zapiskih. Če mi pustite email, vam z veseljem poizvem in odgovorim.",
    "Na to vprašanje žal nimam odgovora pri roki. Lahko vam poizvem - mi zaupate vaš elektronski naslov?",
]
PRODUCT_FOLLOWUP_PHRASES = {
    "kaj pa",
    "kaj še",
    "katere",
    "katere pa",
    "kakšne",
    "še kaj",
}
INFO_FOLLOWUP_PHRASES = {
    "še kaj",
    "še kero",
    "še kero drugo",
    "kaj pa še",
    "pa še",
    "še kakšna",
    "še kakšno",
    "še kakšne",
    "še kaj drugega",
}

reservation_service = ReservationService()

# Osnovni podatki o kmetiji
FARM_INFO = {
    "name": "Turistična kmetija Kovačnik",
    "address": "Planica 9, 2313 Fram",
    "phone": "+386 2 656 10 80",
    "mobile": "+386 41 728 636",
    "email": "info@kovacnik.com",
    "website": "www.kovacnik.com",
    "location_description": "Na pohorski strani, nad Framom, približno 15 min iz doline",
    "parking": "Brezplačen parking ob hiši za 10+ avtomobilov",
    "directions": {
        "from_maribor": (
            "Iz avtoceste A1 (smer Maribor/Ljubljana) izvoz Fram. Pri semaforju v Framu proti cerkvi sv. Ane, "
            "naravnost skozi vas proti Kopivniku. V Kopivniku na glavni cesti zavijete desno (tabla Kmetija Kovačnik) "
            "in nadaljujete še približno 10 minut. Od cerkve v Framu do kmetije je slabih 15 minut."
        ),
        "coordinates": "46.5234, 15.6123",
    },
    "opening_hours": {
        "restaurant": "Sobota in nedelja 12:00-20:00 (zadnji prihod na kosilo 15:00)",
        "rooms": "Sobe: prijava 14:00, odjava 10:00 (pon/torki kuhinja zaprta)",
        "shop": "Po dogovoru ali spletna trgovina 24/7",
        "closed": "Ponedeljek in torek (kuhinja zaprta, večerje za nočitvene goste po dogovoru)",
    },
    "facilities": [
        "Brezplačen WiFi",
        "Klimatizirane sobe",
        "Brezplačen parking",
        "Vrt s pogledom na Pohorje",
        "Otroško igrišče",
    ],
    "activities": [
        "Sprehodi po Pohorju",
        "Kolesarjenje (izposoja koles možna)",
        "Ogled kmetije in živali",
        "Degustacija domačih izdelkov",
    ],
}

LOCATION_KEYWORDS = {
    "kje",
    "naslov",
    "lokacija",
    "kako pridem",
    "priti",
    "parking",
    "telefon",
    "številka",
    "stevilka",
    "email",
    "kontakt",
    "odprti",
    "odprto",
    "delovni čas",
    "ura",
    "kdaj",
    "wifi",
    "internet",
    "klima",
    "parkirišče",
    "parkirisce",
}

FARM_INFO_KEYWORDS = {
    "kje",
    "naslov",
    "lokacija",
    "kako pridem",
    "priti",
    "parking",
    "telefon",
    "številka",
    "stevilka",
    "email",
    "kontakt",
    "odprti",
    "odprto",
    "delovni čas",
    "ura",
    "kdaj",
    "wifi",
    "internet",
    "klima",
    "nahajate",
    "navodila",
    "pot",
    "avtom",
    "parkirišče",
    "parkirisce",
}

FOOD_GENERAL_KEYWORDS = {"hrana", "jest", "jesti", "ponujate", "kuhate", "jedilnik?"}

HELP_KEYWORDS = {"pomoč", "help", "kaj znaš", "kaj znate", "kaj lahko", "možnosti"}
WEEKLY_KEYWORDS = {
    "teden",
    "tedensk",
    "čez teden",
    "med tednom",
    "sreda",
    "četrtek",
    "petek",
    "degustacij",
    "kulinarično",
    "doživetje",
    "4-hodn",
    "5-hodn",
    "6-hodn",
    "7-hodn",
    "4 hodn",
    "5 hodn",
    "6 hodn",
    "7 hodn",
    "štiri hod",
    "stiri hod",
    "pet hod",
    "šest hod",
    "sest hod",
    "sedem hod",
    "4-hodni meni",
    "5-hodni meni",
    "6-hodni meni",
    "7-hodni meni",
}

PRICE_KEYWORDS = {
    "cena",
    "cene",
    "cenika",
    "cenik",
    "koliko stane",
    "koliko stal",
    "koliko košta",
    "koliko kosta",
    "ceno",
    "cenah",
}

GREETING_RESPONSES = [
    # Uporabljamo GREETINGS za variacije v prijaznih uvodih
] + GREETINGS
GOODBYE_RESPONSES = THANKS_RESPONSES
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
    "vseeno",
    "pusti",
}

ROOM_PRICING = {
    "base_price": 50,  # EUR na nočitev na odraslo osebo
    "min_adults": 2,  # minimalno 2 odrasli osebi
    "min_nights_summer": 3,  # jun/jul/avg
    "min_nights_other": 2,  # ostali meseci
    "dinner_price": 25,  # penzionska večerja EUR/oseba
    "dinner_includes": "juha, glavna jed, sladica",
    "child_discounts": {
        "0-4": 100,  # brezplačno
        "4-12": 50,  # 50% popust
    },
    "breakfast_included": True,
    "check_in": "14:00",
    "check_out": "10:00",
    "breakfast_time": "8:00-9:00",
    "dinner_time": "18:00",
    "closed_days": ["ponedeljek", "torek"],  # ni večerij
}

# Vinski seznam za fallback
WINE_LIST = {
    "penece": [
        {"name": "Doppler DIONA brut 2013", "type": "zelo suho", "grape": "100% Chardonnay", "price": 30.00, "desc": "Penina po klasični metodi, eleganca, lupinasto sadje, kruhova skorja"},
        {"name": "Opok27 NYMPHA rose brut 2022", "type": "izredno suho", "grape": "100% Modri pinot", "price": 26.00, "desc": "Rose frizzante, jagodni konfit, češnja, sveže"},
        {"name": "Leber MUŠKATNA PENINA demi sec", "type": "polsladko", "grape": "100% Rumeni muškat", "price": 26.00, "desc": "Klasična metoda, 18 mesecev zorenja, svež vonj limone in muškata"},
    ],
    "bela": [
        {"name": "Greif BELO zvrst 2024", "type": "suho", "grape": "Laški rizling + Sauvignon", "price": 14.00, "desc": "Mladostno, zeliščne in sadne note, visoke kisline"},
        {"name": "Frešer SAUVIGNON 2023", "type": "suho", "grape": "100% Sauvignon", "price": 19.00, "desc": "Aromatičen, zeliščen, črni ribez, koprive, mineralno"},
        {"name": "Frešer LAŠKI RIZLING 2023", "type": "suho", "grape": "100% Laški rizling", "price": 18.00, "desc": "Mladostno, mineralno, note jabolka in suhih zelišč"},
        {"name": "Greif LAŠKI RIZLING terase 2020", "type": "suho", "grape": "100% Laški rizling", "price": 23.00, "desc": "Zoreno 14 mesecev v hrastu, zrelo rumeno sadje, oljnata tekstura"},
        {"name": "Frešer RENSKI RIZLING Markus 2019", "type": "suho", "grape": "100% Renski rizling", "price": 22.00, "desc": "Breskev, petrolej, mineralno, zoreno v hrastu"},
        {"name": "Skuber MUŠKAT OTTONEL 2023", "type": "polsladko", "grape": "100% Muškat ottonel", "price": 17.00, "desc": "Elegantna muškatna cvetica, harmonično, ljubko"},
        {"name": "Greif RUMENI MUŠKAT 2023", "type": "polsladko", "grape": "100% Rumeni muškat", "price": 17.00, "desc": "Mladostno, sortno, note sena in limete"},
    ],
    "rdeca": [
        {"name": "Skuber MODRA FRANKINJA 2023", "type": "suho", "grape": "100% Modra frankinja", "price": 16.00, "desc": "Rubinasta, ribez, murva, malina, polni okus"},
        {"name": "Frešer MODRI PINOT Markus 2020", "type": "suho", "grape": "100% Modri pinot", "price": 23.00, "desc": "Višnje, češnje, maline, žametno, 12 mesecev v hrastu"},
        {"name": "Greif MODRA FRANKINJA črešnjev vrh 2019", "type": "suho", "grape": "100% Modra frankinja", "price": 26.00, "desc": "Zrela, temno sadje, divja češnja, zreli tanini"},
    ],
}

WINE_KEYWORDS = {
    "vino",
    "vina",
    "vin",
    "rdec",
    "rdeca",
    "rdeče",
    "rdece",
    "belo",
    "bela",
    "penin",
    "penina",
    "peneč",
    "muskat",
    "muškat",
    "rizling",
    "sauvignon",
    "frankinja",
    "pinot",
}

# sezonski jedilniki
SEASONAL_MENUS = [
    {
        "months": {3, 4, 5},
        "label": "Marec–Maj (pomladna srajčka)",
        "items": [
            "Pohorska bunka in zorjen Frešerjev sir, hišna suha salama, paštetka iz domačih jetrc, zaseka, bučni namaz, hišni kruhek",
            "Juhe: goveja župca z rezanci in jetrnimi rolicami, koprivna juhica s čemažem",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice z zelišči, mlado goveje meso z rdečim vinom",
            "Priloge: štukelj s skuto, ričota s pirino kašo, pražen krompir, mini pita s porom, ocvrte hruške, pomladna solata",
            "Sladica: Pohorska gibanica babice Angelce",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
    {
        "months": {6, 7, 8},
        "label": "Junij–Avgust (poletna srajčka)",
        "items": [
            "Pohorska bunka, zorjen sir, hišna suha salama, paštetka iz jetrc z žajbljem, bučni namaz, kruhek",
            "Juhe: goveja župca z rezanci, kremna juha poletnega vrta",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice, mlado goveje meso z rabarbaro in rdečim vinom",
            "Priloge: štukelj s skuto, ričota s pirino kašo, mlad krompir z rožmarinom, mini pita z bučkami, ocvrte hruške, poletna solata",
            "Sladica: Pohorska gibanica babice Angelce",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
    {
        "months": {9, 10, 11},
        "label": "September–November (jesenska srajčka)",
        "items": [
            "Dobrodošlica s hišnim likerjem ali sokom; lesena deska s pohorsko bunko, salamo, namazi, Frešerjev sirček, kruhek",
            "Juhe: goveja župca z rezanci, bučna juha s kolerabo, sirne lizike z žajbljem",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice, mlado goveje meso z rabarbaro in rdečo peso",
            "Priloge: štukelj s skuto, ričota s pirino kašo, pražen krompir iz šporheta, mini pita s porom, ocvrte hruške, jesenska solatka",
            "Sladica: Pohorska gibanica (porcijsko)",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
    {
        "months": {12, 1, 2},
        "label": "December–Februar (zimska srajčka)",
        "items": [
            "Pohorska bunka, zorjen sir, hišna suha salama, paštetka iz jetrc s čebulno marmelado, zaseka, bučni namaz, kruhek",
            "Juhe: goveja župca z rezanci, krompirjeva juha s krvavico",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice, mlado goveje meso z rdečim vinom",
            "Priloge: štukelj s skuto, ričota s pirino kašo, pražen krompir iz pečice, mini pita z bučkami, ocvrte hruške, zimska solata",
            "Sladica: Pohorska gibanica babice Angelce",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
]

# kulinarična doživetja (sreda–petek, skupine 6+)
WEEKLY_EXPERIENCES = [
    {
        "label": "Kulinarično doživetje (36 EUR, vinska spremljava 15 EUR / 4 kozarci)",
        "menu": [
            "Penina Doppler Diona 2017, pozdrav iz kuhinje",
            "Sauvignon Frešer 2024, kiblflajš, zelenjava z vrta, zorjen sir, kruh z drožmi",
            "Juha s kislim zeljem in krvavico",
            "Alter Šumenjak 2021, krompir z njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka",
            "Rumeni muškat Greif 2024, Pohorska gibanica ali štrudl ali pita sezone, hišni sladoled",
        ],
    },
    {
        "label": "Kulinarično doživetje (43 EUR)",
        "menu": [
            "Penina Doppler Diona 2017, pozdrav iz kuhinje",
            "Sauvignon Frešer 2024, kiblflajš, zelenjava, zorjen sir, kruh z drožmi",
            "Juha s kislim zeljem in krvavico",
            "Renski rizling Frešer 2019, ričotka pirine kaše z jurčki",
            "Alter Šumenjak 2021, krompir, zelenjavni pire, pohan pišek, solatka",
            "Rumeni muškat Greif 2024, Pohorska gibanica ali štrudl ali pita sezone, hišni sladoled",
        ],
    },
    {
        "label": "Kulinarično doživetje (53 EUR, vinska spremljava 25 EUR / 6 kozarcev)",
        "menu": [
            "Penina Doppler Diona 2017, pozdrav iz kuhinje",
            "Sauvignon Frešer 2024, kiblflajš, zelenjava, zorjen sir, kruh z drožmi",
            "Juha s kislim zeljem in krvavico",
            "Renski rizling Frešer 2019, ričota z jurčki in zelenjavo",
            "Alter Šumenjak 2021, krompir, zelenjavni pire, pohan pišek, solatka",
            "Modra frankinja Greif 2020, štrukelj s skuto, goveje meso, rdeča pesa, rabarbara, naravna omaka",
            "Rumeni muškat Greif 2024, Pohorska gibanica ali štrudl ali pita sezone, hišni sladoled",
        ],
    },
    {
        "label": "Kulinarično doživetje (62 EUR, vinska spremljava 29 EUR / 7 kozarcev)",
        "menu": [
            "Penina Doppler Diona 2017, pozdrav iz kuhinje",
            "Sauvignon Frešer 2024, kiblflajš, zelenjava, zorjen sir, kruh z drožmi",
            "Juha s kislim zeljem in krvavico",
            "Renski rizling Frešer 2019, ričota pirine kaše z jurčki",
            "Alter Šumenjak 2021, krompir, zelenjavni pire, pohan pišek, solatka",
            "Modra frankinja Greif 2020, štrukelj s skuto, goveje meso, rdeča pesa, rabarbara, naravna omaka",
            "Rumeni muškat Greif 2024, Pohorska gibanica ali štrudl ali pita sezone, hišni sladoled",
        ],
    },
]

reservation_state: dict[str, Optional[str | int]] = {
    "step": None,
    "type": None,
    "date": None,
    "time": None,
    "nights": None,
    "rooms": None,
    "people": None,
    "name": None,
    "phone": None,
    "email": None,
    "location": None,
    "available_locations": None,
    "language": None,
}

last_product_query: Optional[str] = None
last_info_query: Optional[str] = None
last_menu_query: bool = False
conversation_history: list[dict[str, str]] = []
last_shown_products: list[str] = []
unknown_question_state: dict[str, dict[str, Any]] = {}
chat_session_id: str = str(uuid.uuid4())[:8]
MENU_INTROS = [
    "Hej! Poglej, kaj kuhamo ta vikend:",
    "Z veseljem povem, kaj je na meniju:",
    "Daj, da ti razkrijem naš sezonski meni:",
    "Evo, vikend jedilnik:",
]
menu_intro_index = 0

def answer_wine_question(message: str) -> str:
    """Odgovarja na vprašanja o vinih SAMO iz WINE_LIST, z upoštevanjem followupov."""
    global last_shown_products

    lowered = message.lower()
    is_followup = any(word in lowered for word in ["še", "drug", "kaj pa", "še kaj", "še kater", "še kakšn", "še kakšno"])

    is_red = any(word in lowered for word in ["rdeč", "rdeca", "rdece", "rdeče", "frankinja", "pinot"])
    is_white = any(word in lowered for word in ["bel", "bela", "belo", "rizling", "sauvignon"])
    is_sparkling = any(word in lowered for word in ["peneč", "penina", "penece", "mehurčk", "brut"])
    is_sweet = any(word in lowered for word in ["sladk", "polsladk", "muškat", "muskat"])
    is_dry = any(word in lowered for word in ["suh", "suho", "suha"])

    def format_wines(wines: list, category_name: str, temp: str) -> str:
        # ob followupu skrij že prikazane
        if is_followup:
            wines = [w for w in wines if w["name"] not in last_shown_products]

        if not wines:
            return (
                f"To so vsa naša {category_name} vina. Imamo pa še:\n"
                "🥂 Bela vina (od 14€)\n"
                "🍾 Peneča vina (od 26€)\n"
                "🍯 Polsladka vina (od 17€)\n"
                "🍷 Rdeča vina (od 16€)\n"
                "Kaj vas zanima?"
            )

        lines = [f"Naša {category_name} vina:"]
        for w in wines:
            lines.append(f"• {w['name']} ({w['type']}, {w['price']:.0f}€) – {w['desc']}")
            if w["name"] not in last_shown_products:
                last_shown_products.append(w["name"])

        if len(last_shown_products) > 15:
            last_shown_products[:] = last_shown_products[-15:]

        return "\n".join(lines) + f"\n\nServiramo ohlajeno na {temp}."

    # Rdeča
    if is_red:
        wines = WINE_LIST["rdeca"]
        if is_dry:
            wines = [w for w in wines if "suho" in w["type"]]
        if is_followup:
            remaining = [w for w in wines if w["name"] not in last_shown_products]
            if not remaining:
                return (
                    "To so vsa naša rdeča vina. Imamo pa še:\n"
                    "🥂 Bela vina (od 14€)\n"
                    "🍾 Peneča vina (od 26€)\n"
                    "🍯 Polsladka vina (od 17€)\n"
                    "Kaj vas zanima?"
                )
        return format_wines(wines, "rdeča", "14°C")

    # Peneča
    if is_sparkling:
        return format_wines(WINE_LIST["penece"], "peneča", "6°C")

    # Bela
    if is_white:
        wines = WINE_LIST["bela"]
        if is_dry:
            wines = [w for w in wines if "suho" in w["type"]]
        if is_sweet:
            wines = [w for w in wines if "polsladk" in w["type"]]
        return format_wines(wines[:5], "bela", "8–10°C")

    # Polsladka
    if is_sweet:
        wines = []
        for w in WINE_LIST["bela"]:
            if "polsladk" in w["type"]:
                wines.append(w)
        for w in WINE_LIST["penece"]:
            if "polsladk" in w["type"].lower() or "demi" in w["type"].lower():
                wines.append(w)
        return format_wines(wines, "polsladka", "8°C")

    # Splošno vprašanje
    return (
        "Ponujamo izbor lokalnih vin:\n\n"
        "🍷 **Rdeča** (suha): Modra frankinja (Skuber 16€, Greif 26€), Modri pinot Frešer (23€)\n"
        "🥂 **Bela** (suha): Sauvignon (19€), Laški rizling (18–23€), Renski rizling (22€)\n"
        "🍾 **Peneča**: Doppler Diona brut (30€), Opok27 rose (26€), Muškatna penina (26€)\n"
        "🍯 **Polsladka**: Rumeni muškat (17€), Muškat ottonel (17€)\n\n"
        "Povejte, kaj vas zanima – rdeče, belo, peneče ali polsladko?"
    )


def answer_weekly_menu(message: str) -> str:
    """Odgovarja na vprašanja o tedenski ponudbi (sreda-petek)."""
    lowered = message.lower()

    requested_courses = None
    if "4" in message or "štiri" in lowered or "stiri" in lowered:
        requested_courses = 4
    elif "5" in message or "pet" in lowered:
        requested_courses = 5
    elif "6" in message or "šest" in lowered or "sest" in lowered:
        requested_courses = 6
    elif "7" in message or "sedem" in lowered:
        requested_courses = 7

    if requested_courses is None:
        lines = [
            "**KULINARIČNA DOŽIVETJA** (sreda–petek, od 13:00, min. 6 oseb)\n",
            "Na voljo imamo degustacijske menije:",
            "",
            f"🍽️ **4-hodni meni**: {WEEKLY_MENUS[4]['price']}€/oseba (vinska spremljava +{WEEKLY_MENUS[4]['wine_pairing']}€ za {WEEKLY_MENUS[4]['wine_glasses']} kozarce)",
            f"🍽️ **5-hodni meni**: {WEEKLY_MENUS[5]['price']}€/oseba (vinska spremljava +{WEEKLY_MENUS[5]['wine_pairing']}€ za {WEEKLY_MENUS[5]['wine_glasses']} kozarcev)",
            f"🍽️ **6-hodni meni**: {WEEKLY_MENUS[6]['price']}€/oseba (vinska spremljava +{WEEKLY_MENUS[6]['wine_pairing']}€ za {WEEKLY_MENUS[6]['wine_glasses']} kozarcev)",
            f"🍽️ **7-hodni meni**: {WEEKLY_MENUS[7]['price']}€/oseba (vinska spremljava +{WEEKLY_MENUS[7]['wine_pairing']}€ za {WEEKLY_MENUS[7]['wine_glasses']} kozarcev)",
            "",
            f"🥗 Posebne zahteve (vege, brez glutena): +{WEEKLY_INFO['special_diet_extra']}€/hod",
            "",
            f"📞 Rezervacije: {WEEKLY_INFO['contact']['phone']} ali {WEEKLY_INFO['contact']['email']}",
            "",
            "Povejte kateri meni vas zanima (4, 5, 6 ali 7-hodni) za podrobnosti!",
        ]
        return "\n".join(lines)

    menu = WEEKLY_MENUS[requested_courses]
    lines = [
        f"**{menu['name']}**",
        f"📅 {WEEKLY_INFO['days'].upper()}, {WEEKLY_INFO['time']}",
        f"👥 Minimum {WEEKLY_INFO['min_people']} oseb",
        "",
    ]

    for i, course in enumerate(menu["courses"], 1):
        wine_text = f" 🍷 _{course['wine']}_" if course["wine"] else ""
        lines.append(f"**{i}.** {course['dish']}{wine_text}")

    lines.extend(
        [
            "",
            f"💰 **Cena: {menu['price']}€/oseba**",
            f"🍷 Vinska spremljava: +{menu['wine_pairing']}€ ({menu['wine_glasses']} kozarcev)",
            f"🥗 Vege/brez glutena: +{WEEKLY_INFO['special_diet_extra']}€/hod",
            "",
            f"📞 Rezervacije: {WEEKLY_INFO['contact']['phone']} ali {WEEKLY_INFO['contact']['email']}",
        ]
    )

    return "\n".join(lines)


def detect_intent(message: str) -> str:
    global last_product_query, last_wine_query
    lower_message = message.lower()

    # 1) nadaljevanje rezervacije ima vedno prednost
    if reservation_state["step"] is not None:
        return "reservation"

    # goodbye/hvala
    if is_goodbye(message):
        return "goodbye"

    # SOBE - posebej pred rezervacijo
    sobe_keywords = ["sobe", "soba", "sobo", "nastanitev", "prenočitev", "nočitev nočitve", "rooms", "room", "accommodation"]
    if any(kw in lower_message for kw in sobe_keywords) and "rezerv" not in lower_message and "book" not in lower_message:
        return "room_info"
    
    # 2) začetek rezervacije
    if any(phrase in lower_message for phrase in RESERVATION_START_PHRASES):
        return "reservation"

    # vino intent
    if any(keyword in lower_message for keyword in WINE_KEYWORDS):
        return "wine"

    # vino followup (če je bila prejšnja interakcija o vinih)
    if last_wine_query and any(
        phrase in lower_message for phrase in ["še", "še kakšn", "še kater", "kaj pa", "drug"]
    ):
        return "wine_followup"

    # cene sob
    if any(word in lower_message for word in PRICE_KEYWORDS):
        if any(word in lower_message for word in ["sob", "nočitev", "nocitev", "noč", "spanje", "bivanje"]):
            return "room_pricing"

    # tedenska ponudba (degustacijski meniji) – pred jedilnikom
    if any(word in lower_message for word in WEEKLY_KEYWORDS):
        return "weekly_menu"
    if re.search(r"\b[4-7]\s*-?\s*hodn", lower_message):
        return "weekly_menu"

    # 3) info o kmetiji / kontakt
    if any(keyword in lower_message for keyword in FARM_INFO_KEYWORDS):
        return "farm_info"

    if is_tourist_query(message):
        return "tourist_info"

    # 3) produktna vprašanja (salama, bunka, marmelada, paket, vino …)
    if any(stem in lower_message for stem in PRODUCT_STEMS):
        return "product"

    # 4) kratko nadaljevanje produktnega vprašanja
    if last_product_query and any(
        phrase in lower_message for phrase in PRODUCT_FOLLOWUP_PHRASES
    ):
        return "product_followup"

    # 5) info vprašanja (kje, soba, nočitve …)
    if any(keyword in lower_message for keyword in INFO_KEYWORDS):
        return "info"
    # 6) splošna hrana (ne jedilnik)
    if any(word in lower_message for word in FOOD_GENERAL_KEYWORDS) and not is_menu_query(message):
        return "food_general"
    # 7) pomoč
    if any(word in lower_message for word in HELP_KEYWORDS):
        return "help"
    # 9) tedenska ponudba
    if any(word in lower_message for word in WEEKLY_KEYWORDS):
        return "weekly_menu"
    return "default"


def format_products(query: str) -> str:
    products = find_products(query)
    if not products:
        return "Trenutno nimam podatkov o izdelkih, prosim preverite spletno trgovino ali nas kontaktirajte."

    product_lines = [
        f"- {product.name}: {product.price:.2f} EUR, {product.weight:.2f} kg"
        for product in products
    ]
    header = "Na voljo imamo naslednje izdelke:\n"
    return header + "\n".join(product_lines)


def answer_product_question(message: str) -> str:
    """Odgovarja na vprašanja o izdelkih z linki do spletne trgovine."""
    from app.rag.knowledge_base import KNOWLEDGE_CHUNKS
    
    lowered = message.lower()
    
    # Določi kategorijo
    category = None
    if "marmelad" in lowered or "džem" in lowered or "dzem" in lowered:
        category = "marmelad"
    elif "liker" in lowered or "žganj" in lowered or "zganj" in lowered or "tepkovec" in lowered:
        category = "liker"
    elif "bunk" in lowered:
        category = "bunka"
    elif "salam" in lowered or "klobas" in lowered or "mesn" in lowered:
        category = "mesn"
    elif "namaz" in lowered or "pašteta" in lowered or "pasteta" in lowered:
        category = "namaz"
    elif "sirup" in lowered or "sok" in lowered:
        category = "sirup"
    elif "čaj" in lowered or "caj" in lowered:
        category = "caj"
    elif "paket" in lowered or "daril" in lowered:
        category = "paket"
    
    # Poišči izdelke
    results = []
    for c in KNOWLEDGE_CHUNKS:
        if "/izdelek/" not in c.url:
            continue
        
        url_lower = c.url.lower()
        title_lower = c.title.lower() if c.title else ""
        content_lower = c.paragraph.lower() if c.paragraph else ""
        
        if category:
            if category == "marmelad" and ("marmelad" in url_lower or "marmelad" in title_lower):
                results.append(c)
            elif category == "liker" and ("liker" in url_lower or "tepkovec" in url_lower):
                results.append(c)
            elif category == "bunka" and "bunka" in url_lower:
                results.append(c)
            elif category == "mesn" and ("salama" in url_lower or "klobas" in url_lower):
                results.append(c)
            elif category == "namaz" and ("namaz" in url_lower or "pastet" in url_lower):
                results.append(c)
            elif category == "sirup" and ("sirup" in url_lower or "sok" in url_lower):
                results.append(c)
            elif category == "caj" and "caj" in url_lower:
                results.append(c)
            elif category == "paket" and "paket" in url_lower:
                results.append(c)
        else:
            # Splošno iskanje po ključnih besedah
            words = [w for w in lowered.split() if len(w) > 3]
            for word in words:
                if word in url_lower or word in title_lower or word in content_lower:
                    results.append(c)
                    break
    
    # Odstrani duplikate in omeji na 5
    seen = set()
    unique = []
    for c in results:
        if c.url not in seen:
            seen.add(c.url)
            unique.append(c)
        if len(unique) >= 5:
            break
    
    if not unique:
        return "Trenutno v bazi ne najdem konkretnih izdelkov za to vprašanje. Predlagam, da pobrskaš po spletni trgovini: https://kovacnik.com/kovacnikova-spletna-trgovina/."
    
    # Formatiraj odgovor
    import re
    lines = ["Na voljo imamo:"]
    for c in unique:
        text = c.paragraph.strip() if c.paragraph else ""
        # Izvleci ceno
        price = ""
        price_match = re.match(r'^(\d+[,\.]\d+\s*€)', text)
        if price_match:
            price = price_match.group(1)
            text = text[len(price_match.group(0)):].strip()
        # Skrajšaj opis
        for marker in [" Kategorija:", " V naši ponudbi", " Šifra:"]:
            idx = text.find(marker)
            if idx > 10:
                text = text[:idx]
        if len(text) > 100:
            text = text[:100] + "..."
        
        title = c.title or "Izdelek"
        if price:
            lines.append(f"• **{title}** ({price}) - {text}")
        else:
            lines.append(f"• **{title}** - {text}")
        lines.append(f"  👉 {c.url}")
    
    lines.append("\nČe želite, vam povem še za kakšen izdelek!")
    return "\n".join(lines)


def is_menu_query(message: str) -> bool:
    lowered = message.lower()
    reservation_indicators = ["rezerv", "sobo", "sobe", "mizo", "nočitev", "nočitve", "nocitev"]
    if any(indicator in lowered for indicator in reservation_indicators):
        return False
    weekly_indicators = [
        "teden",
        "tedensk",
        "čez teden",
        "med tednom",
        "sreda",
        "četrtek",
        "petek",
        "hodni",
        "hodn",
        "hodov",
        "degustacij",
        "kulinarično",
        "doživetje",
    ]
    if any(indicator in lowered for indicator in weekly_indicators):
        return False
    menu_keywords = ["jedilnik", "meni", "meniju", "jedo", "kuhate"]
    if any(word in lowered for word in menu_keywords):
        return True
    if "vikend kosilo" in lowered or "vikend kosila" in lowered:
        return True
    if "kosilo" in lowered and "rezerv" not in lowered and "mizo" not in lowered:
        return True
    return False


def parse_month_from_text(message: str) -> Optional[int]:
    lowered = message.lower()
    month_map = {
        "januar": 1,
        "januarja": 1,
        "februar": 2,
        "februarja": 2,
        "marec": 3,
        "marca": 3,
        "april": 4,
        "aprila": 4,
        "maj": 5,
        "maja": 5,
        "junij": 6,
        "junija": 6,
        "julij": 7,
        "julija": 7,
        "avgust": 8,
        "avgusta": 8,
        "september": 9,
        "septembra": 9,
        "oktober": 10,
        "oktobra": 10,
        "november": 11,
        "novembra": 11,
        "december": 12,
        "decembra": 12,
    }
    for key, val in month_map.items():
        if key in lowered:
            return val
    return None


def parse_relative_month(message: str) -> Optional[int]:
    lowered = message.lower()
    today = datetime.now()
    if "jutri" in lowered:
        target = today + timedelta(days=1)
        return target.month
    if "danes" in lowered:
        return today.month
    return None


def next_menu_intro() -> str:
    global menu_intro_index
    intro = MENU_INTROS[menu_intro_index % len(MENU_INTROS)]
    menu_intro_index += 1
    return intro


def answer_farm_info(message: str) -> str:
    lowered = message.lower()

    if any(word in lowered for word in ["navodila", "pot", "pot do", "pridem", "priti", "pot do vas", "avtom"]):
        return FARM_INFO["directions"]["from_maribor"]

    if any(word in lowered for word in ["kje", "naslov", "lokacija", "nahajate"]):
        return (
            f"Nahajamo se na: {FARM_INFO['address']} ({FARM_INFO['location_description']}). "
            f"Parking: {FARM_INFO['parking']}. Če želite navodila za pot, povejte, od kod prihajate."
        )

    if any(word in lowered for word in ["telefon", "številka", "stevilka", "poklicat", "klicat"]):
        return f"Telefon: {FARM_INFO['phone']}, mobitel: {FARM_INFO['mobile']}. Pišete lahko na {FARM_INFO['email']}."

    if "email" in lowered or "mail" in lowered:
        return f"E-mail: {FARM_INFO['email']}. Splet: {FARM_INFO['website']}."

    if any(word in lowered for word in ["odprt", "kdaj", "delovni", "ura"]):
        return (
            f"Kosila: {FARM_INFO['opening_hours']['restaurant']} | "
            f"Sobe: {FARM_INFO['opening_hours']['rooms']} | "
            f"Trgovina: {FARM_INFO['opening_hours']['shop']} | "
            f"Zaprto: {FARM_INFO['opening_hours']['closed']}"
        )

    if "parking" in lowered or "parkirišče" in lowered or "parkirisce" in lowered or "avto" in lowered:
        return f"{FARM_INFO['parking']}. Naslov za navigacijo: {FARM_INFO['address']}."

    if "wifi" in lowered or "internet" in lowered or "klima" in lowered:
        facilities = ", ".join(FARM_INFO["facilities"])
        return f"Na voljo imamo: {facilities}."

    if any(word in lowered for word in ["počet", "delat", "aktivnost", "izlet"]):
        activities = "; ".join(FARM_INFO["activities"])
        return f"Pri nas in v okolici lahko: {activities}."

    return (
        f"{FARM_INFO['name']} | Naslov: {FARM_INFO['address']} | Tel: {FARM_INFO['phone']} | "
        f"Email: {FARM_INFO['email']} | Splet: {FARM_INFO['website']}"
    )


def answer_food_question(message: str) -> str:
    return (
        "Pripravljamo tradicionalne pohorske jedi iz lokalnih sestavin.\n"
        "Vikend kosila (sob/ned): 36€ odrasli, otroci 4–12 let -50%, vključuje predjed, juho, glavno jed, priloge in sladico.\n"
        "Če želite videti aktualni sezonski jedilnik, recite 'jedilnik'. Posebne zahteve (vege, brez glutena) uredimo ob rezervaciji."
    )


def answer_room_pricing(message: str) -> str:
    """Odgovori na vprašanja o cenah sob."""
    lowered = message.lower()

    if "večerj" in lowered or "penzion" in lowered:
        return (
            f"**Penzionska večerja**: {ROOM_PRICING['dinner_price']}€/oseba\n"
            f"Vključuje: {ROOM_PRICING['dinner_includes']}\n\n"
            "⚠️ Ob ponedeljkih in torkih večerij ni.\n"
            f"Večerja je ob {ROOM_PRICING['dinner_time']}."
        )

    if "otro" in lowered or "popust" in lowered or "otrok" in lowered:
        return (
            "**Popusti za otroke:**\n"
            "• Otroci do 4 let: **brezplačno**\n"
            "• Otroci 4-12 let: **50% popust**\n"
            "• Otroci nad 12 let: polna cena"
        )

    return (
        f"**Cena sobe**: {ROOM_PRICING['base_price']}€/nočitev na odraslo osebo (min. {ROOM_PRICING['min_adults']} odrasli)\n\n"
        f"**Zajtrk**: vključen ({ROOM_PRICING['breakfast_time']})\n"
        f"**Večerja**: {ROOM_PRICING['dinner_price']}€/oseba ({ROOM_PRICING['dinner_includes']})\n\n"
        "**Popusti za otroke:**\n"
        "• Do 4 let: brezplačno\n"
        "• 4-12 let: 50% popust\n\n"
        f"**Minimalno bivanje**: {ROOM_PRICING['min_nights_other']} nočitvi (poleti {ROOM_PRICING['min_nights_summer']})\n"
        f"**Prijava**: {ROOM_PRICING['check_in']}, **Odjava**: {ROOM_PRICING['check_out']}\n\n"
        "Za rezervacijo povejte datum in število oseb!"
    )


def get_help_response() -> str:
    return (
        "Pomagam vam lahko z:\n"
        "📅 Rezervacije – sobe ali mize za vikend kosilo\n"
        "🍽️ Jedilnik – aktualni sezonski meni\n"
        "🏠 Info o kmetiji – lokacija, kontakt, delovni čas\n"
        "🛒 Izdelki – salame, marmelade, vina, likerji\n"
        "❓ Vprašanja – karkoli o naši ponudbi\n"
        "Kar vprašajte!"
    )


def format_current_menu(month_override: Optional[int] = None) -> str:
    now = datetime.now()
    month = month_override or now.month
    current = None
    for menu in SEASONAL_MENUS:
        if month in menu["months"]:
            current = menu
            break
    if not current:
        current = SEASONAL_MENUS[0]
    lines = [
        next_menu_intro(),
        f"{current['label']}",
    ]
    for item in current["items"]:
        if item.lower().startswith("cena"):
            continue
        lines.append(f"- {item}")
    lines.append("Cena: 36 EUR odrasli, otroci 4–12 let -50%.")
    lines.append("")
    lines.append(
        "Jedilnik je sezonski; če želiš meni za drug mesec, samo povej mesec (npr. 'kaj pa novembra'). "
        "Vege ali brez glutena uredimo ob rezervaciji."
    )
    return "\n".join(lines)


def extract_people_count(message: str) -> Optional[int]:
    # če je zapis "2+2" ali "2 + 2", seštejemo
    if "+" in message:
        nums = re.findall(r"\d+", message)
        if nums:
            return sum(int(n) for n in nums)
    match = re.search(r"\d+", message)
    if match:
        return int(match.group())
    return None


def extract_nights(message: str) -> Optional[int]:
    """Ekstraktira število nočitev iz sporočila."""
    cleaned = re.sub(r"\d{1,2}\.\d{1,2}\.\d{2,4}", " ", message)
    cleaned = re.sub(r"(vikend|weekend|sobota|nedelja)", " ", cleaned, flags=re.IGNORECASE)

    # 1) številka ob besedi noč/nočitev
    match = re.search(r"(\d+)\s*(noč|noc|nočit|nocit|nočitev|noči)", cleaned, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # 2) kratko sporočilo samo s številko
    stripped = cleaned.strip()
    if stripped.isdigit():
        num = int(stripped)
        if 1 <= num <= 30:
            return num

    # 3) prvo število v kratkem sporočilu (<20 znakov)
    if len(message.strip()) < 20:
        nums = re.findall(r"\d+", cleaned)
        if nums:
            num = int(nums[0])
            if 1 <= num <= 30:
                return num

    return None


def extract_date_from_text(message: str) -> Optional[str]:
    """
    Vrne prvi datum v formatu d.m.yyyy ali dd.mm.yyyy, če ga najde.
    """
    lowered = message.lower()
    today = datetime.now()

    # DD.MM.YYYY
    match = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b", message)
    if match:
        return match.group(1)

    # danes / jutri / pojutrišnjem
    if "danes" in lowered:
        return today.strftime("%d.%m.%Y")
    if "jutri" in lowered:
        return (today + timedelta(days=1)).strftime("%d.%m.%Y")
    if "pojutri" in lowered:
        return (today + timedelta(days=2)).strftime("%d.%m.%Y")

    # ta/ nasl. sobota/nedelja
    if "sobot" in lowered:
        days_until = (5 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7
        if "nasledn" in lowered:
            days_until += 7
        return (today + timedelta(days=days_until)).strftime("%d.%m.%Y")
    if "nedelj" in lowered:
        days_until = (6 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7
        if "nasledn" in lowered:
            days_until += 7
        return (today + timedelta(days=days_until)).strftime("%d.%m.%Y")

    # naslednji vikend (sobota)
    if "vikend" in lowered:
        days_until = (5 - today.weekday()) % 7
        if days_until <= 1:
            days_until += 7
        return (today + timedelta(days=days_until)).strftime("%d.%m.%Y")

    # čez X dni/tednov
    match_days = re.search(r"čez\s+(\d+)\s*(dan|dni|dnev)", lowered)
    if match_days:
        days = int(match_days.group(1))
        return (today + timedelta(days=days)).strftime("%d.%m.%Y")
    match_weeks = re.search(r"čez\s+(\d+)\s*(teden|tedna|tedne|tednov)", lowered)
    if match_weeks:
        weeks = int(match_weeks.group(1))
        return (today + timedelta(weeks=weeks)).strftime("%d.%m.%Y")

    return None


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
        "vseeno",
        "pusti",
    ]
    return any(word in lowered for word in reset_words + exit_words)

def get_greeting_response() -> str:
    return random.choice(GREETINGS)


def get_goodbye_response() -> str:
    return random.choice(THANKS_RESPONSES)


def is_goodbye(message: str) -> bool:
    lowered = message.lower().strip()
    if lowered in GOODBYE_KEYWORDS:
        return True
    if any(keyword in lowered for keyword in ["hvala", "adijo", "nasvidenje", "čao", "ciao", "bye"]):
        return True
    return False


def detect_language(message: str) -> str:
    """Zazna jezik sporočila. Vrne 'si', 'en' ali 'de'."""
    lowered = message.lower()
    
    # Slovenske besede, ki vsebujejo angleške nize (izjeme), odstranimo pred detekcijo
    slovak_exceptions = ["liker", "likerj", " like ", "slike"]
    for exc in slovak_exceptions:
        lowered = lowered.replace(exc, "")

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

    # posebna obravnava angleškega zaimka "I" kot samostojne besede
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


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v ciljni jezik, če je angleščina ali nemščina."""
    if lang == "en":
        prompt = f"Translate this to English, keep it natural and friendly:\n{reply}"
    elif lang == "de":
        prompt = f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}"
    else:
        return reply

    try:
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v angleščino ali nemščino, če je treba."""
    if lang not in {"en", "de"}:
        return reply

    if lang == "en":
        prompt = f"Translate this to English, keep it natural and friendly:\n{reply}"
    else:
        prompt = f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}"

    try:
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v ciljni jezik, če ni slovenščina."""
    if lang == "en":
        prompt = f"Translate this to English, keep it natural and friendly:\n{reply}"
    elif lang == "de":
        prompt = f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}"
    else:
        return reply

    try:
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v ciljni jezik (en/de) prek LLM, če je potrebno."""
    if lang == "si":
        return reply
    prompts = {
        "en": "Translate this to English, keep it natural and friendly:\n{reply}",
        "de": "Translate this to German/Deutsch, keep it natural and friendly:\n{reply}",
    }
    prompt = prompts.get(lang)
    if not prompt:
        return reply
    try:
        return generate_llm_answer(prompt.format(reply=reply), history=[])
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v želeni jezik, če ni slovenščina."""
    if lang == "si":
        return reply

    prompt_map = {
        "en": "Translate this to English, keep it natural and friendly:\n{reply}",
        "de": "Translate this to German/Deutsch, keep it natural and friendly:\n{reply}",
    }
    if lang not in prompt_map:
        return reply

    try:
        prompt = prompt_map[lang].format(reply=reply)
        translated = generate_llm_answer(prompt, history=[])
        return translated or reply
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor glede na zaznan jezik (en/de), sicer vrne original."""
    if lang == "en":
        return generate_llm_answer(
            "Translate to English, keep it natural and friendly:\n" + reply,
            history=[],
        )
    if lang == "de":
        return generate_llm_answer(
            "Translate to German/Deutsch, keep it natural and friendly:\n" + reply,
            history=[],
        )
    return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v zaznani jezik (en/de), če je potrebno."""
    if not reply or lang not in {"en", "de"}:
        return reply
    prompt = (
        f"Translate this to English, keep it natural and friendly:\n{reply}"
        if lang == "en"
        else f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}"
    )
    try:
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor glede na zaznani jezik, če je treba."""
    if lang == "en":
        prompt = f"Translate this to English, keep it natural and friendly:\n{reply}"
    elif lang == "de":
        prompt = f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}"
    else:
        return reply

    try:
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return reply


def translate_reply(reply: str, lang: str) -> str:
    """Po potrebi prevede odgovor v angleščino ali nemščino."""
    if lang not in {"en", "de"}:
        return reply
    prompt = (
        f"Translate this to English, keep it natural and friendly:\n{reply}"
        if lang == "en"
        else f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}"
    )
    try:
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return reply


def maybe_translate(reply: str, detected_lang: str) -> str:
    """Po potrebi prevede odgovor v angleščino ali nemščino."""
    if detected_lang not in {"en", "de"}:
        return reply
    try:
        if detected_lang == "en":
            return generate_llm_answer(
                f"Translate this to English, keep it natural and friendly:\n{reply}",
                history=[],
            )
        return generate_llm_answer(
            f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}",
            history=[],
        )
    except Exception:
        return reply


def maybe_translate(text: str, detected_lang: str) -> str:
    """Po potrebi prevede besedilo v angleščino ali nemščino."""
    if detected_lang not in {"en", "de"}:
        return text
    try:
        prompt = (
            f"Translate this to English, keep it natural and friendly:\n{text}"
            if detected_lang == "en"
            else f"Translate this to German/Deutsch, keep it natural and friendly:\n{text}"
        )
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return text

def maybe_translate(text: str, detected_lang: str) -> str:
    """Prevede odgovor v zaznan jezik (angleščina ali nemščina)."""
    if detected_lang == "en":
        return generate_llm_answer(
            f"Translate this to English, keep it natural and friendly:\n{text}",
            history=[],
        )
    if detected_lang == "de":
        return generate_llm_answer(
            f"Translate this to German/Deutsch, keep it natural and friendly:\n{text}",
            history=[],
        )
    return text


def maybe_translate(text: str, target_lang: str) -> str:
    """Prevede besedilo v ciljni jezik (en/de), če je smiselno."""
    if target_lang not in {"en", "de"} or not text:
        return text
    prompts = {
        "en": "Translate to English. Keep the tone friendly and concise:\n",
        "de": "Übersetze ins Deutsche. Freundlich und klar antworten:\n",
    }
    try:
        translated = generate_llm_answer(prompts[target_lang] + text, history=[])
        return translated or text
    except Exception:
        return text


def maybe_translate(text: str, target_lang: str) -> str:
    """Prevede besedilo v en/de, če je potrebno. Ob napaki vrne izvorno besedilo."""
    if target_lang not in {"en", "de"} or not text:
        return text
    prompt_map = {
        "en": "Translate this to English, keep it natural and friendly:\n",
        "de": "Translate this to German/Deutsch, keep it natural and friendly:\n",
    }
    try:
        translated = generate_llm_answer(prompt_map[target_lang] + text, history=[])
        return translated or text
    except Exception:
        return text

def maybe_translate(text: str, target_lang: str) -> str:
    """Po potrebi prevede besedilo v angleščino ali nemščino."""
    if target_lang not in {"en", "de"}:
        return text
    try:
        if target_lang == "en":
            prompt = f"Translate this to English, keep it natural and friendly:\n{text}"
        else:
            prompt = f"Translate this to German/Deutsch, keep it natural and friendly:\n{text}"
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return text


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v zaznani jezik (en/de)."""
    if lang == "en":
        try:
            return generate_llm_answer(
                "Translate this to English, keep it natural and friendly:\n" + reply,
                history=[],
            )
        except Exception:
            return reply
    if lang == "de":
        try:
            return generate_llm_answer(
                "Translate this to German/Deutsch, keep it natural and friendly:\n" + reply,
                history=[],
            )
        except Exception:
            return reply
    return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v angleščino ali nemščino, če je potrebno."""
    if not reply or lang == "si":
        return reply
    try:
        if lang == "en":
            return generate_llm_answer(
                f"Translate this to English, keep it natural and friendly:\n{reply}",
                history=[],
            )
        if lang == "de":
            return generate_llm_answer(
                f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}",
                history=[],
            )
    except Exception:
        return reply
    return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v zaznani jezik (en/de); slovenščina ostane."""
    if not reply or lang == "si":
        return reply
    try:
        if lang == "en":
            return generate_llm_answer(
                "Translate the following message to natural, friendly English:\n" + reply,
                history=[],
            )
        if lang == "de":
            return generate_llm_answer(
                "Translate the following message to natural, friendly German (Deutsch):\n" + reply,
                history=[],
            )
    except Exception:
        return reply
    return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v en/de, če je potrebno. Za slovenščino vrne original."""
    if lang == "si" or not reply:
        return reply

    try:
        if lang == "en":
            return generate_llm_answer(
                "Translate the following message to natural, friendly English:\n" + reply,
                history=[],
            )
        if lang == "de":
            return generate_llm_answer(
                "Translate the following message to natural, friendly German (Deutsch):\n" + reply,
                history=[],
            )
    except Exception:
        return reply

    return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v ciljni jezik, če je angleščina ali nemščina."""
    if lang == "en":
        return generate_llm_answer(
            f"Translate this to English, keep it natural and friendly:\n{reply}", history=[]
        )
    if lang == "de":
        return generate_llm_answer(
            f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}", history=[]
        )
    return reply


def translate_reply(reply: str, lang: str) -> str:
    """Prevede odgovor v podani jezik, če ni slovenščina."""
    if lang == "en":
        return generate_llm_answer(
            f"Translate this to English, keep it natural and friendly:\n{reply}", history=[]
        )
    if lang == "de":
        return generate_llm_answer(
            f"Translate this to German/Deutsch, keep it natural and friendly:\n{reply}", history=[]
        )
    return reply


def translate_response(text: str, target_lang: str) -> str:
    """Prevede besedilo glede na zaznan jezik rezervacije."""
    if target_lang == "si" or target_lang is None:
        return text
    try:
        if target_lang == "en":
            prompt = f"Translate to English, natural and friendly, only translation:\\n{text}"
        elif target_lang == "de":
            prompt = f"Translate to German, natural and friendly, only translation:\\n{text}"
        else:
            return text
        return generate_llm_answer(prompt, history=[])
    except Exception:
        return text


def is_unknown_response(response: str) -> bool:
    """Preveri, ali odgovor nakazuje neznano informacijo."""
    unknown_indicators = [
        "žal ne morem",
        "nimam informacij",
        "ne vem",
        "nisem prepričan",
        "ni na voljo",
        "podatka nimam",
    ]
    response_lower = response.lower()
    return any(ind in response_lower for ind in unknown_indicators)


def get_unknown_response(language: str = "si") -> str:
    """Vrne prijazen odgovor, ko podatkov ni."""
    if language == "si":
        return random.choice(UNKNOWN_RESPONSES)
    responses = {
        "en": "Unfortunately, I cannot answer this question. 😊\n\nIf you share your email address, I will inquire and get back to you.",
        "de": "Leider kann ich diese Frage nicht beantworten. 😊\n\nWenn Sie mir Ihre E-Mail-Adresse mitteilen, werde ich mich erkundigen und Ihnen antworten.",
    }
    return responses.get(language, "Na to vprašanje žal ne morem odgovoriti. 😊")


def is_email(text: str) -> bool:
    """Preveri, ali je besedilo e-poštni naslov."""
    import re as _re

    return bool(_re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", text.strip()))


def validate_reservation_rules(arrival_date_str: str, nights: int) -> Tuple[bool, str, str]:
    cleaned_date = arrival_date_str.strip()
    try:
        datetime.strptime(cleaned_date, "%d.%m.%Y")
    except ValueError:
        return False, "Tega datuma ne razumem. Prosimo uporabite obliko DD.MM.YYYY (npr. 12.7.2025).", "date"

    if nights <= 0:
        return False, "Število nočitev mora biti pozitivno. Poskusite znova.", "nights"

    ok, message = reservation_service.validate_room_rules(cleaned_date, nights)
    if not ok:
        # vsako pravilo za sobe zahteva ponovni vnos datuma/nočitev -> vrnemo tip "date" za reset datuma
        return False, message, "date"

    return True, "", ""


def reset_reservation_state() -> None:
    reservation_state["step"] = None
    reservation_state["type"] = None
    reservation_state["date"] = None
    reservation_state["time"] = None
    reservation_state["nights"] = None
    reservation_state["rooms"] = None
    reservation_state["people"] = None
    reservation_state["name"] = None
    reservation_state["phone"] = None
    reservation_state["email"] = None
    reservation_state["location"] = None
    reservation_state["available_locations"] = None
    reservation_state["language"] = None


def generate_confirmation_email(state: dict[str, Optional[str | int]]) -> str:
    subject = "Zadeva: Rezervacija – Domačija Kovačnik"
    name = state.get("name") or "spoštovani"
    lines = [f"Pozdravljeni {name}!"]

    if state.get("type") == "room":
        try:
            adults = int(state.get("people") or 0)
        except (TypeError, ValueError):
            adults = 0
        try:
            nights_val = int(state.get("nights") or 0)
        except (TypeError, ValueError):
            nights_val = 0
        estimated_price = adults * nights_val * ROOM_PRICING["base_price"] if adults and nights_val else 0
        lines.append(
            f"Prejeli smo povpraševanje za sobo od {state.get('date')} za {state.get('nights')} nočitev "
            f"za {state.get('people')} gostov."
        )
        if estimated_price:
            lines.append(
                f"Okvirna cena bivanja: {estimated_price}€ ({adults} oseb × {state.get('nights')} noči × {ROOM_PRICING['base_price']}€). "
                "Popusti za otroke in večerje se dodajo ob potrditvi."
            )
        lines.append(
            "Zajtrk je vključen v ceno. Prijava od 14:00, odjava do 10:00, zajtrk 8:00–9:00, večerja 18:00 (pon/torki brez večerij)."
        )
        lines.append("Naše sobe so klimatizirane, na voljo je brezplačen Wi‑Fi.")
    else:
        lines.append(
            f"Prejeli smo rezervacijo mize za {state.get('people')} oseb na datum {state.get('date')} ob {state.get('time')}."
        )
        lines.append("Kuhinja ob sobotah in nedeljah deluje med 12:00 in 20:00, zadnji prihod na kosilo je ob 15:00.")

    lines.append("Rezervacijo bomo potrdili po preverjanju razpoložljivosti.")
    lines.append(f"Kontakt domačije: {CONTACT['phone']} | {CONTACT['email']}")
    body = "\n".join(lines)
    return f"{subject}\n\n{body}"


def room_intro_text() -> str:
    return (
        "Sobe: ALJAŽ (2+2), JULIJA (2+2), ANA (2+2). "
        "Minimalno 3 nočitve v juniju/juliju/avgustu, 2 nočitvi v ostalih mesecih. "
        "Prijava 14:00, odjava 10:00, zajtrk 8:00–9:00, večerja 18:00 (pon/torki brez večerij). "
        "Sobe so klimatizirane, Wi‑Fi je brezplačen, zajtrk je vključen."
    )


def table_intro_text() -> str:
    return (
        "Kosila ob sobotah in nedeljah med 12:00 in 20:00, zadnji prihod na kosilo ob 15:00. "
        "Jedilnici: 'Pri peči' (15 oseb) in 'Pri vrtu' (35 oseb)."
    )


def parse_reservation_type(message: str) -> Optional[str]:
    lowered = message.lower()

    # soba - slovensko, angleško, nemško
    room_keywords = [
        # slovensko
        "soba",
        "sobe",
        "sobo",
        "sob",
        "nočitev",
        "prenocitev",
        "noč",
        "prenočiti",
        "prespati",
        # angleško
        "room",
        "rooms",
        "stay",
        "overnight",
        "night",
        "accommodation",
        "sleep",
        # nemško
        "zimmer",
        "übernachtung",
        "übernachten",
        "nacht",
        "schlafen",
        "unterkunft",
    ]
    if any(word in lowered for word in room_keywords):
        return "room"

    # miza - slovensko, angleško, nemško
    table_keywords = [
        # slovensko
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
        # angleško
        "table",
        "lunch",
        "dinner",
        "meal",
        "eat",
        "dining",
        "restaurant",
        # nemško
        "tisch",
        "mittagessen",
        "abendessen",
        "essen",
        "speisen",
        "restaurant",
    ]
    if any(word in lowered for word in table_keywords):
        return "table"
    return None


def _handle_room_reservation_impl(message: str) -> str:
    step = reservation_state["step"]

    if step == "awaiting_room_date":
        date_candidate = extract_date_from_text(message) or message.strip()
        nights_candidate = extract_nights(message)
        # če ni datuma in ni nič cifr, samo prosimo za datum
        if not extract_date_from_text(message) and not re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", message):
            reservation_state["date"] = None
            return "Z veseljem uredim sobo. 😊 Sporočite datum prihoda (DD.MM.YYYY) in približno število nočitev?"
        # če so cifre, poskusimo validirati
        if not extract_date_from_text(message):
            try:
                datetime.strptime(date_candidate, "%d.%m.%Y")
            except ValueError:
                return "Morda še enkrat datum v obliki DD.MM.YYYY (npr. 12.3.2025)?"

        reservation_state["date"] = date_candidate

        # če smo že dobili nočitve v istem stavku, jih validiramo
        if nights_candidate:
            ok, error_message, _ = validate_reservation_rules(
                reservation_state["date"] or "", nights_candidate
            )
            if not ok:
                reservation_state["step"] = "awaiting_room_date"
                reservation_state["date"] = None
                reservation_state["nights"] = None
                return error_message + " Prosim pošlji nov datum in št. nočitev skupaj (npr. 15.7.2025 za 3 nočitve)."
            reservation_state["nights"] = nights_candidate
            reservation_state["step"] = "awaiting_people"
            return (
                f"Odlično, zabeležila sem {reservation_state['date']} za {reservation_state['nights']} nočitev. "
                "Za koliko oseb bi bilo bivanje (odrasli + otroci)?"
            )

        reservation_state["step"] = "awaiting_nights"
        return "Hvala! Koliko nočitev si predstavljate? (poleti min. 3, sicer 2)"

    if step == "awaiting_nights":
        if not reservation_state["date"]:
            reservation_state["step"] = "awaiting_room_date"
            return "Najprej mi, prosim, zaupajte datum prihoda (DD.MM.YYYY), potem še število nočitev."
        nights = None
        match = re.search(r"(\d+)\s*(noč|noc|nočit|nocit|nočitev|noči)", message, re.IGNORECASE)
        if match:
            nights = int(match.group(1))
        else:
            stripped = message.strip()
            if stripped.isdigit():
                nights = int(stripped)
            else:
                nums = re.findall(r"\d+", message)
                if nums and len(message.strip()) < 20:
                    nights = int(nums[0])

        if nights is None:
            return "Koliko nočitev bi si želeli? (npr. '3' ali '3 nočitve')"
        if nights <= 0 or nights > 30:
            return "Število nočitev mora biti med 1 in 30. Koliko nočitev želite?"

        ok, error_message, error_type = validate_reservation_rules(
            reservation_state["date"] or "", nights
        )
        if not ok:
            reservation_state["step"] = "awaiting_room_date"
            reservation_state["date"] = None
            reservation_state["nights"] = None
            return error_message + " Prosim pošlji nov datum prihoda (DD.MM.YYYY) in število nočitev."
        reservation_state["nights"] = nights
        reservation_state["step"] = "awaiting_people"
        return "Super! Za koliko oseb (odrasli + otroci skupaj)? Vsaka soba je 2+2, imamo tri sobe in jih lahko tudi kombiniramo."

    if step == "awaiting_people":
        # če uporabnik popravlja nočitve v tem koraku
        if "nočit" in message.lower() or "nocit" in message.lower() or "noči" in message.lower():
            new_nights = extract_nights(message)
            if new_nights:
                ok, error_message, _ = validate_reservation_rules(
                    reservation_state["date"] or "", new_nights
                )
                if not ok:
                    return error_message + " Koliko nočitev želite?"
                reservation_state["nights"] = new_nights
                # nadaljuj vprašanje za osebe
                return f"Popravljeno na {new_nights} nočitev. Za koliko oseb (odrasli + otroci skupaj)?"
        people = extract_people_count(message)
        if people is None or people <= 0:
            return "Koliko vas bo? (npr. '2 odrasla in 1 otrok' ali '3 osebe')"
        if people > 12:
            return "Na voljo so tri sobe (vsaka 2+2). Za več kot 12 oseb nas prosim kontaktirajte na email."
        reservation_state["people"] = people
        reservation_state["rooms"] = max(1, (people + 3) // 4)
        available, alternative = reservation_service.check_room_availability(
            reservation_state["date"] or "",
            reservation_state["nights"] or 0,
            people,
            reservation_state["rooms"],
        )
        if not available:
            reservation_state["step"] = "awaiting_room_date"
            free_now = reservation_service.available_rooms(
                reservation_state["date"] or "",
                reservation_state["nights"] or 0,
            )
            free_text = ""
            if free_now:
                free_text = f" Trenutno so na ta termin proste: {', '.join(free_now)} (vsaka 2+2)."
            suggestion = (
                f"Najbližji prost termin je {alternative}. Sporočite, ali vam ustreza, ali podajte drug datum."
                if alternative
                else "Prosim izberite drug datum ali manjšo skupino."
            )
            return f"V izbranem terminu nimamo dovolj prostih sob.{free_text} {suggestion}"
        # ponudi izbiro sobe, če je več prostih
        free_rooms = reservation_service.available_rooms(
            reservation_state["date"] or "",
            reservation_state["nights"] or 0,
        )
        needed = reservation_state["rooms"] or 1
        if free_rooms and len(free_rooms) > needed:
            reservation_state["available_locations"] = free_rooms
            reservation_state["step"] = "awaiting_room_location"
            names = ", ".join(free_rooms)
            return f"Proste imamo: {names}. Katero bi želeli (lahko tudi več, npr. 'ALJAZ in ANA')?"
        # auto-assign
        if free_rooms:
            chosen = free_rooms[:needed]
            reservation_state["location"] = ", ".join(chosen)
        else:
            reservation_state["location"] = "Sobe (dodelimo ob potrditvi)"
        reservation_state["step"] = "awaiting_name"
        return "Odlično. Kako se glasi ime in priimek nosilca rezervacije?"

    if step == "awaiting_room_location":
        options = reservation_state.get("available_locations") or []
        if not options:
            reservation_state["step"] = "awaiting_name"
            return "Nadaljujmo. Prosim še ime in priimek nosilca rezervacije."
        # normalizacija za šumnike
        def normalize(text: str) -> str:
            return (
                text.lower()
                .replace("š", "s")
                .replace("ž", "z")
                .replace("č", "c")
                .replace("ć", "c")
            )

        input_norm = normalize(message)
        selected = []
        for opt in options:
            opt_norm = normalize(opt)
            if opt_norm in input_norm or input_norm == opt_norm:
                selected.append(opt)
        if not selected:
            return "Prosim izberite med: " + ", ".join(options)
        needed = reservation_state.get("rooms") or 1
        if len(selected) < needed:
            # če je uporabnik izbral premalo, dopolnimo
            for opt in options:
                if opt not in selected and len(selected) < needed:
                    selected.append(opt)
        reservation_state["location"] = ", ".join(selected[:needed])
        reservation_state["step"] = "awaiting_name"
        return f"Zabeleženo: {reservation_state['location']}. Prosim še ime in priimek nosilca rezervacije."

    if step == "awaiting_name":
        full_name = message.strip()
        if len(full_name.split()) < 2:
            return "Prosim napišite ime in priimek (npr. 'Ana Kovačnik')."
        reservation_state["name"] = full_name
        reservation_state["step"] = "awaiting_phone"
        return "Hvala! Zdaj prosim še telefonsko številko."

    if step == "awaiting_phone":
        phone = message.strip()
        digits = re.sub(r"\D+", "", phone)
        if len(digits) < 7:
            return "Zaznal sem premalo številk. Prosimo vpišite veljavno telefonsko številko."
        reservation_state["phone"] = phone
        reservation_state["step"] = "awaiting_email"
        return "Kam naj pošljem povzetek ponudbe? (e-poštni naslov)"

    if step == "awaiting_email":
        email = message.strip()
        if "@" not in email or "." not in email:
            return "Prosim vpišite veljaven e-poštni naslov (npr. info@primer.si)."
        reservation_state["email"] = email
        reservation_state["step"] = "awaiting_dinner"
        return (
            "Želite ob bivanju tudi večerje? (25€/oseba, vključuje juho, glavno jed in sladico)\n"
            "Odgovorite Da ali Ne."
        )

    if step == "awaiting_dinner":
        answer = message.strip().lower()
        positive = {"da", "ja", "seveda", "zelim", "želim", "hocem", "hočem"}
        negative = {"ne", "no", "nocem", "nočem", "brez"}

        def dinner_warning() -> Optional[str]:
            arrival = reservation_service._parse_date(reservation_state.get("date") or "")
            nights = int(reservation_state.get("nights") or 1)
            if not arrival:
                return None
            for offset in range(max(1, nights)):
                day = (arrival + timedelta(days=offset)).weekday()
                if day in {0, 1}:
                    return "Opozorilo: večerje ob ponedeljkih in torkih ne strežemo."
            return None

        warn = dinner_warning()
        if any(word in answer for word in positive):
            reservation_state["step"] = "awaiting_dinner_count"
            follow = "Za koliko oseb želite večerje?"
            if warn:
                follow = warn + " " + follow
            return follow
        if any(word in answer for word in negative):
            reservation_state["dinner_people"] = 0
            reservation_state["step"] = None
            summary_state = reservation_state.copy()
            reservation_service.create_reservation(
                date=reservation_state["date"] or "",
                people=int(reservation_state["people"] or 0),
                reservation_type="room",
                source="chat",
                nights=int(reservation_state["nights"] or 0),
                rooms=int(reservation_state["rooms"] or 0),
                name=str(reservation_state["name"]),
                phone=str(reservation_state["phone"]),
                email=reservation_state["email"],
                location="Sobe (dodelimo ob potrditvi)",
            )
            email_preview = generate_confirmation_email(summary_state)
            human_summary = (
                f"Zabeležil sem rezervacijo sobe od {summary_state['date']} za {summary_state['nights']} nočitev "
                f"za {summary_state['people']} gostov"
                + (f" ({summary_state.get('rooms')} sob)." if summary_state.get('rooms') else ".")
                + " Prijava 14:00, odjava 10:00. "
                "Zajtrk je vključen (8:00–9:00), večerja 18:00, ob ponedeljkih in torkih večerij ni. "
                "Sobe so klimatizirane, Wi‑Fi je brezplačen. "
                "Večerje: ne."
            )
            if warn:
                human_summary += f" {warn}"
            saved_lang = reservation_state.get("language", "si")
            reset_reservation_state()
            final_response = human_summary + "\n\n---\nPredlagan potrditveni e-mail:\n" + email_preview
            return translate_response(final_response, saved_lang)
        return "Prosim odgovorite z Da ali Ne glede na večerje."

    if step == "awaiting_dinner_count":
        digits = re.findall(r"\d+", message)
        if not digits:
            return "Prosim povejte za koliko oseb želite večerje (število)."
        count = int(digits[0])
        reservation_state["dinner_people"] = count
        reservation_state["step"] = None
        dinner_note = f"Večerje: {count} oseb (25€/oseba)"
        summary_state = reservation_state.copy()
        note_text = dinner_note
        reservation_service.create_reservation(
            date=reservation_state["date"] or "",
            people=int(reservation_state["people"] or 0),
            reservation_type="room",
            source="chat",
            nights=int(reservation_state["nights"] or 0),
            rooms=int(reservation_state["rooms"] or 0),
            name=str(reservation_state["name"]),
            phone=str(reservation_state["phone"]),
            email=reservation_state["email"],
            location="Sobe (dodelimo ob potrditvi)",
            note=note_text,
        )
        email_preview = generate_confirmation_email(summary_state)
        human_summary = (
            f"Zabeležil sem rezervacijo sobe od {summary_state['date']} za {summary_state['nights']} nočitev "
            f"za {summary_state['people']} gostov"
            + (f" ({summary_state['rooms']} sob)." if summary_state.get('rooms') else ".")
            + " Prijava 14:00, odjava 10:00. "
            "Zajtrk je vključen (8:00–9:00), večerja 18:00, ob ponedeljkih in torkih večerij ni. "
            "Sobe so klimatizirane, Wi‑Fi je brezplačen. "
            f"{dinner_note}."
        )
        warning = None
        arrival = reservation_service._parse_date(summary_state.get("date") or "")
        if arrival:
            nights = int(summary_state.get("nights") or 1)
            for offset in range(max(1, nights)):
                if (arrival + timedelta(days=offset)).weekday() in {0, 1}:
                    warning = "Opozorilo: večerje ob ponedeljkih in torkih ne strežemo."
                    break
        if warning:
            human_summary += f" {warning}"
        saved_lang = reservation_state.get("language", "si")
        reset_reservation_state()
        final_response = human_summary + "\n\n---\nPredlagan potrditveni e-mail:\n" + email_preview
        return translate_response(final_response, saved_lang)

    return "Nadaljujmo z rezervacijo sobe. Za kateri datum jo želite?"


def handle_room_reservation(message: str) -> str:
    response = _handle_room_reservation_impl(message)
    lang = reservation_state.get("language", "si")
    return translate_response(response, lang)


def _handle_table_reservation_impl(message: str) -> str:
    step = reservation_state["step"]

    if step == "awaiting_table_date":
        proposed = message.strip()
        ok, error_message = reservation_service.validate_table_rules(proposed, "12:00")
        if not ok:
            reservation_state["date"] = None
            return error_message + " Bi poslali datum sobote ali nedelje v obliki DD.MM.YYYY?"
        reservation_state["date"] = proposed
        reservation_state["step"] = "awaiting_table_time"
        return "Ob kateri uri bi želeli mizo? (12:00–20:00, zadnji prihod na kosilo 15:00)"

    if step == "awaiting_table_time":
        desired_time = message.strip()
        ok, error_message = reservation_service.validate_table_rules(
            reservation_state["date"] or "", desired_time
        )
        if not ok:
            reservation_state["step"] = "awaiting_table_date"
            reservation_state["date"] = None
            reservation_state["time"] = None
            return error_message + " Poskusiva z novim datumom (sobota/nedelja, DD.MM.YYYY)."
        reservation_state["time"] = reservation_service._parse_time(desired_time)
        reservation_state["step"] = "awaiting_table_people"
        return "Za koliko oseb pripravimo mizo?"

    if step == "awaiting_table_people":
        people = extract_people_count(message)
        if people is None or people <= 0:
            return "Prosim sporočite število oseb (npr. '6 oseb')."
        if people > 35:
            return "Za večje skupine nad 35 oseb nas prosim kontaktirajte za dogovor o razporeditvi."
        reservation_state["people"] = people
        available, location, suggestions = reservation_service.check_table_availability(
            reservation_state["date"] or "",
            reservation_state["time"] or "",
            people,
        )
        if not available:
            reservation_state["step"] = "awaiting_table_time"
            alt = (
                "Predlagani prosti termini: " + "; ".join(suggestions)
                if suggestions
                else "Prosim izberite drugo uro ali enega od naslednjih vikendov."
            )
            return f"Izbran termin je zaseden. {alt}"
        # če imamo lokacijo že izbranega prostora
        if location:
            reservation_state["location"] = location
            reservation_state["step"] = "awaiting_name"
            return f"Lokacija: {location}. Odlično. Prosim še ime in priimek nosilca rezervacije."

        # če ni vnaprej dodelil, ponudimo izbiro med razpoložljivimi
        # če so na voljo oba prostora, vprašamo za izbiro
        possible = []
        occupancy = reservation_service._table_room_occupancy()
        norm_time = reservation_service._parse_time(reservation_state["time"] or "")
        for room in ["Jedilnica Pri peči", "Jedilnica Pri vrtu"]:
            used = occupancy.get((reservation_state["date"], norm_time, room), 0)
            cap = 15 if "peč" in room.lower() else 35
            if used + people <= cap:
                possible.append(room)
        if len(possible) <= 1:
            reservation_state["location"] = possible[0] if possible else "Jedilnica (dodelimo ob prihodu)"
            reservation_state["step"] = "awaiting_name"
            return "Odlično. Prosim še ime in priimek nosilca rezervacije."
        reservation_state["available_locations"] = possible
        reservation_state["step"] = "awaiting_table_location"
        return "Imamo prosto v: " + " ali ".join(possible) + ". Kje bi želeli sedeti?"

    if step == "awaiting_table_location":
        choice = message.strip().lower()
        options = reservation_state.get("available_locations") or []
        selected = None
        for opt in options:
            if opt.lower() in choice or opt.lower().split()[-1] in choice:
                selected = opt
                break
        if not selected:
            return "Prosim izberite med: " + " ali ".join(options)
        reservation_state["location"] = selected
        reservation_state["step"] = "awaiting_name"
        return f"Zabeleženo: {selected}. Prosim še ime in priimek nosilca rezervacije."

    if step == "awaiting_name":
        full_name = message.strip()
        if len(full_name.split()) < 2:
            return "Prosim napišite ime in priimek (npr. 'Ana Kovačnik')."
        reservation_state["name"] = full_name
        reservation_state["step"] = "awaiting_phone"
        return "Hvala! Zdaj prosim še telefonsko številko."

    if step == "awaiting_phone":
        phone = message.strip()
        digits = re.sub(r"\D+", "", phone)
        if len(digits) < 7:
            return "Zaznal sem premalo številk. Prosimo vpišite veljavno telefonsko številko."
        reservation_state["phone"] = phone
        reservation_state["step"] = "awaiting_email"
        return "Kam naj pošljem povzetek ponudbe? (e-poštni naslov)"

    if step == "awaiting_email":
        email = message.strip()
        if "@" not in email or "." not in email:
            return "Prosim vpišite veljaven e-poštni naslov (npr. info@primer.si)."
        reservation_state["email"] = email
        summary_state = reservation_state.copy()
        reservation_service.create_reservation(
            date=reservation_state["date"] or "",
            people=int(reservation_state["people"] or 0),
            reservation_type="table",
            source="chat",
            time=reservation_state["time"],
            location=reservation_state["location"],
            name=str(reservation_state["name"]),
            phone=str(reservation_state["phone"]),
            email=reservation_state["email"],
        )
        email_preview = generate_confirmation_email(summary_state)
        human_summary = (
            f"Zabeležil sem rezervacijo mize za {summary_state['people']} oseb "
            f"na datum {summary_state['date']} ob {summary_state['time']} ({summary_state.get('location')}). "
            "Kuhinja ob sobotah in nedeljah deluje med 12:00 in 20:00, zadnji prihod na kosilo ob 15:00."
        )
        reset_reservation_state()
        return human_summary + "\n\n---\nPredlagan potrditveni e-mail:\n" + email_preview

    return "Nadaljujmo z rezervacijo mize. Kateri datum vas zanima?"


def handle_table_reservation(message: str) -> str:
    response = _handle_table_reservation_impl(message)
    lang = reservation_state.get("language", "si")
    return translate_response(response, lang)


def handle_reservation_flow(message: str) -> str:
    if reservation_state["language"] is None:
        reservation_state["language"] = detect_language(message)

    def _tr(text: str) -> str:
        return translate_response(text, reservation_state.get("language", "si"))

    # možnost popolnega izhoda iz rezervacije
    if any(word in message.lower() for word in EXIT_KEYWORDS):
        reset_reservation_state()
        return _tr("V redu, rezervacijo sem preklical. Kako vam lahko pomagam?")

    if detect_reset_request(message):
        reset_reservation_state()
        return _tr("Ni problema, začniva znova. Želite rezervirati sobo ali mizo za kosilo?")

    # če smo v enem toku, pa uporabnik omeni drug tip, preklopimo
    lowered = message.lower()
    if reservation_state["step"] and reservation_state.get("type") == "room" and "miza" in lowered:
        reset_reservation_state()
        reservation_state["type"] = "table"
        reservation_state["step"] = "awaiting_table_date"
        return _tr(
            f"Preklopim na rezervacijo mize. Za kateri datum (sobota/nedelja)? (DD.MM.YYYY)\n{table_intro_text()}"
        )
    if reservation_state["step"] and reservation_state.get("type") == "table" and "soba" in lowered:
        reset_reservation_state()
        reservation_state["type"] = "room"
        reservation_state["step"] = "awaiting_room_date"
        return _tr(
            f"Preklopim na rezervacijo sobe. Za kateri datum prihoda? (DD.MM.YYYY)\n{room_intro_text()}"
        )

    if reservation_state["step"] is None:
        # Če že iz prvega stavka razberemo tip, preskočimo dodatno vprašanje.
        detected = parse_reservation_type(message)
        if detected == "room":
            reservation_state["type"] = "room"
            # poskusimo prebrati datum in nočitve iz prvega stavka
            prefilled_date = extract_date_from_text(message)
            prefilled_nights = None
            if "nočit" in message.lower() or "nocit" in message.lower() or "noči" in message.lower():
                prefilled_nights = extract_nights(message)
            if prefilled_date:
                reservation_state["date"] = prefilled_date
            reply_prefix = "Super, z veseljem uredim rezervacijo sobe. 😊"
            # če imamo nočitve, jih validiramo
            if prefilled_nights:
                ok, error_message, _ = validate_reservation_rules(
                    reservation_state["date"] or "", prefilled_nights
                )
                if not ok:
                    reservation_state["step"] = "awaiting_room_date"
                    reservation_state["date"] = None
                    reservation_state["nights"] = None
                    return _tr(
                        f"{error_message} Na voljo imamo najmanj 2 nočitvi (oz. 3 v poletnih mesecih). "
                        "Mi pošljete nov datum prihoda (DD.MM.YYYY) in število nočitev?"
                    )
                reservation_state["nights"] = prefilled_nights
            # določi naslednji korak glede na manjkajoče podatke
            if not reservation_state["date"]:
                reservation_state["step"] = "awaiting_room_date"
                return _tr(
                    f"{reply_prefix} Za kateri datum prihoda? (DD.MM.YYYY)\n{room_intro_text()}"
                )
            if not reservation_state["nights"]:
                reservation_state["step"] = "awaiting_nights"
                return _tr(
                    f"{reply_prefix} Koliko nočitev načrtujete? (min. 3 v jun/jul/avg, sicer 2)"
                )
            reservation_state["step"] = "awaiting_people"
            return _tr(
                f"{reply_prefix} Zabeleženo imam {reservation_state['date']} za "
                f"{reservation_state['nights']} nočitev. Za koliko oseb bi to bilo?"
            )
        if detected == "table":
            reservation_state["type"] = "table"
            reservation_state["step"] = "awaiting_table_date"
            return _tr(
                f"Odlično, mizo rezerviramo z veseljem. Za kateri datum (sobota/nedelja)? (DD.MM.YYYY)\n{table_intro_text()}"
            )
        reservation_state["step"] = "awaiting_type"
        return _tr("Kako vam lahko pomagam – rezervacija sobe ali mize za kosilo?")

    if reservation_state["step"] == "awaiting_type":
        choice = parse_reservation_type(message)
        if not choice:
            return _tr(
                "Mi zaupate, ali rezervirate sobo ali mizo za kosilo? "
                f"{room_intro_text()} / {table_intro_text()}"
            )
        reservation_state["type"] = choice
        if choice == "room":
            reservation_state["step"] = "awaiting_room_date"
            return _tr(
                f"Odlično, sobo uredimo. Za kateri datum prihoda razmišljate? (DD.MM.YYYY)\n{room_intro_text()}"
            )
        reservation_state["step"] = "awaiting_table_date"
        return _tr(
            f"Super, uredim mizo. Za kateri datum (sobota/nedelja)? (DD.MM.YYYY)\n{table_intro_text()}"
        )

    if reservation_state["type"] == "room":
        return handle_room_reservation(message)
    return handle_table_reservation(message)


def is_greeting(message: str) -> bool:
    lowered = message.lower()
    return any(greeting in lowered for greeting in GREETING_KEYWORDS)


def append_today_hint(message: str, reply: str) -> str:
    lowered = message.lower()
    if "danes" in lowered:
        today = datetime.now().strftime("%A, %d.%m.%Y")
        reply = f"{reply}\n\nZa orientacijo: danes je {today}."
    return reply


def ensure_single_greeting(message: str, reply: str) -> str:
    greetings = ("pozdrav", "živjo", "zdravo", "hej", "hello")
    if reply.lstrip().lower().startswith(greetings):
        return reply
    return f"Pozdravljeni! {reply}"


def build_effective_query(message: str) -> str:
    global last_info_query
    normalized = message.strip().lower()
    short_follow = (
        len(normalized) < 12
        or normalized in INFO_FOLLOWUP_PHRASES
        or normalized.rstrip("?") in INFO_FOLLOWUP_PHRASES
    )
    if short_follow:
        if last_product_query:
            return f"{last_product_query} {message}"
        if last_info_query:
            return f"{last_info_query} {message}"
    return message


@router.post("", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    global last_product_query, last_wine_query, last_info_query, last_menu_query, conversation_history
    session_id = chat_session_id
    needs_followup = False

    # zabeležimo user vprašanje v zgodovino (omejimo na zadnjih 6 parov)
    conversation_history.append({"role": "user", "content": payload.message})
    if len(conversation_history) > 12:
        conversation_history = conversation_history[-12:]

    detected_lang = detect_language(payload.message)

    def finalize(reply_text: str, intent_value: str, followup_flag: bool = False) -> ChatResponse:
        nonlocal needs_followup
        global conversation_history
        final_reply = reply_text
        flag = followup_flag or needs_followup or is_unknown_response(final_reply)
        if flag:
            final_reply = get_unknown_response(detected_lang)
        conv_id = reservation_service.log_conversation(
            session_id=session_id,
            user_message=payload.message,
            bot_response=final_reply,
            intent=intent_value,
            needs_followup=flag,
        )
        if flag:
            unknown_question_state[session_id] = {"question": payload.message, "conv_id": conv_id}
        conversation_history.append({"role": "assistant", "content": final_reply})
        if len(conversation_history) > 12:
            conversation_history = conversation_history[-12:]
        return ChatResponse(reply=final_reply)

    # če je prejšnji odgovor bil "ne vem" in uporabnik pošlje email
    if session_id in unknown_question_state and is_email(payload.message):
        state = unknown_question_state.pop(session_id)
        email_value = payload.message.strip()
        conv_id = state.get("conv_id")
        if conv_id:
            reservation_service.update_followup_email(conv_id, email_value)
        reply = "Hvala! 📧 Vaš elektronski naslov sem si zabeležil. Odgovoril vam bom v najkrajšem možnem času."
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "followup_email", followup_flag=False)

    # aktivna rezervacija ima prednost
    if reservation_state["step"] is not None:
        reply = handle_reservation_flow(payload.message)
        last_product_query = None
        last_wine_query = None
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "reservation")

    intent = detect_intent(payload.message)

    if intent == "goodbye":
        reply = get_goodbye_response()
        last_product_query = None
        last_wine_query = None
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "goodbye")

    if intent == "reservation":
        reply = handle_reservation_flow(payload.message)
        last_product_query = None
        last_wine_query = None
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "reservation")

    # tedenska ponudba naj ima prednost pred vikend jedilnikom
    if intent == "weekly_menu":
        reply = answer_weekly_menu(payload.message)
        last_product_query = None
        last_wine_query = None
        last_info_query = payload.message
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "weekly_menu")

    if intent == "room_info":
        reply = """Seveda! 😊 Imamo tri prijetne družinske sobe:

🛏️ **Soba ALJAŽ** - soba z balkonom (2+2 osebi)
🛏️ **Soba JULIJA** - družinska soba z balkonom (2 odrasla + 2 otroka)  
🛏️ **Soba ANA** - družinska soba z dvema spalnicama (2 odrasla + 2 otroka)

**Cena**: 50€/osebo/noč z zajtrkom
**Večerja**: dodatnih 25€/osebo

Sobe so klimatizirane, Wi-Fi je brezplačen. Prijava ob 14:00, odjava ob 10:00.

Bi želeli rezervirati? Povejte mi datum in število oseb! 🗓️"""
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "room_info")

    if intent == "room_pricing":
        reply = answer_room_pricing(payload.message)
        last_product_query = None
        last_wine_query = None
        last_info_query = payload.message
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "room_pricing")

    if intent == "tourist_info":
        tourist_reply = answer_tourist_question(payload.message)
        if tourist_reply:
            detected_lang = detect_language(payload.message)
            if detected_lang == "en":
                reply = generate_llm_answer(
                    f"Translate this to English, keep it natural and friendly:\n{tourist_reply}",
                    history=[],
                )
            elif detected_lang == "de":
                reply = generate_llm_answer(
                    f"Translate this to German/Deutsch, keep it natural and friendly:\n{tourist_reply}",
                    history=[],
                )
            else:
                reply = tourist_reply
            last_product_query = None
            last_wine_query = None
            last_info_query = payload.message
            last_menu_query = False
            return finalize(reply, "tourist_info")

    month_hint = parse_month_from_text(payload.message) or parse_relative_month(payload.message)
    if month_hint is not None or is_menu_query(payload.message):
        reply = format_current_menu(month_override=month_hint)
        last_product_query = None
        last_wine_query = None
        last_info_query = None
        last_menu_query = True
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "menu")

    if intent == "product":
        reply = answer_product_question(payload.message)
        last_product_query = payload.message
        last_wine_query = None
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "product")

    if intent == "product_followup":
        combined = f"{last_product_query} {payload.message}" if last_product_query else payload.message
        reply = answer_product_question(combined)
        last_product_query = combined
        last_wine_query = None
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "product_followup")

    if intent == "farm_info":
        reply = answer_farm_info(payload.message)
        last_product_query = None
        last_wine_query = None
        last_info_query = payload.message
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "farm_info")

    if intent == "food_general":
        reply = answer_food_question(payload.message)
        last_product_query = None
        last_wine_query = None
        last_info_query = payload.message
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "food_general")

    if intent == "help":
        reply = get_help_response()
        last_product_query = None
        last_wine_query = None
        last_info_query = payload.message
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "help")

    if intent == "wine":
        reply = answer_wine_question(payload.message)
        last_product_query = None
        last_wine_query = payload.message
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "wine")

    if intent == "wine_followup":
        combined = f"{last_wine_query} {payload.message}" if last_wine_query else payload.message
        reply = answer_wine_question(combined)
        last_wine_query = combined
        last_product_query = None
        last_info_query = None
        last_menu_query = False
        reply = maybe_translate(reply, detected_lang)
        return finalize(reply, "wine_followup")

    try:
        effective_query = build_effective_query(payload.message)
        detected_lang = detect_language(payload.message)

        if detected_lang == "en":
            lang_hint = "\n\n[IMPORTANT: The user is writing in English. Respond in English.]"
            effective_query = effective_query + lang_hint
        elif detected_lang == "de":
            lang_hint = "\n\n[IMPORTANT: The user is writing in German. Respond in German/Deutsch.]"
            effective_query = effective_query + lang_hint

        reply = generate_llm_answer(effective_query, history=conversation_history)
        last_info_query = effective_query
    except Exception:
        reply = (
            "Trenutno imam tehnične težave pri dostopu do podatkov. "
            "Za natančne informacije prosim preverite www.kovacnik.com."
        )
        last_info_query = None
    last_product_query = None
    last_wine_query = None
    last_menu_query = False

    if intent == "default" and is_greeting(payload.message):
        reply = get_greeting_response()
    else:
        reply = append_today_hint(payload.message, reply)

    reply = maybe_translate(reply, detected_lang)
    return finalize(reply, intent)
WEEKLY_MENUS = {
    4: {
        "name": "4-HODNI DEGUSTACIJSKI MENI",
        "price": 36,
        "wine_pairing": 15,
        "wine_glasses": 4,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
    5: {
        "name": "5-HODNI DEGUSTACIJSKI MENI",
        "price": 43,
        "wine_pairing": 20,
        "wine_glasses": 5,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Frešer Renski rizling 2019 (suho)", "dish": "Ričotka pirine kaše z jurčki in zelenjavo"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
    6: {
        "name": "6-HODNI DEGUSTACIJSKI MENI",
        "price": 53,
        "wine_pairing": 25,
        "wine_glasses": 6,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Frešer Renski rizling 2019 (suho)", "dish": "Ričotka pirine kaše z jurčki in zelenjavo"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Modra frankinja 2020 (suho)", "dish": "Štrukelj s skuto naše krave Miške, goveje meso iz Kovačnikove proste reje, rdeča pesa, rabarbara, naravna omaka"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
    7: {
        "name": "7-HODNI DEGUSTACIJSKI MENI",
        "price": 62,
        "wine_pairing": 29,
        "wine_glasses": 7,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Greif Laški rizling Terase 2020 (suho)", "dish": "An ban en goban – Jurčki, ajda, ocvirki, korenček, peteršilj"},
            {"wine": "Frešer Renski rizling 2019 (suho)", "dish": "Ričotka pirine kaše z jurčki in zelenjavo"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Modra frankinja 2020 (suho)", "dish": "Štrukelj s skuto naše krave Miške, goveje meso iz Kovačnikove proste reje, rdeča pesa, rabarbara, naravna omaka"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
}

WEEKLY_INFO = {
    "days": "sreda, četrtek, petek",
    "time": "od 13:00 naprej",
    "min_people": 6,
    "contact": {"phone": "031 330 113", "email": "info@kovacnik.com"},
    "special_diet_extra": 8,
}
