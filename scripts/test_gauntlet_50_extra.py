#!/usr/bin/env python3
"""
GAUNTLET 50 EXTRA — Additional edge case tests
- Extreme typos and phonetic spelling
- Dialect variations (štajerski, prekmurski)
- Multi-language mixing
- Complex recovery scenarios
- Boundary conditions
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "2026"))

from dotenv import load_dotenv
load_dotenv()

from app2026.brand.registry import get_brand


@dataclass
class Turn:
    msg: str
    must: list[str] = field(default_factory=list)
    any_: list[str] = field(default_factory=list)
    not_: list[str] = field(default_factory=list)


@dataclass
class TC:
    name: str
    category: str
    turns: list[Turn]


async def run_tc(tc: TC, brand) -> tuple[bool, str]:
    from app2026.chat_v3.router import handle_message
    session_id = f"test_{tc.name.replace(' ', '_')}"
    for i, turn in enumerate(tc.turns, 1):
        resp = await handle_message(turn.msg, session_id, brand)
        reply = resp.get("reply", "")
        reply_lower = reply.lower()
        for token in turn.must:
            if token.lower() not in reply_lower:
                return False, f"Turn {i}: missing '{token}' | reply: {reply[:200]}"
        if turn.any_:
            if not any(t.lower() in reply_lower for t in turn.any_):
                return False, f"Turn {i}: none of {turn.any_} found | reply: {reply[:200]}"
        for token in turn.not_:
            if token.lower() in reply_lower:
                return False, f"Turn {i}: forbidden '{token}' found | reply: {reply[:200]}"
    return True, ""


TESTS: list[TC] = [
    # ════════════════════════════════════════
    # PHONETIC (10) — fonetični zapis, ekstremni typo
    # ════════════════════════════════════════
    TC("PH01 kolko kosta prnocitev", "PHONETIC", [
        Turn("kolko kosta prnocitev",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
    ]),
    TC("PH02 rezervirm sobo za julij", "PHONETIC", [
        Turn("rezervirm sobo za julij",
             any_=["datum", "kdaj", "prihod"]),
    ]),
    TC("PH03 kok daleq je smucisce", "PHONETIC", [
        Turn("kok daleq je smucisce od vas",
             any_=["Areh", "km", "minut", "smučišč", "25"]),
    ]),
    TC("PH04 ktero vino je ble", "PHONETIC", [
        Turn("ktero vino je ble",
             any_=["bela", "Greif", "Frešer", "vino", "Laški", "Sauvignon"]),
    ]),
    TC("PH05 kdj je cekout", "PHONETIC", [
        Turn("kdj je cekout check-out",
             any_=["10", "odhod", "ura", "checkout"]),
    ]),
    TC("PH06 mrem jhat na poniju", "PHONETIC", [
        Turn("mrem jhat na poniju",
             any_=["5", "€", "jahanj", "krog", "poni"]),
    ]),
    TC("PH07 kva je v degustacjskem meniju", "PHONETIC", [
        Turn("kva je v degustacjskem meniju",
             any_=["juha", "€", "hodni", "glavna"]),
    ]),
    TC("PH08 mate kake popuste za otrce", "PHONETIC", [
        Turn("mate kake popuste za otrce",
             any_=["popust", "otrok", "50%", "brezplačno", "4"]),
    ]),
    TC("PH09 jst bi rezerviral mizo za nedeljo", "PHONETIC", [
        Turn("jst bi rezerviral mizo za nedeljo",
             any_=["datum", "kdaj", "termin"]),
    ]),
    TC("PH10 kke zivali mate na kmetji", "PHONETIC", [
        Turn("kke zivali mate na kmetji",
             any_=["Malajka", "Marsi", "Svinje", "Kokoši", "poni", "živali"]),
    ]),

    # ════════════════════════════════════════
    # DIALECT (10) — štajerski/prekmurski dialekt
    # ════════════════════════════════════════
    TC("DI01 kuko drage so sobe", "DIALECT", [
        Turn("kuko drage so sobe pr vas",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
    ]),
    TC("DI02 kaj pa zajtrk mate", "DIALECT", [
        Turn("kaj pa zajtrk mate zjutre",
             any_=["zajtrk", "vključen", "8:00", "domač"]),
    ]),
    TC("DI03 a lahk psa pripeljemo", "DIALECT", [
        Turn("a lahk psa pripeljemo ali dovolite pse",
             any_=["žal", "ne sprejemamo", "ljubljenčk"]),
    ]),
    TC("DI04 kaj pa ce dezi", "DIALECT", [
        Turn("kaj pa ce dezi cele dan",
             any_=["živali", "degustat", "liker", "ogled", "doživet", "jedi", "kmetij", "kmečk", "dobrot", "čaj"]),
    ]),
    TC("DI05 kje pa se parkiramo", "DIALECT", [
        Turn("kje pa se parkiramo pr vas",
             any_=["parking", "brezplačno", "kmetij"]),
    ]),
    TC("DI06 a je klima v sobah", "DIALECT", [
        Turn("a je klima v sobah al kak",
             any_=["klima", "klimat", "udobn"]),
    ]),
    TC("DI07 kdo pa je ta Barbara", "DIALECT", [
        Turn("kdo pa je ta Barbara k jo klicemo",
             any_=["Barbara", "nosilka", "031", "dopolnilne"]),
    ]),
    TC("DI08 mate kake marmelade", "DIALECT", [
        Turn("mate kake domace marmelade",
             any_=["jagoda", "malina", "marmelad", "5,50"]),
    ]),
    TC("DI09 kdaj je pa kosilo", "DIALECT", [
        Turn("kdaj je pa kosilo pr vas",
             any_=["12:00", "20:00", "sobota", "nedelja"]),
    ]),
    TC("DI10 a se da rezervirat za zdele", "DIALECT", [
        Turn("a se da rezervirat za zdele vikend",
             any_=["datum", "kdaj", "prihod", "termin"]),
    ]),

    # ════════════════════════════════════════
    # MIXLANG (10) — mešanje jezikov (ang/slo/nem)
    # ════════════════════════════════════════
    TC("MX01 hi koliko je room", "MIXLANG", [
        Turn("hi koliko je room per night",
             any_=["50", "EUR", "€", "osebo"]),
    ]),
    TC("MX02 wieviel kostet soba", "MIXLANG", [
        Turn("wieviel kostet soba bei ihnen",
             any_=["50", "EUR", "€"]),
    ]),
    TC("MX03 can I book sobo", "MIXLANG", [
        Turn("can I book sobo for two people",
             any_=["datum", "kdaj", "prihod"]),
    ]),
    TC("MX04 parking free ali platiti", "MIXLANG", [
        Turn("is parking free ali moram platiti",
             any_=["parking", "brezplačno"]),
    ]),
    TC("MX05 breakfast included v ceni", "MIXLANG", [
        Turn("is breakfast included v ceni sobe",
             any_=["zajtrk", "vključen"]),
    ]),
    TC("MX06 danke hvala za info", "MIXLANG", [
        Turn("danke hvala za info",
             any_=["Prosim", "veseljem"]),
    ]),
    TC("MX07 haben sie wifi", "MIXLANG", [
        Turn("haben sie wifi v sobah",
             any_=["wifi", "brezplačno"]),
    ]),
    TC("MX08 what time je checkout", "MIXLANG", [
        Turn("what time je checkout",
             any_=["10", "odhod", "checkout"]),
    ]),
    TC("MX09 reservation za table kosilo", "MIXLANG", [
        Turn("ich möchte reservation za table kosilo",
             any_=["datum", "kdaj", "termin", "miz"]),
    ]),
    TC("MX10 guten tag dober dan", "MIXLANG", [
        Turn("guten tag dober dan",
             any_=["Pozdravljeni", "pomagam", "Kovačnik"]),
    ]),

    # ════════════════════════════════════════
    # RECOVERY (10) — obnovitev po napakah
    # ════════════════════════════════════════
    TC("RC01 preklic nato nova rezervacija", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Ne, pustimo.",
             any_=["preklic", "preklical", "pomagam"]),
        Turn("Mizo bi rezerviral.",
             any_=["datum", "kdaj", "termin"]),
    ]),
    TC("RC02 napaka nato popravek datuma", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("asdfasdf",
             any_=["datum", "prihod", "prosim"]),
        Turn("15. septembra",
             any_=["noč", "koliko", "odhod"]),
    ]),
    TC("RC03 premalo noci potem ok", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("1 noč",
             any_=["minimum", "vsaj", "2", "noči", "3"]),
        Turn("3 noči",
             any_=["oseb", "Koliko", "odrasl", "datum"]),
    ]),
    TC("RC04 napačen email potem ok", "RECOVERY", [
        Turn("Rad bi sobo za 15. oktobra 2 noci 2 osebi.",
             any_=["ime", "naziv", "koga"]),
        Turn("Novak Peter",
             any_=["031", "telefon"]),
        Turn("041123456",
             any_=["email", "pošt"]),
        Turn("peter@email.com",
             any_=["večerj", "opomb", "potrditev"]),
    ]),
    TC("RC05 menjava sobe na mizo mid-flow", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("Pravzaprav bi raje mizo.",
             any_=["datum", "kdaj", "termin", "miza"]),
    ]),
    TC("RC06 cancel mid-booking nato info", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("stop pustimo",
             any_=["preklic", "preklical", "pomagam"]),
        Turn("Koliko stane jahanje?",
             any_=["5", "€", "krog", "poni"]),
    ]),
    TC("RC07 info med booking nato nadaljuj", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Aja koliko pa stane?",
             any_=["50", "EUR", "€", "osebo"]),
        Turn("OK super, 20. avgusta.",
             any_=["noč", "koliko", "odhod"]),
    ]),
    TC("RC08 dvakrat isti vnos", "RECOVERY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "oseb", "že imam"]),
    ]),
    TC("RC09 sprememba med potrditvijo", "RECOVERY", [
        Turn("Rad bi sobo za 15. oktobra 2 noci 2 osebi.",
             any_=["ime", "naziv", "koga"]),
        Turn("Novak Jan",
             any_=["031", "telefon"]),
        Turn("041111222",
             any_=["email", "pošt"]),
        Turn("jan@email.si",
             any_=["večerj"]),
        Turn("ne",
             any_=["opomb", "komentar", "dodatno", "želje", "sporoči"]),
    ]),
    TC("RC10 gibberish nato normalno", "RECOVERY", [
        Turn("asdkjhaskdjh",
             any_=["pomagam", "veseljem", "ponudbi"]),
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
    ]),

    # ════════════════════════════════════════
    # BOUNDARY (10) — mejne vrednosti
    # ════════════════════════════════════════
    TC("BO01 maksimalno oseb 12", "BOUNDARY", [
        Turn("Rad bi sobo za 12 oseb.",
             any_=["datum", "kdaj", "prihod"]),
    ]),
    TC("BO02 prevec oseb 15", "BOUNDARY", [
        Turn("Rad bi sobo za 15 oseb.",
             any_=["12", "kontakt", "email", "več"]),
    ]),
    TC("BO03 ena oseba", "BOUNDARY", [
        Turn("Rad bi sobo za 1 osebo.",
             any_=["datum", "kdaj", "prihod"]),
    ]),
    TC("BO04 7 noci poletje", "BOUNDARY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("7 noči",
             any_=["oseb", "Koliko", "odrasl"]),
    ]),
    TC("BO05 prazno sporocilo", "BOUNDARY", [
        Turn("   ",
             any_=["pomagam", "veseljem", "ponudbi", "pomoč"]),
    ]),
    TC("BO06 samo vprasaj", "BOUNDARY", [
        Turn("?",
             any_=["pomagam", "veseljem", "ponudbi"]),
    ]),
    TC("BO07 dolg tekst 100 znakov", "BOUNDARY", [
        Turn("Pozdravljeni jaz sem oseba ki bi rada vedela vse o vaši kmetiji in sobah in cenah in jedeh " * 2,
             any_=["pomagam", "veseljem", "soba", "miza", "rezervac"]),
    ]),
    TC("BO08 datum v preteklosti", "BOUNDARY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. januarja 2020",
             any_=["noč", "koliko", "datum", "pretekl", "napak"]),
    ]),
    TC("BO09 zelo velik datum", "BOUNDARY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("99.99.9999",
             any_=["datum", "prihod", "prosim", "noč", "neveljavne"]),
    ]),
    TC("BO10 negativno stevilo noci", "BOUNDARY", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("20. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("-3 noči",
             any_=["pozitiv", "vsaj", "noč", "število", "datum", "koliko"]),
    ]),
]

assert len(TESTS) == 50, f"Expected 50 TCs, got {len(TESTS)}"


async def main() -> int:
    brand = get_brand()
    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    print()
    print("════════════════════════════════════════════════════════════════════")
    print("  GAUNTLET 50 EXTRA — phonetic · dialect · mixlang · recovery")
    print("════════════════════════════════════════════════════════════════════")

    categories: dict[str, list[TC]] = {}
    for tc in TESTS:
        categories.setdefault(tc.category, []).append(tc)

    for cat, tcs in categories.items():
        cat_pass = 0
        cat_total = len(tcs)
        for tc in tcs:
            ok, err = await run_tc(tc, brand)
            if ok:
                cat_pass += 1
                passed += 1
                print(f"  ✓ {tc.name}")
            else:
                failed += 1
                print(f"  ✗ {tc.name}: {err}")
                failures.append((tc.name, err))
        print(f"  [{cat}] → {cat_pass}/{cat_total}")
        print()

    print("════════════════════════════════════════════════════════════════════")
    print(f"  SKUPAJ: {passed}/{len(TESTS)} passed  ({failed} FAIL)")
    print("════════════════════════════════════════════════════════════════════")
    if failures:
        print("\nNeuspešni:")
        for name, err in failures:
            print(f"  [{name}] {err}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
