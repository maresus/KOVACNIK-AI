#!/usr/bin/env python3
"""20 stresnih testov za nove funkcionalnosti (commit 4903bb8).

Pokriva: jahanje, Kaja, spletna trgovina, traktor hallucination,
         zimske aktivnosti v INFO_ROOM, dežj handler, klima v INFO_GENERAL,
         družina z normalizo, darilni paketi, kombinacije.

Zagon:
    PYTHONPATH=. python scripts/test_stress_new.py
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "2026"))

from dotenv import load_dotenv
load_dotenv()

from app2026.brand.registry import get_brand
from app2026.chat_v3.router import handle_message


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


def _contains(text: str, token: str) -> bool:
    return token.lower() in text.lower()


async def run_tc(tc: TC, brand: Any) -> tuple[bool, str]:
    sid = str(uuid.uuid4())[:8]
    for i, turn in enumerate(tc.turns):
        try:
            result = await handle_message(turn.msg, sid, brand)
        except Exception as exc:
            return False, f"Turn {i+1} exception: {exc}"
        reply = result.get("reply", "")
        sid = result.get("session_id", sid)
        if not reply:
            return False, f"Turn {i+1} empty reply"
        for token in turn.must:
            if not _contains(reply, token):
                return False, f"Turn {i+1}: missing '{token}' | reply: {reply[:200]}"
        if turn.any_ and not any(_contains(reply, t) for t in turn.any_):
            return False, f"Turn {i+1}: none of {turn.any_} found | reply: {reply[:200]}"
        for token in turn.not_:
            if _contains(reply, token):
                return False, f"Turn {i+1}: forbidden '{token}' found | reply: {reply[:200]}"
    return True, ""


TESTS: list[TC] = [

    # ══════════════════════════════════════════
    # JAHANJE (5)
    # ══════════════════════════════════════════
    TC("Jahanje direktno", "JAHANJE", [
        Turn("Ali je jahanje mogoče?",
             must=["mogoče"],
             any_=["poni", "Malajka", "Marsi", "5 €", "5€", "krog"]),
    ]),
    TC("Jahanje na ponijih", "JAHANJE", [
        Turn("Imate jahanje na ponijah?",
             any_=["jahanj", "poni", "Malajka", "Marsi", "5"],
             not_=["ni mogoče"]),
    ]),
    TC("Cena jahanja", "JAHANJE", [
        Turn("Koliko stane jahanje?",
             any_=["5", "krog", "EUR", "€", "poni"],
             not_=["ni mogoče"]),
    ]),
    TC("Ali je jahanje brezplačno", "JAHANJE", [
        Turn("Je jahanje brezplačno?",
             any_=["5", "€", "krog", "cena", "poni"]),
    ]),
    TC("Jahanje za otroke", "JAHANJE", [
        Turn("Ali otroci lahko jahajo?",
             any_=["jahanj", "poni", "Malajka", "Marsi", "otrok", "5"]),
    ]),

    # ══════════════════════════════════════════
    # KAJA (3)
    # ══════════════════════════════════════════
    TC("Kdo je Kaja", "KAJA", [
        Turn("Kdo je Kaja?",
             any_=["Kaja", "partner", "Aljaž", "razvedri", "dobra volja"]),
    ]),
    TC("Kaja in Aljaž", "KAJA", [
        Turn("Kdo je partnerica Aljaža?",
             any_=["Kaja", "partner", "razvedri"]),
    ]),
    TC("Kajin paket", "KAJA", [
        Turn("Kaj je v Kajinem paketu?",
             any_=["Kajin", "sirup", "čaj", "marmelada", "17", "paket"]),
    ]),

    # ══════════════════════════════════════════
    # SPLETNA TRGOVINA / SHOP (4)
    # ══════════════════════════════════════════
    TC("Kaj prodajate", "SHOP", [
        Turn("Kaj prodajate?",
             any_=["bunka", "salama", "marmelad", "liker", "sirček"]),
    ]),
    TC("Spletna trgovina link", "SHOP", [
        Turn("Kje je vaša spletna trgovina?",
             any_=["kovacnik.com", "spletna", "trgovin", "nakup"]),
    ]),
    TC("Cena marmelad", "SHOP", [
        Turn("Koliko stanejo marmelade?",
             any_=["5,50", "5.50", "€", "marmelad"]),
    ]),
    TC("Cena bunke", "SHOP", [
        Turn("Koliko stane pohorska bunka?",
             any_=["18", "21", "€", "bunka"]),
    ]),

    # ══════════════════════════════════════════
    # TRAKTOR HALLUCINATION BLOCK (2)
    # ══════════════════════════════════════════
    TC("Traktor vožnja block", "TRAKTOR", [
        Turn("Ali ponujate vožnje s traktorjem?",
             any_=["ni", "ne", "mehanizaci", "kmetijsk", "poni", "jahanj"],
             not_=["vožnja s traktorjem je možna", "organiziramo", "rezerv"]),
    ]),
    TC("Traktor za otroke block", "TRAKTOR", [
        Turn("Ali se otroci lahko peljejo s traktorjem?",
             any_=["ni", "ne", "mehanizaci", "kmetijsk", "poni"],
             not_=["organiziramo", "rezerviramo", "cena traktork"]),
    ]),

    # ══════════════════════════════════════════
    # ZIMSKE AKTIVNOSTI V INFO_ROOM (2)
    # ══════════════════════════════════════════
    TC("Kaj na voljo pozimi sobe", "ZIMSKE", [
        Turn("Kaj je na voljo pozimi?",
             any_=["Areh", "smučišč", "Mariborsko", "25", "35", "Pohorje", "smučanj"]),
    ]),
    TC("Pozimi aktivnosti", "ZIMSKE", [
        Turn("Kaj početi pozimi pri vas?",
             any_=["smučišč", "Areh", "Mariborsko", "Pohorje", "30", "25"]),
    ]),

    # ══════════════════════════════════════════
    # DEŽJ HANDLER (1)
    # ══════════════════════════════════════════
    TC("Kaj ob dežju", "DEZJ", [
        Turn("Kaj počnemo ob deževnem vremenu?",
             any_=["živali", "ogled", "kmetij", "domač", "pokličite", "degustat", "liker"]),
    ]),

    # ══════════════════════════════════════════
    # KLIMA V INFO_GENERAL (1)
    # ══════════════════════════════════════════
    TC("Klimatizacija general", "KLIMA", [
        Turn("Imate klimatizacijo?",
             any_=["klima", "klimat"]),
    ]),

    # ══════════════════════════════════════════
    # KOMBINACIJE (2)
    # ══════════════════════════════════════════
    TC("Jahanje nato shop", "KOMBO", [
        Turn("Ali je jahanje mogoče?",
             any_=["poni", "Malajka", "Marsi", "5", "krog"]),
        Turn("In kaj pa kupim za domov?",
             any_=["bunka", "marmelad", "liker", "salama", "kovacnik.com"]),
    ]),
    TC("Kaja nato jahanje", "KOMBO", [
        Turn("Kdo je Kaja?",
             any_=["Kaja", "partner", "razvedri"]),
        Turn("Ali pa pri vas jahajo na poniju?",
             any_=["jahanj", "poni", "5", "krog", "mogoče"]),
    ]),
]


async def main() -> int:
    brand = get_brand()
    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    print()
    print("══════════════════════════════════════════════════════════════")
    print("  STRESS TESTI — nove funkcionalnosti (4903bb8)")
    print("══════════════════════════════════════════════════════════════")

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

    print("════════════════════════════════════════════════════════════")
    print(f"  SKUPAJ: {passed}/{len(TESTS)} passed  ({failed} FAIL)")
    print("════════════════════════════════════════════════════════════")
    if failures:
        print("\nNeuspešni:")
        for name, err in failures:
            print(f"  [{name}] {err}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
