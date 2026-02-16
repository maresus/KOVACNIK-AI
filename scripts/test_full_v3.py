#!/usr/bin/env python3
"""Komprehenzivni test suite za Kovačnik AI V3 chatbot.

Pokriva: pozdrav, živali, sobe, disambiguation, osebe, vina,
vikend meni, tedenski meniji (4-7 hodni), kontakt/lokacija,
rezervacije, zahvale — skupaj ~100 testov.

Zagon:
    PYTHONPATH=. python scripts/test_full_v3.py
    PYTHONPATH=. python scripts/test_full_v3.py --category VINA
    PYTHONPATH=. python scripts/test_full_v3.py --fail-fast
"""
from __future__ import annotations

import argparse
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


# ─────────────────────────────────────────────
# Test infrastructure
# ─────────────────────────────────────────────

@dataclass
class Turn:
    msg: str
    must: list[str] = field(default_factory=list)   # ALL must appear (case-insensitive)
    any_: list[str] = field(default_factory=list)   # at least ONE must appear
    not_: list[str] = field(default_factory=list)   # NONE must appear
    # If empty — just checks the response is non-empty and not an error.


@dataclass
class TC:
    name: str
    category: str
    turns: list[Turn]


def _contains(text: str, token: str) -> bool:
    return token.lower() in text.lower()


async def run_tc(tc: TC, brand: Any, verbose: bool = False) -> tuple[bool, str]:
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
        if "V3 endpoint je izklopljen" in reply:
            return False, "V3 izklopljen"

        # Check must-contain (all)
        for token in turn.must:
            if not _contains(reply, token):
                return False, f"Turn {i+1}: missing '{token}' | reply: {reply[:120]}"

        # Check any-of
        if turn.any_ and not any(_contains(reply, t) for t in turn.any_):
            return False, (
                f"Turn {i+1}: none of {turn.any_} found | reply: {reply[:120]}"
            )

        # Check not-contains
        for token in turn.not_:
            if _contains(reply, token):
                return False, f"Turn {i+1}: forbidden '{token}' | reply: {reply[:120]}"

    return True, reply[:80] if tc.turns else "no turns"


# ─────────────────────────────────────────────
# TEST CASES
# ─────────────────────────────────────────────

TESTS: list[TC] = [

    # ══════════════════════════════════════════
    # A. POZDRAV
    # ══════════════════════════════════════════
    TC("Živjo", "POZDRAV", [Turn("Živjo", any_=["pozdr", "pomoč", "dobr", "zdravo", "hej", "vam"])]),
    TC("Dober dan", "POZDRAV", [Turn("Dober dan", any_=["pozdr", "pomoč", "dobr", "zdravo", "dan"])]),
    TC("Pozdravljeni", "POZDRAV", [Turn("Pozdravljeni", any_=["pozdr", "dobr", "pomoč"])]),
    TC("Zdravo", "POZDRAV", [Turn("Zdravo", any_=["pozdr", "dobr", "zdravo", "pomoč"])]),
    TC("Hej", "POZDRAV", [Turn("Hej", any_=["pozdr", "pomoč", "dobr", "zdravo"])]),

    # ══════════════════════════════════════════
    # B. ŽIVALI
    # ══════════════════════════════════════════
    TC("Vse živali", "ŽIVALI", [
        Turn("Kakšne živali imate na kmetiji?",
             must=["Malajka", "Marsi"],
             any_=["Luna", "Pepa", "Čarli"]),
    ]),
    TC("Konji", "ŽIVALI", [
        Turn("Imate konje?", any_=["Malajka", "Marsi", "konj"]),
    ]),
    TC("Malajka", "ŽIVALI", [
        Turn("Kdo je Malajka?", any_=["konjiček", "konj", "Malajka"]),
    ]),
    TC("Marsi", "ŽIVALI", [
        Turn("Kaj je Marsi?", any_=["konjiček", "konj", "Marsi"]),
    ]),
    TC("Pujska Pepa", "ŽIVALI", [
        Turn("Imate pujse?", any_=["Pepa", "pujsk"]),
    ]),
    TC("Psička Luna", "ŽIVALI", [
        Turn("Imate psa?", any_=["Luna", "psička", "pes", "psa"]),
    ]),
    TC("Mucke", "ŽIVALI", [
        Turn("Imate mačke?", any_=["Mucke", "mačk"]),
    ]),
    TC("Oven Čarli", "ŽIVALI", [
        Turn("Kdo je Čarli?", any_=["oven", "Čarli"]),
    ]),
    TC("Govedo", "ŽIVALI", [
        Turn("Imate govedo?", any_=["govedo", "krav", "Govej"]),
    ]),
    TC("Račke", "ŽIVALI", [
        Turn("Imate račke?", any_=["račk", "Račk"]),
    ]),
    TC("Kokoši", "ŽIVALI", [
        Turn("Imate kokoši?", any_=["kokoš", "Kokoš"]),
    ]),
    TC("Povej o živalih", "ŽIVALI", [
        Turn("Povejte mi o živalih na vaši kmetiji.",
             must=["Malajka"],
             any_=["Luna", "Pepa", "Marsi"]),
    ]),

    # ══════════════════════════════════════════
    # C. SOBE
    # ══════════════════════════════════════════
    TC("Katere sobe imate", "SOBE", [
        Turn("Katere sobe imate?",
             any_=["ALJAŽ", "Aljaž", "JULIJA", "Julija", "ANA", "Ana"]),
    ]),
    TC("Soba Aljaž - direktno", "SOBE", [
        Turn("Kakšna je soba Aljaž?",
             must=["50"],
             any_=["2+2", "balkon", "klima", "ALJAŽ", "Aljaž"]),
    ]),
    TC("Soba Julija", "SOBE", [
        Turn("Opišite mi sobo Julija.",
             must=["50"],
             any_=["2+2", "JULIJA", "Julija"]),
    ]),
    TC("Soba Ana", "SOBE", [
        Turn("Kakšna je soba Ana?",
             any_=["ANA", "Ana", "spalnic", "2+2"]),
    ]),
    TC("Cena nočitve", "SOBE", [
        Turn("Koliko stane nočitev?", must=["50"]),
    ]),
    TC("Check-in čas", "SOBE", [
        Turn("Kdaj je check-in?", any_=["14", "check"]),
    ]),
    TC("Check-out čas", "SOBE", [
        Turn("Kdaj je odjava oz. check-out?", any_=["10", "odjav"]),
    ]),
    TC("Je zajtrk vključen", "SOBE", [
        Turn("Je zajtrk vključen v ceno?", any_=["zajtrk", "vključ"]),
    ]),
    TC("WiFi v sobah", "SOBE", [
        Turn("Imate WiFi v sobah?", any_=["wifi", "WiFi"]),
    ]),
    TC("Klimatizacija", "SOBE", [
        Turn("Imate klimatizacijo v sobah?", any_=["klima", "klimat"]),
    ]),
    TC("Soba za 4 osebe", "SOBE", [
        Turn("Ali imate sobo za 4 osebe?", any_=["2+2", "4", "kapacitet"]),
    ]),
    TC("Balkon", "SOBE", [
        Turn("Ali ima soba Aljaž balkon?",
             any_=["balkon", "50", "ALJAŽ", "Aljaž"]),
    ]),
    TC("Minimalno nočitev poleti", "SOBE", [
        Turn("Koliko je minimalno število nočitev poleti?", any_=["3", "mini", "polet"]),
    ]),
    TC("Rezervacija sobe - cena ANA", "SOBE", [
        Turn("Kakšna je cena sobe ANA za dve osebi?", must=["50"]),
    ]),
    TC("Soba - satelitska TV", "SOBE", [
        Turn("Ali imajo sobe satelitsko televizijo?", any_=["satelit", "tv", "telev"]),
    ]),

    # ══════════════════════════════════════════
    # D. DISAMBIGUATION (multi-turn)
    # ══════════════════════════════════════════
    TC("Aljaž → iz družine (2 turn)", "DISAMBIGUATION", [
        Turn("Kdo je Aljaž?",
             any_=["ali", "zanima", "soba", "družin", "familij"]),
        Turn("Iz družine me zanima.",
             must=["sin"],
             any_=["harmonik", "gospodar", "Aljaž"]),
    ]),
    TC("Aljaž → soba (2 turn)", "DISAMBIGUATION", [
        Turn("Kdo je Aljaž?"),
        Turn("Zanima me soba.",
             must=["50"],
             any_=["balkon", "klima", "ALJAŽ", "Aljaž"]),
    ]),
    TC("Julija → iz družine (2 turn)", "DISAMBIGUATION", [
        Turn("Kdo je Julija?",
             any_=["ali", "zanima", "soba", "familij"]),
        Turn("Julija iz družine.",
             any_=["hči", "živali", "animatorka", "Julija"]),
    ]),
    TC("Julija → soba (2 turn)", "DISAMBIGUATION", [
        Turn("Kdo je Julija?"),
        Turn("Soba me zanima.",
             must=["50"],
             any_=["JULIJA", "Julija", "2+2"]),
    ]),
    TC("Soba Aljaž - en turn (soba v sporočilu)", "DISAMBIGUATION", [
        Turn("Koliko stane soba Aljaž?",
             must=["50"],
             not_=["Ali vas zanima"]),
    ]),
    TC("Rezerviraj sobo Aljaž - en turn", "DISAMBIGUATION", [
        Turn("Rad bi rezerviral sobo Aljaž.",
             any_=["rezerv", "datum", "ime", "oseb", "kdaj", "50", "ALJAŽ"]),
    ]),
    TC("Ana - disambiguacija (2 turn)", "DISAMBIGUATION", [
        Turn("Kdo je Ana?",
             any_=["ali", "zanima", "soba", "družin", "familij", "najmlajš"]),
        Turn("Ana iz družine me zanima.",
             any_=["najmlajš", "hči", "Ana"]),
    ]),
    TC("Ana - soba direktno", "DISAMBIGUATION", [
        Turn("Kakšna je soba Ana?",
             any_=["ANA", "Ana", "spalnic", "2+2", "50"],
             not_=["Ali vas zanima"]),
    ]),
    TC("Kdo je Aljaž sin", "DISAMBIGUATION", [
        Turn("Aljaž - sin kmetije",
             any_=["sin", "harmonik", "Aljaž", "gospodar"]),
    ]),

    # ══════════════════════════════════════════
    # E. OSEBE
    # ══════════════════════════════════════════
    TC("Danilo", "OSEBE", [
        Turn("Kdo je Danilo?",
             must=["Danilo"],
             any_=["gospodar", "Štern", "041"]),
    ]),
    TC("Barbara", "OSEBE", [
        Turn("Kdo je Barbara?",
             must=["Barbara"],
             any_=["Štern", "031", "dejavnost", "nosil"]),
    ]),
    TC("Angelca", "OSEBE", [
        Turn("Kdo je Angelca?",
             must=["Angelca"],
             any_=["babic", "gospodinj"]),
    ]),
    TC("Danilo telefon", "OSEBE", [
        Turn("Kakšna je telefonska številka Danila?",
             any_=["041", "878", "Danilo"]),
    ]),
    TC("Barbara kontakt", "OSEBE", [
        Turn("Kako pokličem Barbaro?",
             any_=["031", "330", "Barbara"]),
    ]),
    TC("Kdo igra harmoniko", "OSEBE", [
        Turn("Kdo igra harmoniko?",
             any_=["Aljaž", "harmonik"]),
    ]),
    TC("Kdo skrbi za živali (oseba)", "OSEBE", [
        Turn("Katera oseba iz družine skrbi za živali?",
             any_=["Julija", "živali", "animatorka", "hči"]),
    ]),
    TC("Mladi gospodar", "OSEBE", [
        Turn("Kdo je mladi gospodar?",
             any_=["Aljaž", "mlad", "gospodar"]),
    ]),
    TC("Lastnik kmetije", "OSEBE", [
        Turn("Kdo je gospodar kmetije?",
             any_=["Danilo", "gospodar"]),
    ]),
    TC("Vsa družina", "OSEBE", [
        Turn("Povejte mi o vaši družini.",
             any_=["Danilo", "Barbara", "Aljaž", "Julija", "Angelca"]),
    ]),

    # ══════════════════════════════════════════
    # F. VINA
    # ══════════════════════════════════════════
    TC("Vinska karta - splošno", "VINA", [
        Turn("Kakšna vina ponujate?",
             must=["Peneča", "Bela", "Rdeča"],
             any_=["Doppler", "Frešer", "Skuber", "Greif"]),
    ]),
    TC("Rdeča vina", "VINA", [
        Turn("Imate rdeča vina?",
             any_=["frankinja", "pinot", "Rdeča", "rdec"]),
    ]),
    TC("Bela vina", "VINA", [
        Turn("Imate bela vina?",
             any_=["Sauvignon", "Rizling", "Muškat", "Bela", "bel"]),
    ]),
    TC("Peneča vina", "VINA", [
        Turn("Imate penino?",
             any_=["Doppler", "DIONA", "Peneča", "peneč"]),
    ]),
    TC("Muškat", "VINA", [
        Turn("Imate muškat?",
             any_=["Muškat", "muškat", "Skuber", "Greif", "Leber"]),
    ]),
    TC("Rizling", "VINA", [
        Turn("Imate rizling?",
             any_=["Rizling", "rizling", "Frešer", "Greif"]),
    ]),
    TC("Modra frankinja", "VINA", [
        Turn("Imate modro frankinjo?",
             any_=["Frankinja", "frankinja", "Skuber", "Greif"]),
    ]),
    TC("Chardonnay penina", "VINA", [
        Turn("Imate chardonnay?",
             any_=["Chardonnay", "Doppler", "DIONA"]),
    ]),
    TC("Sauvignon", "VINA", [
        Turn("Ali imate sauvignon?",
             any_=["Sauvignon", "Frešer"]),
    ]),
    TC("Modri pinot", "VINA", [
        Turn("Imate modri pinot?",
             any_=["Pinot", "pinot", "Frešer"]),
    ]),
    TC("Cene vin", "VINA", [
        Turn("Kakšne so cene vin?",
             any_=["EUR", "eur", "€", "30", "26", "14", "19", "18", "23", "22", "16"]),
    ]),
    TC("Vinska karta - vse kategorije", "VINA", [
        Turn("Pokažite mi vašo vinsko karto.",
             must=["Peneča", "Bela", "Rdeča"]),
    ]),

    # ══════════════════════════════════════════
    # G. VIKEND MENI
    # ══════════════════════════════════════════
    TC("Vikend meni - kaj ponujate", "VIKEND_MENI", [
        Turn("Kaj ponujate za vikend kosilo?",
             any_=["meni", "pečenka", "gibanica", "juha", "bunk", "zimsk",
                   "pomladn", "pojetn", "jesensk"]),
    ]),
    TC("Vikend meni - kdaj", "VIKEND_MENI", [
        Turn("Kdaj imate vikend kosilo?",
             any_=["sobota", "nedelja", "sob", "ned", "12"]),
    ]),
    TC("Vikend meni - cena", "VIKEND_MENI", [
        Turn("Koliko stane vikend meni?",
             must=["36"],
             any_=["EUR", "eur"]),
    ]),
    TC("Vikend meni - cena za otroke", "VIKEND_MENI", [
        Turn("Kakšna je cena za otroke na vikend kosilu?",
             any_=["otrok", "50%", "-50", "let", "36", "odrasl"]),
    ]),
    TC("Pohorska gibanica", "VIKEND_MENI", [
        Turn("Imate pohorsko gibanico?",
             any_=["gibanica", "Gibanica", "Angelca", "Pohorsk"]),
    ]),
    TC("Goveja župca", "VIKEND_MENI", [
        Turn("Ali imate govejo župco?",
             any_=["župca", "župco", "juha"]),
    ]),
    TC("Vikend meni - pečenka", "VIKEND_MENI", [
        Turn("Imate pečenko v meniju?",
             any_=["pečenka", "pečenko", "pujsk"]),
    ]),
    TC("Štukelj", "VIKEND_MENI", [
        Turn("Imate štukelj s skuto?",
             any_=["štukelj", "skuta", "skuto"]),
    ]),
    TC("Vikend meni - odpiralni čas", "VIKEND_MENI", [
        Turn("Ob katerem času se začne vikend kosilo?",
             any_=["12", "12:00", "sob", "ned"]),
    ]),
    TC("Domači kruh", "VIKEND_MENI", [
        Turn("Ali imate domači kruh?",
             any_=["kruh", "kruhek", "hišn"]),
    ]),

    # ══════════════════════════════════════════
    # H. TEDENSKI MENIJI (4-7 hodni)
    # ══════════════════════════════════════════
    TC("Tedenski meni - splošno", "TEDENSKI_MENI", [
        Turn("Kaj ponujate čez teden?",
             any_=["sreda", "četrtek", "petek", "hodni", "degustat", "13:00"]),
    ]),
    TC("Tedenski meni - dnevi", "TEDENSKI_MENI", [
        Turn("Kdaj imate tedenski meni?",
             any_=["sreda", "četrtek", "petek"]),
    ]),
    TC("Tedenski meni - min oseb", "TEDENSKI_MENI", [
        Turn("Kakšna je minimalna skupina za tedenski degustacijski meni?",
             any_=["6", "min", "oseb"]),
    ]),
    TC("4-hodni meni", "TEDENSKI_MENI", [
        Turn("Zanima me 4-hodni meni.",
             must=["36"],
             any_=["4-HODNI", "4-hodni", "gibanica", "župca"]),
    ]),
    TC("5-hodni meni", "TEDENSKI_MENI", [
        Turn("Opišite 5-hodni degustacijski meni.",
             must=["43"],
             any_=["5-HODNI", "5-hodni", "gibanica"]),
    ]),
    TC("6-hodni meni", "TEDENSKI_MENI", [
        Turn("Kakšen je 6-hodni meni?",
             must=["53"],
             any_=["6-HODNI", "6-hodni", "štukelj"]),
    ]),
    TC("7-hodni meni", "TEDENSKI_MENI", [
        Turn("Kaj vsebuje 7-hodni meni?",
             must=["62"],
             any_=["7-HODNI", "7-hodni", "gibanica"]),
    ]),
    TC("4-hodni follow-up guard", "TEDENSKI_MENI", [
        Turn("Kaj ponujate čez teden?"),
        Turn("4",
             must=["36"],
             any_=["4-HODNI", "4-hodni", "gibanica"]),
    ]),
    TC("6-hodni follow-up guard", "TEDENSKI_MENI", [
        Turn("Kaj ponujate čez teden?"),
        Turn("6",
             must=["53"],
             any_=["6-HODNI", "6-hodni"]),
    ]),
    TC("7-hodni follow-up guard", "TEDENSKI_MENI", [
        Turn("Kaj ponujate čez teden?"),
        Turn("7",
             must=["62"],
             any_=["7-HODNI", "7-hodni"]),
    ]),
    TC("Vinska degustacija uz meni", "TEDENSKI_MENI", [
        Turn("Ali je možna vinska degustacija ob meniju?",
             any_=["vinska", "degustacij", "EUR", "15", "20", "25", "29"]),
    ]),
    TC("Cena 4-hodnega menija direktno", "TEDENSKI_MENI", [
        Turn("Koliko stane 4-hodni meni?",
             must=["36"]),
    ]),
    TC("Cena 7-hodnega menija direktno", "TEDENSKI_MENI", [
        Turn("Koliko stane 7-hodni meni?",
             must=["62"]),
    ]),
    TC("Rezervacija menija", "TEDENSKI_MENI", [
        Turn("Kako rezerviram tedenski meni?",
             any_=["031", "330", "pokliči", "telefon", "reserv", "rezerv"]),
    ]),

    # ══════════════════════════════════════════
    # I. KONTAKT & LOKACIJA
    # ══════════════════════════════════════════
    TC("Kje ste", "KONTAKT", [
        Turn("Kje se nahajate?",
             any_=["Planica", "Fram", "Pohorje", "2313"]),
    ]),
    TC("Telefonska številka", "KONTAKT", [
        Turn("Kakšna je vaša telefonska številka?",
             any_=["031", "330", "113", "02 601", "878"]),
    ]),
    TC("Odpiralni čas restavracije", "KONTAKT", [
        Turn("Kdaj ste odprti?",
             any_=["sobota", "nedelja", "sob", "ned", "12", "20"]),
    ]),
    TC("Zaprti v ponedeljek", "KONTAKT", [
        Turn("Ste odprti v ponedeljek?",
             any_=["zaprto", "zaprt", "ponedelj", "ne"]),
    ]),
    TC("Zajtrk kdaj", "KONTAKT", [
        Turn("Ob kateri uri je zajtrk?",
             any_=["8", "9", "zajtrk", "08", "sobe"]),
    ]),
    TC("Večerja kdaj", "KONTAKT", [
        Turn("Ob kateri uri je večerja?",
             any_=["18", "večerj"]),
    ]),
    TC("Parking", "KONTAKT", [
        Turn("Ali imate parkirišče?",
             any_=["parking", "parkirišč", "brezplačn", "park"]),
    ]),
    TC("WiFi splošno", "KONTAKT", [
        Turn("Ali imate WiFi?",
             any_=["Wi-Fi", "wifi", "WiFi", "brezžičn", "brezplačen"]),
    ]),

    # ══════════════════════════════════════════
    # J. REZERVACIJE
    # ══════════════════════════════════════════
    TC("Rezervacija mize - start", "REZERVACIJE", [
        Turn("Rad bi rezerviral mizo za kosilo.",
             any_=["datum", "kdaj", "termin", "ime", "rezerv", "oseb"]),
    ]),
    TC("Rezervacija sobe - start", "REZERVACIJE", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "termin", "ime", "rezerv", "oseb", "nočit"]),
    ]),
    TC("Prekliči rezervacijo", "REZERVACIJE", [
        Turn("Prekliči mojo rezervacijo.",
             any_=["prekliči", "preklican", "preklical", "stornir", "razveljavl"]),
    ]),
    TC("Splošno o rezervacijah", "REZERVACIJE", [
        Turn("Kako rezerviram?",
             any_=["rezerv", "pokliči", "031", "kontakt", "mizo", "sobo"]),
    ]),
    TC("Rezervacija - multi-turn datum", "REZERVACIJE", [
        Turn("Rad bi rezerviral mizo.",
             any_=["datum", "kdaj", "termin", "oseb"]),
        Turn("15.3.2026",
             any_=["ime", "oseb", "15.3", "15. 3", "uri", "ure", "čas", "rezerv", "potrd"]),
    ]),

    # ══════════════════════════════════════════
    # K. ZAHVALA & SMALLTALK
    # ══════════════════════════════════════════
    TC("Hvala", "ZAHVALA", [
        Turn("Hvala za informacije!",
             any_=["prosim", "z veseljem", "veselj", "pomoč", "hvala"]),
    ]),
    TC("Odlično", "ZAHVALA", [
        Turn("Odlično, hvala!",
             any_=["prosim", "veselj", "pomoč", "hvala", "dobr"]),
    ]),
    TC("Na svidenje", "ZAHVALA", [
        Turn("Na svidenje!",
             any_=["svidenje", "zdravo", "adijo", "prihodnjič", "veselj", "prosim"]),
    ]),
    TC("Kako ste", "ZAHVALA", [
        Turn("Kako ste?",
             any_=["pomoč", "veselj", "dobr", "kmetij"]),
    ]),
    TC("To je odlično", "ZAHVALA", [
        Turn("To je odlično, res lepa ponudba.",
             any_=["hvala", "veselj", "prosim", "pomoč"]),
    ]),

    # ══════════════════════════════════════════
    # L. SPLOŠNE INFORMACIJE
    # ══════════════════════════════════════════
    TC("Ime kmetije", "SPLOŠNO", [
        Turn("Kako se imenuje vaša kmetija?",
             any_=["Kovačnik", "kmetija", "Domačija", "Planica"]),
    ]),
    TC("Kaj ponujate", "SPLOŠNO", [
        Turn("Kaj ponujate gostom?",
             any_=["sobe", "meni", "kosilo", "rezerv", "vina", "živali", "nastanit", "ponujamo"]),
    ]),
    TC("Domači izdelki", "SPLOŠNO", [
        Turn("Imate domače pridelke in izdelke za nakup?",
             any_=["domač", "salama", "bunk", "marmelad", "sirek", "liker", "bučni", "pridelk"]),
    ]),
    TC("Aktivnosti na kmetiji", "SPLOŠNO", [
        Turn("Katere aktivnosti ponujate obiskovalcem?",
             any_=["jahanj", "kolesarj", "poni", "živali", "animat", "pohod", "ogled"]),
    ]),
    TC("Je kmetija primerna za otroke", "SPLOŠNO", [
        Turn("Je kmetija primerna za obisk z otroki?",
             any_=["otrok", "otroci", "živali", "poni", "jahanj", "animat", "50%"]),
    ]),
]


# ─────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────

async def main() -> int:
    parser = argparse.ArgumentParser(description="Kovačnik AI V3 full test suite")
    parser.add_argument("--category", default="", help="Run only this category")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    brand = get_brand()

    # Filter tests
    tests = TESTS
    if args.category:
        tests = [t for t in TESTS if t.category.upper() == args.category.upper()]
        if not tests:
            print(f"[ERROR] Kategorija '{args.category}' ni najdena.")
            return 1

    # Group by category
    categories: dict[str, list[TC]] = {}
    for tc in tests:
        categories.setdefault(tc.category, []).append(tc)

    total = passed = 0
    failed_list: list[tuple[str, str, str]] = []

    for cat, cat_tests in categories.items():
        print(f"\n{'─'*54}")
        print(f"  {cat} ({len(cat_tests)} testov)")
        print(f"{'─'*54}")
        cat_pass = 0
        for tc in cat_tests:
            ok, detail = await run_tc(tc, brand, verbose=args.verbose)
            total += 1
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
                cat_pass += 1
                print(f"  ✓ {tc.name}")
            else:
                print(f"  ✗ {tc.name}")
                print(f"      → {detail}")
                failed_list.append((cat, tc.name, detail))
                if args.fail_fast:
                    print("\n[FAIL-FAST] Ustavitev pri prvem neuspehu.")
                    return 1
        print(f"  → {cat_pass}/{len(cat_tests)} passed")

    print(f"\n{'═'*54}")
    print(f"  SKUPAJ: {passed}/{total} passed  ({total - passed} FAIL)")
    print(f"{'═'*54}")

    if failed_list:
        print("\nNeuspešni testi:")
        for cat, name, detail in failed_list:
            print(f"  [{cat}] {name}: {detail}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
