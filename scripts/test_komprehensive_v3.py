#!/usr/bin/env python3
"""Komprehenzivni test suite 400+ scenarijev za Kovačnik AI V3.

Pokriva: pozdrav, sobe, osebe, živali, vina, meniji, cene, kontakt,
outdoor/smučišče, rezervacije (soba+miza), edge cases, zanke, hallucination traps.

Zagon:
    PYTHONPATH=. python scripts/test_komprehensive_v3.py
    PYTHONPATH=. python scripts/test_komprehensive_v3.py --category REZERVACIJE_SOBA
    PYTHONPATH=. python scripts/test_komprehensive_v3.py --fail-fast --verbose
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
        for token in turn.must:
            if not _contains(reply, token):
                return False, f"Turn {i+1}: missing '{token}' | reply: {reply[:150]}"
        if turn.any_ and not any(_contains(reply, t) for t in turn.any_):
            return False, f"Turn {i+1}: none of {turn.any_} found | reply: {reply[:150]}"
        for token in turn.not_:
            if _contains(reply, token):
                return False, f"Turn {i+1}: forbidden '{token}' found | reply: {reply[:150]}"
    return True, ""


TESTS: list[TC] = [

    # ══════════════════════════════════════════
    # A. POZDRAV (20)
    # ══════════════════════════════════════════
    TC("Živjo", "POZDRAV", [Turn("Živjo!", any_=["pozdravlj", "Kovačnik", "pomoč", "dobrodošl"])]),
    TC("Zdravo", "POZDRAV", [Turn("Zdravo", any_=["pozdravlj", "Kovačnik", "pomoč", "dobrodošl"])]),
    TC("Pozdravljeni", "POZDRAV", [Turn("Pozdravljeni!", any_=["pozdravlj", "Kovačnik", "pomoč"])]),
    TC("Dober dan", "POZDRAV", [Turn("Dober dan", any_=["dan", "pozdravlj", "Kovačnik", "pomoč"])]),
    TC("Dober večer", "POZDRAV", [Turn("Dober večer", any_=["večer", "pozdravlj", "pomoč"])]),
    TC("Dobro jutro", "POZDRAV", [Turn("Dobro jutro", any_=["jutro", "pozdravlj", "pomoč"])]),
    TC("Hello", "POZDRAV", [Turn("Hello", any_=["hello", "Kovačnik", "welcome", "pozdravlj"])]),
    TC("Hallo", "POZDRAV", [Turn("Hallo", any_=["hallo", "Kovačnik", "willkommen", "pozdravlj"])]),
    TC("Hi there", "POZDRAV", [Turn("Hi there", any_=["hi", "hello", "Kovačnik", "pozdravlj"])]),
    TC("Ej", "POZDRAV", [Turn("Ej!", any_=["pozdravlj", "Kovačnik", "pomoč"])]),
    TC("Cao", "POZDRAV", [Turn("Ciao", any_=["pozdravlj", "Kovačnik", "pomoč"])]),
    TC("Hvala za pozdrav", "POZDRAV", [Turn("Hvala!", any_=["hvala", "prosim", "pomoč", "veselj"])]),
    TC("Nasvidenje", "POZDRAV", [Turn("Nasvidenje!", any_=["nasvidenje", "adijo", "veselj", "pride"])]),
    TC("Na svidenje", "POZDRAV", [Turn("Na svidenje!", any_=["nasvidenje", "adijo", "veselj"])]),
    TC("Adijo", "POZDRAV", [Turn("Adijo!", any_=["nasvidenje", "adijo", "veselj", "čakamo", "prosim", "nadaljuj"])]),
    TC("Kako ste", "POZDRAV", [Turn("Kako ste?", any_=["dobr", "hvala", "odlično", "pomoč", "pomagam", "ponudba"])]),
    TC("Ali ste odprti", "POZDRAV", [Turn("Ali ste odprti?", any_=["sobota", "nedelja", "12", "odprt", "ura"])]),
    TC("Kdo ste vi", "POZDRAV", [Turn("Kdo ste vi?", any_=["Kovačnik", "pomočnik", "asistent", "kmetij"])]),
    TC("Kaj zmorete", "POZDRAV", [Turn("Kaj zmorete?", any_=["sobe", "meni", "rezerv", "vina", "pomoč"])]),
    TC("Odlično res lepa ponudba", "POZDRAV", [Turn("Odlično, res lepa ponudba!", any_=["hvala", "veselj", "prosim", "pomoč"])]),

    # ══════════════════════════════════════════
    # B. SOBE (30)
    # ══════════════════════════════════════════
    TC("Katere sobe imate", "SOBE", [Turn("Katere sobe imate?", any_=["ALJAŽ", "Aljaž", "JULIJA", "ANA"])]),
    TC("Soba Aljaž", "SOBE", [Turn("Kakšna je soba Aljaž?", must=["50"], any_=["balkon", "klima", "2+2", "ALJAŽ"])]),
    TC("Soba Julija", "SOBE", [Turn("Opišite mi sobo Julija.", must=["50"], any_=["2+2", "JULIJA", "Julija"])]),
    TC("Soba Ana", "SOBE", [Turn("Kakšna je soba Ana?", any_=["ANA", "Ana", "spalnic", "2+2"])]),
    TC("Cena nočitve", "SOBE", [Turn("Koliko stane nočitev?", must=["50"])]),
    TC("Cena sobe za 2", "SOBE", [Turn("Koliko stane soba za dve osebi?", must=["50"])]),
    TC("Soba za 4 osebe", "SOBE", [Turn("Ali imate sobo za 4 osebe?", any_=["2+2", "4", "kapacitet"])]),
    TC("Check-in čas", "SOBE", [Turn("Kdaj je check-in?", any_=["14", "check"])]),
    TC("Check-out čas", "SOBE", [Turn("Kdaj je odjava?", any_=["10", "odjav"])]),
    TC("Zajtrk vključen", "SOBE", [Turn("Je zajtrk vključen v ceno?", any_=["zajtrk", "vključ"])]),
    TC("WiFi sobe", "SOBE", [Turn("Imate WiFi v sobah?", any_=["wifi", "WiFi", "brezžičn"])]),
    TC("Klimatizacija", "SOBE", [Turn("Imate klimatizacijo?", any_=["klima", "klimat"])]),
    TC("Balkon Aljaž", "SOBE", [Turn("Ima soba Aljaž balkon?", any_=["balkon", "ALJAŽ"])]),
    TC("Kopalnica", "SOBE", [Turn("Ali imajo sobe kopalnico?", any_=["kopalnic", "tuš"])]),
    TC("Satelitska TV", "SOBE", [Turn("Ali imajo sobe satelitsko televizijo?", any_=["satelit", "tv", "telev"])]),
    TC("Min nočitve poleti", "SOBE", [Turn("Koliko je min nočitev poleti?", any_=["3", "polet", "jun", "avg"])]),
    TC("Min nočitve splošno", "SOBE", [Turn("Koliko nočitev moram minimalno rezervirati?", any_=["2", "3", "min"])]),
    TC("Cena ANA", "SOBE", [Turn("Kakšna je cena sobe ANA?", must=["50"])]),
    TC("Katera soba ima dve spalnici", "SOBE", [Turn("Katera soba ima dve spalnici?", any_=["ANA", "Ana", "spalnic"])]),
    TC("Kaj je vključeno v ceno", "SOBE", [Turn("Kaj je vključeno v ceno nočitve?", any_=["zajtrk", "vključ"])]),
    TC("Čas zajtrka", "SOBE", [Turn("Ob kateri uri je zajtrk?", any_=["8", "9", "zajtrk"])]),
    TC("Večerja", "SOBE", [Turn("Ali imate večerje za nočitvene goste?", any_=["večerj", "25", "dogovor"])]),
    TC("Soba za otroke", "SOBE", [Turn("Katero sobo priporočate za družino z 2 otrokoma?", any_=["ANA", "Ana", "ALJAŽ", "kapacitet", "2+2"])]),
    TC("Opiši vse sobe", "SOBE", [Turn("Opiši mi vse sobe.", any_=["ALJAŽ", "JULIJA", "ANA", "50"])]),
    TC("Soba poleg balkona", "SOBE", [Turn("Imate sobe z balkonom?", any_=["balkon", "ALJAŽ", "JULIJA"])]),
    TC("Soba za 1 osebo", "SOBE", [Turn("Imate enoposteljno sobo?", any_=["2+2", "sobo", "oseb"])]),
    TC("Rezervacija sobe ANA cena", "SOBE", [Turn("Kakšna je cena sobe ANA za dve noči?", must=["50"])]),
    TC("Zajtrk kaj je", "SOBE", [Turn("Kaj je za zajtrk?", any_=["zajtrk", "mleko", "bunka", "marmelad", "kruh", "8"])]),
    TC("Ponedeljek večerja", "SOBE", [Turn("Ali strežete večerje ob ponedeljkih?", any_=["ponedeljek", "torek", "zaprta", "ne"])]),
    TC("Cena z zajtrkom", "SOBE", [Turn("Je zajtrk plačan posebej?", any_=["vključen", "vključ", "zajtrk", "50"])]),

    # ══════════════════════════════════════════
    # C. OSEBE (25)
    # ══════════════════════════════════════════
    TC("Danilo", "OSEBE", [Turn("Kdo je Danilo?", must=["Danilo"], any_=["gospodar", "Štern"])]),
    TC("Barbara", "OSEBE", [Turn("Kdo je Barbara?", must=["Barbara"], any_=["Štern", "dejavnost", "nosil"])]),
    TC("Angelca", "OSEBE", [Turn("Kdo je Angelca?", must=["Angelca"], any_=["babic", "gospodinj"])]),
    TC("Aljaž - disambiguacija", "OSEBE", [
        Turn("Kdo je Aljaž?", any_=["soba", "sin", "ali", "disambiguacij", "Ali"]),
    ]),
    TC("Aljaž - sin", "OSEBE", [Turn("Aljaž sin kmetije?", any_=["sin", "harmonik", "gospodar", "Aljaž"])]),
    TC("Julija - disambiguacija", "OSEBE", [
        Turn("Kdo je Julija?", any_=["soba", "hči", "ali", "Ali"]),
    ]),
    TC("Ana - disambiguacija", "OSEBE", [
        Turn("Kdo je Ana?", any_=["soba", "hči", "ali", "Ali", "najmlajš"]),
        Turn("Ana iz družine", any_=["hči", "najmlajš", "Ana"]),
    ]),
    TC("Kdo igra harmoniko", "OSEBE", [Turn("Kdo igra harmoniko?", any_=["Aljaž", "harmonik"])]),
    TC("Kdo skrbi za živali", "OSEBE", [Turn("Katera oseba skrbi za živali?", any_=["Julija", "animat", "živali"])]),
    TC("Mladi gospodar", "OSEBE", [Turn("Kdo je mladi gospodar?", any_=["Aljaž", "gospodar"])]),
    TC("Gospodar kmetije", "OSEBE", [Turn("Kdo je gospodar kmetije?", any_=["Danilo", "gospodar"])]),
    TC("Danilo telefon", "OSEBE", [Turn("Kakšna je telefonska številka Danila?", must=["Danilo"], any_=["041", "878"])]),
    TC("Barbara kontakt", "OSEBE", [Turn("Kako pokličem Barbaro?", any_=["031", "330", "Barbara"])]),
    TC("Kdo dela animacije", "OSEBE", [Turn("Kdo dela animacije za otroke?", any_=["Julija", "animat"])]),
    TC("Kdo je babica", "OSEBE", [Turn("Kdo je babica?", any_=["Angelca", "babic", "gospodinj"])]),
    TC("Najmlajša Štern", "OSEBE", [Turn("Kdo je najmlajša članica družine?", any_=["Ana", "najmlajš", "hči"])]),
    TC("Vsa družina", "OSEBE", [Turn("Povejte mi o vaši družini.", any_=["Danilo", "Barbara", "Aljaž", "Julija"])]),
    TC("Danilo brez telefona", "OSEBE", [Turn("Kdo je Danilo Štern?", must=["Danilo"], not_=["041"])]),
    TC("Barbara vloga", "OSEBE", [Turn("Kakšna je vloga Barbare?", any_=["nosil", "dejavnost", "Barbara"])]),
    TC("Angelca zeliščni čaj", "OSEBE", [Turn("Kdo naredi zeliščni čaj za zajtrk?", any_=["Angelca", "babic", "zeliš"])]),
    TC("Aljaž harmonika direktno", "OSEBE", [Turn("Aljaž - igra harmoniko?", any_=["harmonik", "Aljaž"])]),
    TC("Julija živali direktno", "OSEBE", [Turn("Julija skrbi za živali?", any_=["Julija", "živali", "animat"])]),
    TC("Koliko je v družini", "OSEBE", [Turn("Koliko članov ima vaša družina?", any_=["Danilo", "Barbara", "Aljaž", "Julija", "Ana", "Angelca"])]),
    TC("Ana soba direktno", "OSEBE", [Turn("Kakšna je soba Ana?", any_=["ANA", "Ana", "spalnic", "2+2"])]),
    TC("Aljaž soba direktno", "OSEBE", [Turn("Kakšna je soba Aljaž?", must=["50"], any_=["balkon", "klima", "ALJAŽ"])]),

    # ══════════════════════════════════════════
    # D. ŽIVALI (20)
    # ══════════════════════════════════════════
    TC("Katere živali imate", "ŽIVALI", [Turn("Katere živali imate?", any_=["Malajka", "Marsi", "Pepa", "Čarli", "Luna"])]),
    TC("Konji", "ŽIVALI", [Turn("Imate konje?", any_=["konj", "poni", "Malajka", "Marsi"])]),
    TC("Malajka", "ŽIVALI", [Turn("Kdo je Malajka?", any_=["konj", "poni", "Malajka"])]),
    TC("Marsi", "ŽIVALI", [Turn("Kdo je Marsi?", any_=["konj", "poni", "Marsi"])]),
    TC("Pepa pujska", "ŽIVALI", [Turn("Kdo je Pepa?", any_=["pujska", "Pepa", "prašič"])]),
    TC("Čarli oven", "ŽIVALI", [Turn("Kdo je Čarli?", any_=["oven", "ovca", "Čarli"])]),
    TC("Luna psička", "ŽIVALI", [Turn("Kdo je Luna?", any_=["psička", "pes", "Luna"])]),
    TC("Krave", "ŽIVALI", [Turn("Imate krave?", any_=["krav", "govedo", "kmetij", "živali"])]),
    TC("Kokoši", "ŽIVALI", [Turn("Imate kokoši?", any_=["kokoš", "perutn", "živali"])]),
    TC("Mačke", "ŽIVALI", [Turn("Imate mačke?", any_=["mačke", "mucke", "živali"])]),
    TC("Hišni ljubljenčki", "ŽIVALI", [Turn("Ali sprejmete hišne ljubljenčke?", any_=["ne", "žal", "dovoljeni", "prepovedani"])]),
    TC("Psi dovoljeni", "ŽIVALI", [Turn("Ali so psi dovoljeni pri vas?", any_=["ne", "žal", "dovoljeni", "prepovedani"])]),
    TC("Jahanje na ponijih", "ŽIVALI", [Turn("Imate jahanje na ponijih?", any_=["jahanj", "poni", "Malajka", "Marsi"])]),
    TC("Hranjenje živali", "ŽIVALI", [Turn("Ali lahko hranimo živali?", any_=["živali", "hranj", "ogled", "Pepa", "Čarli"])]),
    TC("Ovce", "ŽIVALI", [Turn("Imate ovce?", any_=["Čarli", "oven", "ovca", "kmetij"])]),
    TC("Svinje", "ŽIVALI", [Turn("Imate svinje?", any_=["svinje", "Pepa", "pujska", "živali"])]),
    TC("Koliko živali imate", "ŽIVALI", [Turn("Koliko živali imate na kmetiji?", any_=["živali", "Malajka", "Marsi", "Pepa"])]),
    TC("Domače živali splošno", "ŽIVALI", [Turn("Povejte mi o živalih na vaši kmetiji.", any_=["živali", "Malajka", "Pepa", "Čarli"])]),
    TC("Muče", "ŽIVALI", [Turn("Imate mačke na kmetiji?", any_=["mačke", "mucke"])]),
    TC("Račke", "ŽIVALI", [Turn("Imate račke?", any_=["račke", "perutn", "živali", "kmetij"])]),

    # ══════════════════════════════════════════
    # E. VINA (30)
    # ══════════════════════════════════════════
    TC("Vinska karta splošno", "VINA", [Turn("Kakšna vina ponujate?", must=["Peneča", "Bela", "Rdeča"])]),
    TC("Bela vina samo", "VINA", [Turn("Katera bela vina imate?", any_=["Bela", "Sauvignon", "Rizling", "Muškat"], not_=["Rdeča vina"])]),
    TC("Rdeča vina samo", "VINA", [Turn("Katera rdeča vina ponujate?", any_=["Rdeča", "frankinja", "Pinot"], not_=["Bela vina"])]),
    TC("Peneča vina samo", "VINA", [Turn("Imate penino?", any_=["Doppler", "DIONA", "peneč", "Peneča"])]),
    TC("Sauvignon", "VINA", [Turn("Imate sauvignon?", any_=["Sauvignon", "Frešer"])]),
    TC("Modra frankinja", "VINA", [Turn("Imate modro frankinjo?", any_=["frankinja", "Frankinja", "Skuber", "Greif"])]),
    TC("Rizling", "VINA", [Turn("Imate rizling?", any_=["Rizling", "rizling", "Frešer"])]),
    TC("Muškat", "VINA", [Turn("Imate muškat?", any_=["Muškat", "muškat", "Skuber"])]),
    TC("Modri pinot", "VINA", [Turn("Imate modri pinot?", any_=["Pinot", "pinot", "Frešer"])]),
    TC("Chardonnay", "VINA", [Turn("Imate chardonnay?", any_=["Chardonnay", "Doppler", "DIONA"])]),
    TC("Doppler DIONA podrobnosti", "VINA", [Turn("Povej mi o Doppler DIONA brut.", any_=["Doppler", "DIONA", "brut", "chardonnay", "Chardonnay"])]),
    TC("Cene vin", "VINA", [Turn("Kakšne so cene vin?", any_=["EUR", "30", "26", "14", "19"])]),
    TC("Pokažite vinsko karto", "VINA", [Turn("Pokažite mi vašo vinsko karto.", must=["Peneča", "Bela", "Rdeča"])]),
    TC("Lokalna vina", "VINA", [Turn("Imate lokalna vina?", any_=["vina", "Pohorje", "Doppler", "Frešer"])]),
    TC("Suho vino", "VINA", [Turn("Imate suho vino?", any_=["vino", "vina", "brut", "suho", "frankinja"])]),
    TC("Cena penine", "VINA", [Turn("Koliko stane penina?", any_=["EUR", "Doppler", "peneč"])]),
    TC("Vina poimensko", "VINA", [Turn("Naštejte vsa vina.", any_=["Doppler", "Frešer", "Skuber", "Greif"])]),
    TC("Belo vino katero", "VINA", [Turn("Katero belo vino priporočate?", any_=["Sauvignon", "Rizling", "Muškat", "bel"])]),
    TC("Rdeče vino katero", "VINA", [Turn("Katero rdeče vino priporočate?", any_=["frankinja", "Pinot", "rdec"])]),
    TC("Greif vino", "VINA", [Turn("Imate Greif vino?", any_=["Greif", "frankinja", "Rizling", "vino"])]),
    TC("Frešer vino", "VINA", [Turn("Imate Frešer vino?", any_=["Frešer", "Sauvignon", "Pinot", "vino"])]),
    TC("Skuber vino", "VINA", [Turn("Imate Skuber vino?", any_=["Skuber", "frankinja", "Muškat", "vino"])]),
    TC("Leber vino", "VINA", [Turn("Imate Leber vino?", any_=["Leber", "Muškat", "vino"])]),
    TC("Vinska karta bela in rdeča", "VINA", [Turn("Kakšne bele in rdeče vino imate?", any_=["Bela", "Rdeča", "Sauvignon", "frankinja"])]),
    TC("CTA ni", "VINA", [Turn("Kakšna vina imate?", not_=["Za podrobnosti z veseljem", "z veseljem povem več"])]),
    TC("Penina brez CTA", "VINA", [Turn("Katera penina je na voljo?", not_=["Za podrobnosti z veseljem"])]),
    TC("Vino cena detail", "VINA", [Turn("Kakšna je cena za Doppler DIONA?", any_=["Doppler", "DIONA", "EUR"])]),
    TC("Rdeče ali belo", "VINA", [Turn("Imate rdeče in belo vino?", any_=["Rdeča", "Bela", "frankinja", "Sauvignon"])]),
    TC("Penino priporoči", "VINA", [Turn("Priporočite penino.", any_=["Doppler", "DIONA", "peneč"])]),
    TC("Vino za meso", "VINA", [Turn("Katero vino priporočate k mesu?", any_=["rdec", "frankinja", "Rdeč", "Greif"])]),

    # ══════════════════════════════════════════
    # F. MENIJI (30)
    # ══════════════════════════════════════════
    TC("Vikend meni", "MENIJI", [Turn("Kakšen je vikend meni?", any_=["vikend", "sobota", "nedelja", "kosilo", "meni"])]),
    TC("Kosilo kaj ponujate", "MENIJI", [Turn("Kaj ponujate za kosilo?", any_=["meni", "kosilo", "vikend"])]),
    TC("4-hodni meni", "MENIJI", [Turn("Kakšen je 4-hodni meni?", must=["4"], any_=["hodni", "EUR", "36"])]),
    TC("5-hodni meni", "MENIJI", [Turn("Kakšen je 5-hodni meni?", must=["5"], any_=["hodni", "EUR", "43"])]),
    TC("6-hodni meni", "MENIJI", [Turn("Kakšen je 6-hodni meni?", must=["6"], any_=["hodni", "EUR", "53"])]),
    TC("7-hodni meni", "MENIJI", [Turn("Kakšen je 7-hodni meni?", must=["7"], any_=["hodni", "EUR", "62"])]),
    TC("Cena vikend meni", "MENIJI", [Turn("Koliko stane vikend meni?", any_=["36", "EUR"])]),
    TC("Cena degustacijski meni", "MENIJI", [Turn("Koliko stane degustacijski meni?", any_=["36", "43", "53", "62", "EUR"])]),
    TC("Kdaj kosila", "MENIJI", [Turn("Kdaj imate kosila?", any_=["sobota", "nedelja", "12", "15"])]),
    TC("Ura kosila", "MENIJI", [Turn("Ob kateri uri je kosilo?", any_=["12", "15", "sobota", "nedelja"])]),
    TC("Med tednom kosilo", "MENIJI", [Turn("Ali ponujate kosilo med tednom?", any_=["sreda", "četrtek", "petek", "degustat", "teden"])]),
    TC("Tedenski meni", "MENIJI", [Turn("Kaj je na tedenskem meniju?", any_=["4-hodni", "5-hodni", "hodni", "degustat"])]),
    TC("Popust otroci meni", "MENIJI", [Turn("Ali je popust za otroke pri kosilu?", any_=["50%", "otrok", "popust", "4–12", "4-12"])]),
    TC("Zadnji prihod kosilo", "MENIJI", [Turn("Kdaj je zadnji prihod na kosilo?", any_=["15", "zadnji"])]),
    TC("Gibanica", "MENIJI", [Turn("Kakšna je gibanica pri vas?", any_=["gibanica", "Pohorje", "specialitet"])]),
    TC("Kaj je v 6-hodnem", "MENIJI", [Turn("Kaj je v 6-hodnem meniju?", must=["6"], any_=["hodni", "EUR", "53"])]),
    TC("Aktualni meni", "MENIJI", [Turn("Kakšen je aktualni meni?", any_=["meni", "vikend", "kosilo", "EUR"])]),
    TC("Vegetarijansko", "MENIJI", [Turn("Ali imate vegetarijansko ponudbo?", any_=["vegetarij", "pokličite", "info", "meni", "naroč"])]),
    TC("Kosila ob ponedeljkih", "MENIJI", [Turn("Ali imate kosila ob ponedeljkih?", any_=["ponedeljek", "torek", "zaprta", "ne", "sobota"])]),
    TC("Vinska degustacija ob meniju", "MENIJI", [Turn("Koliko stane vinska degustacija ob meniju?", any_=["15", "20", "25", "29", "EUR"])]),
    TC("Min oseb degustacija", "MENIJI", [Turn("Koliko oseb je minimalno za degustacijo?", any_=["6", "min"])]),
    TC("4-hodni follow-up", "MENIJI", [
        Turn("Kakšni degustacijski meniji so na voljo?", any_=["4-hodni", "5-hodni", "hodni"]),
        Turn("4", any_=["4-hodni", "36", "hodni", "EUR"]),
    ]),
    TC("5-hodni follow-up", "MENIJI", [
        Turn("Naštej tedenski degustacijske menije.", any_=["4-hodni", "5-hodni", "hodni"]),
        Turn("5", any_=["5-hodni", "43", "hodni", "EUR"]),
    ]),
    TC("6-hodni follow-up", "MENIJI", [
        Turn("Kakšni degustacijski meniji so na voljo med tednom?", any_=["4-hodni", "hodni"]),
        Turn("6", any_=["6-hodni", "53", "EUR"]),
    ]),
    TC("Meni za praznovanje", "MENIJI", [Turn("Ali imate posebne menije za praznovanje?", any_=["meni", "degustat", "pokličite", "posebn"])]),
    TC("Popust otrok vikend", "MENIJI", [Turn("Koliko stane vikend meni za otroka?", any_=["50%", "18", "otrok", "popust", "EUR"])]),
    TC("Šampanjec meni", "MENIJI", [Turn("Ali je šampanjec vključen v meni?", any_=["penin", "vinska", "degustacij", "EUR", "meni"])]),
    TC("Meni rezervacija", "MENIJI", [Turn("Kako rezerviram mizo za kosilo?", any_=["rezerv", "datum", "pokličite", "sobota"])]),
    TC("Jedilnica", "MENIJI", [Turn("Kateri jedilnici imate?", any_=["peč", "vrt", "jedilnic", "15", "35"])]),
    TC("Koliko oseb jedilnica", "MENIJI", [Turn("Koliko oseb sprejme vaša jedilnica?", any_=["15", "35", "peč", "vrt"])]),

    # ══════════════════════════════════════════
    # G. CENE (20)
    # ══════════════════════════════════════════
    TC("Cena nočitve splošno", "CENE", [Turn("Koliko stane nočitev?", must=["50"])]),
    TC("Cena sobe splošno", "CENE", [Turn("Kakšne so cene sob?", must=["50"])]),
    TC("Cena vikend meni G", "CENE", [Turn("Koliko stane vikend kosilo?", any_=["36", "EUR"])]),
    TC("Cena 4-hodni G", "CENE", [Turn("Koliko stane 4-hodni meni?", any_=["36", "EUR"])]),
    TC("Cena 7-hodni G", "CENE", [Turn("Koliko stane 7-hodni meni?", any_=["62", "EUR"])]),
    TC("Zajtrk cena", "CENE", [Turn("Je zajtrk vključen ali se plača posebej?", any_=["vključen", "vključ", "zajtrk", "50"])]),
    TC("Cena otrok nočitev", "CENE", [Turn("Kakšna je cena za otroke pri nočitvi?", any_=["50%", "popust", "otrok", "5", "12"])]),
    TC("Cena otrok meni", "CENE", [Turn("Kakšna je cena za otroke pri kosilu?", any_=["50%", "popust", "otrok", "4", "12"])]),
    TC("Cena večerja", "CENE", [Turn("Koliko stane večerja?", any_=["25", "EUR", "večerj"])]),
    TC("Cena nastanitev 2 osebi", "CENE", [Turn("Koliko stane nastanitev za 2 osebi?", must=["50"])]),
    TC("Ali so cene all-inclusive", "CENE", [Turn("Ali so cene all-inclusive?", any_=["zajtrk", "vključen", "večerj", "naroč"])]),
    TC("Cena vikend", "CENE", [Turn("Kakšna je cena za vikend?", any_=["50", "soba", "nočitev"])]),
    TC("Cena skupna nočitev + večerja", "CENE", [Turn("Koliko skupaj stane nočitev z večerjo?", any_=["50", "25", "EUR", "skupaj"])]),
    TC("Cena otroci do 5 let", "CENE", [Turn("Ali so otroci do 5 let brezplačni?", any_=["brezplač", "5 let", "brez"])]),
    TC("Cene menijev vse", "CENE", [Turn("Kakšne so cene vseh menijev?", any_=["36", "43", "53", "62", "EUR"])]),
    TC("Popust poleti", "CENE", [Turn("Ali imate poletne popuste?", any_=["popust", "cena", "soba", "polet"])]),
    TC("Cena 5-hodni G", "CENE", [Turn("Koliko stane 5-hodni degustacijski meni?", any_=["43", "EUR"])]),
    TC("Cena 6-hodni G", "CENE", [Turn("Koliko stane 6-hodni degustacijski meni?", any_=["53", "EUR"])]),
    TC("Cena penina", "CENE", [Turn("Koliko stane penina?", any_=["EUR", "Doppler", "peneč"])]),
    TC("Cena skupaj 3 noči", "CENE", [Turn("Koliko stane 3 nočitve za 2 osebi?", any_=["50", "EUR", "nočitev"])]),

    # ══════════════════════════════════════════
    # H. KONTAKT & LOKACIJA (20)
    # ══════════════════════════════════════════
    TC("Kje ste", "KONTAKT", [Turn("Kje ste?", any_=["Planica", "Fram", "Pohorje", "naslov"])]),
    TC("Naslov", "KONTAKT", [Turn("Kakšen je vaš naslov?", any_=["Planica", "Fram", "2313"])]),
    TC("Kako pridem do vas", "KONTAKT", [Turn("Kako pridem do vas?", any_=["Fram", "A1", "Pohorje", "minut", "avtocest"])]),
    TC("Parkirišče", "KONTAKT", [Turn("Imate parkirišče?", any_=["parking", "parkirišč", "brezplačn"])]),
    TC("Parkirišče brezplačno", "KONTAKT", [Turn("Je parkirišče brezplačno?", any_=["brezplač", "parking"])]),
    TC("Kdaj odprti", "KONTAKT", [Turn("Kdaj ste odprti?", any_=["sobota", "nedelja", "12", "20", "15"])]),
    TC("Delovni časi", "KONTAKT", [Turn("Kakšni so vaši delovni časi?", any_=["sobota", "nedelja", "12"])]),
    TC("Ob nedeljah odprti", "KONTAKT", [Turn("Ali ste odprti ob nedeljah?", any_=["nedelja", "da", "12", "odprt"])]),
    TC("Ob ponedeljkih zaprti", "KONTAKT", [Turn("Ali ste odprti ob ponedeljkih?", any_=["ponedeljek", "zaprt", "torek", "ne"])]),
    TC("Telefonska kmetija", "KONTAKT", [Turn("Kakšna je telefonska številka kmetije?", any_=["031", "330", "113", "02"])]),
    TC("Email kmetija", "KONTAKT", [Turn("Kakšen je vaš email?", any_=["info@", "kovacnik", "email", "e-pošta"])]),
    TC("Spletna stran", "KONTAKT", [Turn("Ali imate spletno stran?", any_=["www", "kovacnik", "spletna"])]),
    TC("WiFi splošno", "KONTAKT", [Turn("Imate WiFi?", any_=["WiFi", "wifi", "brezžičn"])]),
    TC("Razdalja Maribor", "KONTAKT", [Turn("Kako daleč ste od Maribora?", any_=["minut", "km", "Maribor", "Fram", "A1"])]),
    TC("Koordinate", "KONTAKT", [Turn("Kakšne so koordinate kmetije?", any_=["46", "15", "koordinat", "Planica", "Fram"])]),
    TC("Navigacija", "KONTAKT", [Turn("Kako do vas z navigacijo?", any_=["Planica", "Fram", "Kovačnik", "navigac"])]),
    TC("Fotografije", "KONTAKT", [Turn("Ali imate fotografije sob?", any_=["spletna", "www", "kovacnik", "pokličite", "kontakt"])]),
    TC("Rezervacija po telefonu", "KONTAKT", [Turn("Ali lahko rezerviram po telefonu?", any_=["031", "da", "pokličite", "telefon", "sobe", "mize"])]),
    TC("Rezervacija po emailu", "KONTAKT", [Turn("Ali sprejmete rezervacije po emailu?", any_=["info@", "email", "pokličite", "kontakt", "sobe", "mize"])]),
    TC("Dostop z invalidskim vozičkom", "KONTAKT", [Turn("Ali imate dostop za invalide?", any_=["pokličite", "kontakt", "031", "dostop", "informacij"])]),

    # ══════════════════════════════════════════
    # I. OUTDOOR / AKTIVNOSTI (20)
    # ══════════════════════════════════════════
    TC("Smučišče blizu", "OUTDOOR", [Turn("Je v bližini kakšno smučišče?", must=["Areh"], any_=["Mariborsko", "25", "35"])]),
    TC("Areh razdalja", "OUTDOOR", [Turn("Kako daleč je Areh od vas?", any_=["Areh", "25", "35", "minut"])]),
    TC("Mariborsko Pohorje", "OUTDOOR", [Turn("Je Mariborsko Pohorje blizu?", any_=["Mariborsko", "Areh", "minut", "25"])]),
    TC("Smučišče Areh direktno", "OUTDOOR", [Turn("Smučišče Areh - kako daleč?", any_=["Areh", "25", "35", "minut"])]),
    TC("Terme blizu", "OUTDOOR", [Turn("So v bližini terme?", any_=["Zreče", "Ptuj", "terme", "30", "40"])]),
    TC("Terme Zreče", "OUTDOOR", [Turn("Kje so Terme Zreče?", any_=["Zreče", "terme", "30", "minut"])]),
    TC("Pohodi", "OUTDOOR", [Turn("So v bližini pohodniške poti?", any_=["Pohorje", "pohod", "sprehod", "gozd"])]),
    TC("Slap Skalca", "OUTDOOR", [Turn("Kje je slap Skalca?", any_=["Skalca", "slap", "sprehod", "bližin"])]),
    TC("Kolesarjenje", "OUTDOOR", [Turn("Ali je mogoče kolesariti v okolici?", any_=["koles", "izpos", "Pohorje"])]),
    TC("Izposoja koles", "OUTDOOR", [Turn("Ali imate izposojo koles?", any_=["koles", "izpos", "dogovor"])]),
    TC("Izleti v okolici", "OUTDOOR", [Turn("Kaj je v okolici za izlete?", any_=["Pohorje", "pohod", "slap", "Areh"])]),
    TC("Aktivnosti otroci", "OUTDOOR", [Turn("Katere aktivnosti priporočate za otroke?", any_=["jahanj", "poni", "živali", "animat"])]),
    TC("Jahanje brezplačno", "OUTDOOR", [Turn("Je jahanje brezplačno?", any_=["jahanj", "poni", "kontakt", "pokličite", "cena"])]),
    TC("Wellness savna", "OUTDOOR", [Turn("Imate savno ali wellness?", any_=["terme", "Zreče", "sauna", "wellness", "ne"])]),
    TC("Naravo pot", "OUTDOOR", [Turn("Priporočite mi sprehod v naravi.", any_=["Pohorje", "pohod", "sprehod", "Skalca"])]),
    TC("Zimske aktivnosti", "OUTDOOR", [Turn("Kaj je na voljo pozimi?", any_=["Areh", "smučišč", "Mariborsko", "minut", "smučanj"])]),
    TC("Poletne aktivnosti", "OUTDOOR", [Turn("Kaj priporočate za poletje?", any_=["pohod", "kolesarj", "jahanj", "živali", "Pohorje", "aktiv"])]),
    TC("Animacija otrok", "OUTDOOR", [Turn("Imate animacijo za otroke?", any_=["animat", "otroci", "jahanj", "živali"])]),
    TC("Kaj početi ob dežju", "OUTDOOR", [Turn("Kaj počnemo ob deževnem vremenu?", any_=["živali", "ogled", "kmetij", "domač", "pokličite"])]),
    TC("Areh smučanje", "OUTDOOR", [Turn("Ali je Areh dobro smučišče?", any_=["Areh", "Mariborsko", "minut", "smučišč"])]),

    # ══════════════════════════════════════════
    # J. LOKALNI IZDELKI (15)
    # ══════════════════════════════════════════
    TC("Domači izdelki splošno", "IZDELKI", [Turn("Imate domače pridelke?", any_=["bunka", "salama", "marmelad", "liker", "domač"])]),
    TC("Salama", "IZDELKI", [Turn("Prodajate domačo salamo?", any_=["salama", "mesnin", "domač"])]),
    TC("Marmelada", "IZDELKI", [Turn("Imate domačo marmelado?", any_=["marmelad", "domač", "kompot"])]),
    TC("Liker", "IZDELKI", [Turn("Prodajate domači liker?", any_=["liker", "žganje", "domač"])]),
    TC("Bunka", "IZDELKI", [Turn("Imate Pohorsko bunko?", any_=["bunka", "mesnin", "sušen"])]),
    TC("Sirček", "IZDELKI", [Turn("Imate domači sirček?", any_=["sirček", "sirek", "Frešer"])]),
    TC("Kje kupim izdelke", "IZDELKI", [Turn("Kje kupim domače izdelke?", any_=["pokličite", "031", "Barbara", "nakup", "dogovor"])]),
    TC("Darilni paketi", "IZDELKI", [Turn("Ali imate darilne pakete?", any_=["darilni", "paket", "bon", "pokličite"])]),
    TC("Darilni boni", "IZDELKI", [Turn("Imate darilne bone?", any_=["bon", "darilni", "pokličite"])]),
    TC("Pošiljanje po pošti", "IZDELKI", [Turn("Ali pošiljate domače izdelke po pošti?", any_=["pokličite", "dogovor", "kontakt", "031", "ne", "kmetij"])]),
    TC("Namazni sir", "IZDELKI", [Turn("Imate domači namaz?", any_=["namaz", "sirček", "bučni", "zeliščni", "domač"])]),
    TC("Nakup med obiskom", "IZDELKI", [Turn("Ali kupim domače izdelke med obiskom?", any_=["domač", "pokličite", "dogovor"])]),
    TC("Kaj je v darilnem paketu", "IZDELKI", [Turn("Kaj je v darilnem paketu?", any_=["domač", "pokličite", "bon", "paket"])]),
    TC("Spletna prodaja", "IZDELKI", [Turn("Ali imate spletno prodajo?", any_=["spletna", "www", "pokličite", "dogovor", "nimamo", "prodaje", "kmetij"])]),
    TC("Kaj ponujate za nakup", "IZDELKI", [Turn("Kaj prodajate?", any_=["bunka", "salama", "marmelad", "liker", "sirček"])]),

    # ══════════════════════════════════════════
    # K. REZERVACIJE - SOBA (multi-turn) (30)
    # ══════════════════════════════════════════
    TC("Rezervacija sobe - start", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "kdaj", "prihod", "sobo"]),
    ]),
    TC("Rezervacija sobe - z datumom", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo za 15. julij.", any_=["datum", "nočitev", "koliko", "15.7"]),
    ]),
    TC("Rezervacija sobe - datum + nočitve", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo za 15.7.2026 za 3 nočitve.", any_=["oseb", "koliko", "datum"]),
    ]),
    TC("Rezervacija - 4 nocitve ne menu", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("1.8.2026", any_=["nočitev", "koliko", "8"]),
        Turn("4", not_=["4-hodni", "degustacij", "meni"], any_=["oseb", "nočitev", "noči", "4"]),
    ]),
    TC("Rezervacija - 3 nočitve", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("10.9.2026", any_=["nočitev", "koliko"]),
        Turn("3", not_=["3-hodni", "degustacij"], any_=["oseb", "nočitev", "noči"]),
    ]),
    TC("Rezervacija - nočitve 2", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("21.10.2026", any_=["nočitev", "koliko"]),
        Turn("2 nočitvi", any_=["oseb", "koliko", "noči"]),
    ]),
    TC("Rezervacija - 5 nočitev", "REZERVACIJE_SOBA", [
        Turn("Rezerviraj sobo.", any_=["datum", "prihod"]),
        Turn("5.7.2026", any_=["nočitev", "koliko"]),
        Turn("5 nočitev", not_=["5-hodni", "degustacij"], any_=["oseb", "noči", "nočitev"]),
    ]),
    TC("Rezervacija - 6 nočitev", "REZERVACIJE_SOBA", [
        Turn("Rad bi sobo za 6 nočitev.", any_=["datum", "prihod", "nočitev"]),
        Turn("12.6.2026", any_=["nočitev", "oseb", "koliko", "ALJAZ", "JULIJA"]),
        Turn("6", not_=["6-hodni", "degustacij"], any_=["oseb", "noči", "nočitev", "ALJAZ", "soba"]),
    ]),
    TC("Rezervacija - 7 nočitev", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo za 7 nočitev.", any_=["datum", "prihod"]),
        Turn("5.8.2026", any_=["nočitev", "koliko"]),
        Turn("7", not_=["7-hodni", "degustacij"], any_=["oseb", "noči", "nočitev", "ALJAZ", "soba"]),
    ]),
    TC("Rezervacija - 2 osebi", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo za 2 osebi.", any_=["datum", "prihod"]),
    ]),
    TC("Rezervacija - otroci info", "REZERVACIJE_SOBA", [
        Turn("Imamo 2 odrasla in 2 otroka - ali imate sobo?", any_=["soba", "2+2", "kapacitet", "datum"]),
    ]),
    TC("Rezervacija - prekliči start", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Nehaj", any_=["preklical", "preklic", "kako", "pomagam"]),
    ]),
    TC("Rezervacija - prekliči z stop", "REZERVACIJE_SOBA", [
        Turn("Rezerviraj sobo.", any_=["datum", "prihod"]),
        Turn("stop", any_=["preklical", "preklic", "kako", "pomagam"]),
    ]),
    TC("Rezervacija ne prekliče pri NE", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("15.8.2026", any_=["nočitev", "koliko"]),
        Turn("3", not_=["3-hodni", "meni", "degustacij"]),
    ]),
    TC("Rezervacija - topik switch vina med booking", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("16.9.2026", any_=["nočitev", "koliko"]),
        Turn("Kakšna vina imate?", any_=["vina", "vino", "Nadaljujemo", "rezervacij"]),
    ]),
    TC("Rezervacija - topik switch živali", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("7.10.2026", any_=["nočitev", "koliko"]),
        Turn("Katere živali imate?", any_=["živali", "Malajka", "Nadaljujemo", "rezervacij"]),
    ]),
    TC("Rezervacija - topik switch smučišče", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("20.1.2027", any_=["nočitev", "koliko"]),
        Turn("Je v bližini smučišče?", any_=["Areh", "Mariborsko", "Nadaljujemo"]),
    ]),
    TC("Booking ne menu po menuju", "REZERVACIJE_SOBA", [
        Turn("Kakšni tedenski meniji so?", any_=["hodni", "degustat", "4-hodni"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("1.7.2026", any_=["nočitev", "koliko"]),
        Turn("4", not_=["4-hodni meni", "degustacij"], any_=["oseb", "noči", "nočitev"]),
    ]),
    TC("Rezervacija za familijo", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo za 4 osebe, 2 odrasla in 2 otroka.", any_=["datum", "prihod"]),
    ]),
    TC("Rezervacija soba z rezervacijo mize", "REZERVACIJE_SOBA", [
        Turn("Ali lahko rezerviram sobo in mizo?", any_=["sobo", "mizo", "datum", "rezerv"]),
    ]),
    TC("Soba splošno pred rezervacijo", "REZERVACIJE_SOBA", [
        Turn("Najprej me zanima soba, potem pa rezerviram.", any_=["soba", "ALJAŽ", "JULIJA", "ANA", "50"]),
    ]),
    TC("Rezervacija po jeziku slovenščina", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo, prosim.", any_=["datum", "prihod"]),
    ]),
    TC("Rezervacija z začetnim datumom", "REZERVACIJE_SOBA", [
        Turn("Rad bi rezerviral sobo od 1.7.2026.", any_=["nočitev", "koliko"]),
    ]),
    TC("Rezervacija splošno", "REZERVACIJE_SOBA", [
        Turn("Kako rezerviram sobo?", any_=["datum", "rezerv", "pokličite", "031"]),
    ]),
    TC("Rezervacija dostopnost", "REZERVACIJE_SOBA", [
        Turn("Ali imate prosto sobo za julij?", any_=["datum", "nočitev", "kdaj", "julij"]),
    ]),
    TC("Rezervacija zgodaj check-in", "REZERVACIJE_SOBA", [
        Turn("Ali je možen zgodnji check-in?", any_=["14", "check", "pokličite", "dogovor"])
    ]),
    TC("Rezervacija pozni check-out", "REZERVACIJE_SOBA", [
        Turn("Ali je možen pozni check-out?", any_=["10", "odjav", "pokličite", "dogovor"])
    ]),
    TC("Rezervacija za poroke", "REZERVACIJE_SOBA", [
        Turn("Imate prostore za poroke?", any_=["pokličite", "kontakt", "031", "dogovor", "sobo", "sobe", "ALJAŽ"])
    ]),
    TC("Rezervacija poletna minimalca", "REZERVACIJE_SOBA", [
        Turn("Koliko nočitev je min poleti?", any_=["3", "junij", "julij", "avgust", "polet"])
    ]),
    TC("Rezervacija izven sezone", "REZERVACIJE_SOBA", [
        Turn("Koliko nočitev min izven poletne sezone?", any_=["2", "min"])
    ]),

    # ══════════════════════════════════════════
    # L. REZERVACIJE - MIZA (15)
    # ══════════════════════════════════════════
    TC("Rezervacija mize - start", "REZERVACIJE_MIZA", [
        Turn("Rad bi rezerviral mizo za kosilo.", any_=["datum", "sobota", "nedelja", "kdaj"]),
    ]),
    TC("Rezervacija mize - z datumom", "REZERVACIJE_MIZA", [
        Turn("Rad bi rezerviral mizo za 12.7.2026.", any_=["ura", "uri", "čas", "koliko", "15:00"])
    ]),
    TC("Rezervacija mize - samo ob vikendih", "REZERVACIJE_MIZA", [
        Turn("Ali je miza na voljo ob sredi?", any_=["sobota", "nedelja", "vikend", "sreda"])
    ]),
    TC("Rezervacija mize - jedilnica", "REZERVACIJE_MIZA", [
        Turn("Kateri jedilnici imate?", any_=["peč", "vrt", "15", "35"])
    ]),
    TC("Rezervacija mize za skupino", "REZERVACIJE_MIZA", [
        Turn("Rad bi rezerviral mizo za 20 oseb.", any_=["datum", "sobota", "peč", "vrt", "35"])
    ]),
    TC("Rezervacija mize - prekliči", "REZERVACIJE_MIZA", [
        Turn("Rad bi rezerviral mizo.", any_=["datum", "sobota"]),
        Turn("Nehaj", any_=["preklical", "preklic", "pomagam"])
    ]),
    TC("Rezervacija mize splošno", "REZERVACIJE_MIZA", [
        Turn("Kako rezerviram mizo?", any_=["datum", "sobota", "pokličite", "031"])
    ]),
    TC("Miza - ura kosila", "REZERVACIJE_MIZA", [
        Turn("Ob kateri uri je kosilo?", any_=["12", "15", "sobota", "nedelja"])
    ]),
    TC("Miza - zadnji prihod", "REZERVACIJE_MIZA", [
        Turn("Kdaj je zadnji prihod na kosilo?", any_=["15", "zadnji", "15:00"])
    ]),
    TC("Miza - prihod 16:00", "REZERVACIJE_MIZA", [
        Turn("Ali je miza na voljo ob 16:00?", any_=["15", "zadnji", "16"])
    ]),
    TC("Miza za 2 osebi", "REZERVACIJE_MIZA", [
        Turn("Rad bi mizo za 2 osebi.", any_=["datum", "sobota", "nedelja"])
    ]),
    TC("Miza za 35 oseb", "REZERVACIJE_MIZA", [
        Turn("Ali sprejmete 35 oseb?", any_=["35", "vrt", "jedilnic", "pokličite", "sobe", "prosta"])
    ]),
    TC("Miza skupaj z degustacijo", "REZERVACIJE_MIZA", [
        Turn("Ali je ob kosilu možna degustacija?", any_=["vikend", "meni", "degustat", "pokličite"])
    ]),
    TC("Miza med tednom", "REZERVACIJE_MIZA", [
        Turn("Ali imate kosilo med tednom?", any_=["sreda", "četrtek", "petek", "degustat", "sobota"])
    ]),
    TC("Miza za otroke", "REZERVACIJE_MIZA", [
        Turn("Imate posebne cene za otroke?", any_=["50%", "otrok", "4-12", "popust"])
    ]),

    # ══════════════════════════════════════════
    # M. EDGE CASES & ZANKE (40)
    # ══════════════════════════════════════════
    TC("Kratko OK", "EDGE", [Turn("OK", any_=["Kovačnik", "pomoč", "vprašanj", "da", "pomagam", "kosilo"])]),
    TC("Samo da", "EDGE", [Turn("Da", any_=["Kovačnik", "pomoč", "vprašanj", "kako", "pomagam", "prosim", "natančnej", "datum", "rezerv", "kmetij"])]),
    TC("Samo ne", "EDGE", [Turn("Ne", any_=["Kovačnik", "pomoč", "vprašanj", "kako", "pomagam", "prosim"])]),
    TC("Samo a", "EDGE", [Turn("a", any_=["pomoč", "Kovačnik", "vprašanj", "pomagam", "prosim"])]),
    TC("Pika", "EDGE", [Turn(".", any_=["pomoč", "Kovačnik", "vprašanj", "pomagam"])]),
    TC("Vprašaj", "EDGE", [Turn("?", any_=["pomoč", "Kovačnik", "vprašanj", "pomagam"])]),
    TC("Ponovi isto vprašanje", "EDGE", [
        Turn("Kakšna vina imate?", any_=["vina", "vino"]),
        Turn("Kakšna vina imate?", any_=["vina", "vino"]),
    ]),
    TC("Vina nato rezervacija nato vina", "EDGE", [
        Turn("Kakšna vina imate?", any_=["vina", "Peneča"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Kakšna vina imate?", any_=["vina", "Nadaljujemo", "rezervacij"]),
    ]),
    TC("Hallucination trap traktor", "EDGE", [
        Turn("Kakšen traktor imate?", not_=["Tur", "Claas", "John Deere", "Fendt", "New Holland"]),
    ]),
    TC("Hallucination trap lastnik", "EDGE", [
        Turn("Kdo je lastnik Kovačnik AI?", not_=["Google", "Microsoft", "OpenAI", "Anthropic"]),
    ]),
    TC("Hallucination trap rezervacija danes", "EDGE", [
        Turn("Ali imate prosto danes zvečer?", any_=["datum", "pokličite", "031", "soba", "prihod", "pomagam", "rezervacij"]),
    ]),
    TC("Hallucination trap cena", "EDGE", [
        Turn("Koliko stane soba za 1 noč?", must=["50"]),
    ]),
    TC("Ponovi rezervacijo po prekliču", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Nehaj", any_=["preklical"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
    ]),
    TC("CTA zanka vina", "EDGE", [
        Turn("Kakšna vina imate?", not_=["Za podrobnosti z veseljem", "z veseljem povem več"]),
        Turn("Kakšna vina imate?", not_=["Za podrobnosti z veseljem"]),
    ]),
    TC("Zmeda soba vs oseba po disambiguacija", "EDGE", [
        Turn("Kakšna je soba Aljaž?", must=["50"], any_=["ALJAŽ", "balkon"]),
        Turn("Kdo je Aljaž sin?", any_=["sin", "harmonik", "gospodar"]),
    ]),
    TC("Neznana beseda", "EDGE", [
        Turn("Xyzxyz", any_=["Kovačnik", "pomoč", "vprašanj", "razumem", "pomagam", "kmetij"]),
    ]),
    TC("Anglešky hello rooms", "EDGE", [
        Turn("Do you have rooms available?", any_=["room", "soba", "Kovačnik", "50"]),
    ]),
    TC("Nemško Zimmer", "EDGE", [
        Turn("Haben Sie ein Zimmer frei?", any_=["zimmer", "sobe", "datum", "prihod", "Kovačnik"]),
    ]),
    TC("Dolgo sporočilo", "EDGE", [
        Turn("Pozdravljeni, rad bi preveril, ali imate na voljo sobo za naše stanovanje s 4 člani - 2 odrasla in 2 otroka - za teden dni v juliju ali avgustu.", any_=["datum", "prihod", "soba", "nočitev"]),
    ]),
    TC("Duplicirano vprašanje soba", "EDGE", [
        Turn("Koliko stane soba? Koliko stane soba?", must=["50"]),
    ]),
    TC("Mešano slovensko-angleško", "EDGE", [
        Turn("I want to book a room za julij.", any_=["datum", "prihod", "soba", "book"]),
    ]),
    TC("Zanka po disambiguacija", "EDGE", [
        Turn("Kdo je Ana?", any_=["soba", "hči", "ali", "Ali"]),
        Turn("Ana iz družine.", any_=["hči", "najmlajš", "Ana"]),
        Turn("Kdo je Ana?", any_=["soba", "hči", "ali", "Ali"]),
    ]),
    TC("Booking po tem ko vprašal soba", "EDGE", [
        Turn("Kakšna je soba Julija?", any_=["JULIJA", "50"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
    ]),
    TC("Booking po tem ko vprašal vino", "EDGE", [
        Turn("Kakšna vina imate?", must=["Peneča"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
    ]),
    TC("Smučišče med rezervacijo in nazaj", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Je v bližini smučišče?", any_=["Areh", "Nadaljujemo"]),
        Turn("15.1.2027", any_=["nočitev", "koliko"]),
    ]),
    TC("NE pri potrditvi = preklic", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("15.8.2026", any_=["nočitev", "koliko"]),
        Turn("2", not_=["2-hodni", "meni"]),
        Turn("2 osebi", any_=["oseb", "datum", "soba", "ime"]),
    ]),
    TC("Booking ne rezervira pri samo info", "EDGE", [
        Turn("Ali je soba Aljaž prosta za julij?", any_=["ALJAŽ", "50", "balkon", "soba", "datum", "prihod"]),
    ]),
    TC("Vprašanje o ceni med booking", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Koliko stane nočitev?", any_=["50", "Nadaljujemo", "rezervacij"]),
    ]),
    TC("Vprašanje o živalih med booking", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Imate konje?", any_=["konj", "poni", "Nadaljujemo"]),
    ]),
    TC("Topik switch osebe med booking", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Kdo je Aljaž?", any_=["Aljaž", "Nadaljujemo", "soba", "sin"]),
    ]),
    TC("Nasvidenje med booking", "EDGE", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Nasvidenje!", any_=["nasvidenje", "adijo", "veselj", "čakamo"]),
    ]),

    # ══════════════════════════════════════════
    # N. CELOTNI TOKI (full end-to-end) (20)
    # ══════════════════════════════════════════
    TC("Pozdrav nato info nato rezervacija", "CELOTNO", [
        Turn("Živjo!", any_=["pozdravlj", "Kovačnik"]),
        Turn("Kakšne sobe imate?", any_=["ALJAŽ", "JULIJA", "ANA"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
    ]),
    TC("Info o soba nato cena nato booking", "CELOTNO", [
        Turn("Kakšna je soba Aljaž?", must=["50"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
    ]),
    TC("Meniji nato booking", "CELOTNO", [
        Turn("Kakšni meniji so?", any_=["meni", "kosilo", "vikend"]),
        Turn("Rad bi rezerviral mizo za kosilo.", any_=["datum", "sobota"]),
    ]),
    TC("Vina nato meniji", "CELOTNO", [
        Turn("Kakšna vina imate?", must=["Peneča"]),
        Turn("Kakšni vikend meniji so?", any_=["meni", "vikend", "36"]),
    ]),
    TC("Sobe nato živali nato sobe", "CELOTNO", [
        Turn("Kakšne sobe imate?", any_=["ALJAŽ", "JULIJA"]),
        Turn("Katere živali imate?", any_=["Malajka", "Pepa"]),
        Turn("Koliko stane soba?", must=["50"]),
    ]),
    TC("Oseba nato soba disambiguation", "CELOTNO", [
        Turn("Kdo je Aljaž?", any_=["soba", "sin", "Ali"]),
        Turn("Me zanima soba.", any_=["ALJAŽ", "50", "soba"]),
    ]),
    TC("Booking preklic nato info", "CELOTNO", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("stop", any_=["preklical"]),
        Turn("Kakšna vina imate?", must=["Peneča"]),
    ]),
    TC("Info lokacija nato booking", "CELOTNO", [
        Turn("Kje ste?", any_=["Planica", "Fram"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
    ]),
    TC("Smučišče nato booking", "CELOTNO", [
        Turn("Kje je smučišče Areh?", any_=["Areh", "minut"]),
        Turn("Super, rad bi rezerviral sobo za januar.", any_=["datum", "prihod"]),
    ]),
    TC("Booking nato vina brez zanke", "CELOTNO", [
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("16.9.2026", any_=["nočitev", "koliko"]),
        Turn("Kakšna vina imate?", any_=["vina", "Nadaljujemo"]),
        Turn("2", not_=["2-hodni", "meni"], any_=["oseb", "noči"]),
    ]),
    TC("Cena nato booking nato cena", "CELOTNO", [
        Turn("Koliko stane nočitev?", must=["50"]),
        Turn("Rad bi rezerviral sobo.", any_=["datum", "prihod"]),
        Turn("Koliko stane nočitev?", any_=["50", "Nadaljujemo"]),
    ]),
    TC("Pozdrav in info splošno", "CELOTNO", [
        Turn("Pozdravljeni!", any_=["pozdravlj", "Kovačnik"]),
        Turn("Kaj ponujate?", any_=["sobe", "meni", "vina", "ponujamo"]),
        Turn("Kako pridem do vas?", any_=["Fram", "A1", "Pohorje"]),
    ]),
    TC("Živali nato jahanje", "CELOTNO", [
        Turn("Katere živali imate?", any_=["Malajka", "Pepa"]),
        Turn("Ali je jahanje možno?", any_=["jahanj", "poni", "Malajka"]),
    ]),
    TC("Terme nato sobe", "CELOTNO", [
        Turn("So v bližini terme?", any_=["Zreče", "terme"]),
        Turn("Kakšne sobe imate?", any_=["ALJAŽ", "JULIJA", "ANA"]),
    ]),
    TC("Gibanica nato meni", "CELOTNO", [
        Turn("Imate gibanico?", any_=["gibanica", "specialitet", "Pohorje"]),
        Turn("Kakšen je vikend meni?", any_=["meni", "36", "vikend"]),
    ]),
    TC("Hallucination chain", "CELOTNO", [
        Turn("Imate bazen?", any_=["ne", "žal", "ni", "pokličite"]),
        Turn("Imate savno?", any_=["ne", "terme", "Zreče", "pokličite"]),
        Turn("Imate fitnese?", any_=["ne", "žal", "ni", "pokličite"]),
    ]),
    TC("Pozdrav info goodbye", "CELOTNO", [
        Turn("Dober dan!", any_=["dan", "pozdravlj", "Kovačnik"]),
        Turn("Kakšne sobe imate?", any_=["ALJAŽ", "JULIJA", "ANA"]),
        Turn("Hvala, nasvidenje!", any_=["nasvidenje", "adijo", "hvala", "prosim", "veseljem"]),
    ]),
    TC("Multi-info brez booking", "CELOTNO", [
        Turn("Koliko stane soba?", must=["50"]),
        Turn("Kakšna vina imate?", must=["Peneča"]),
        Turn("Kdaj imate kosilo?", any_=["sobota", "nedelja", "12"]),
        Turn("Kje ste?", any_=["Planica", "Fram"]),
    ]),
    TC("Info o osebah celotno", "CELOTNO", [
        Turn("Kdo je Danilo?", any_=["gospodar", "Danilo"]),
        Turn("Kdo je Barbara?", any_=["dejavnost", "Barbara"]),
        Turn("Kdo je Angelca?", any_=["babic", "Angelca"]),
    ]),
    TC("Booking miza celotno", "CELOTNO", [
        Turn("Rad bi rezerviral mizo za kosilo ob soboti.", any_=["datum", "sobota", "kdaj"]),
        Turn("12.7.2026", any_=["ura", "uri", "čas", "koliko", "15:00"]),
    ]),
]


async def main() -> int:
    parser = argparse.ArgumentParser(description="Kovačnik AI V3 komprehenzivni test suite")
    parser.add_argument("--category", default="", help="Run only this category")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    brand = get_brand()
    tests = TESTS
    if args.category:
        tests = [t for t in TESTS if t.category.upper() == args.category.upper()]
        if not tests:
            print(f"[ERROR] Kategorija '{args.category}' ni najdena.")
            return 1

    categories: dict[str, list[TC]] = {}
    for tc in tests:
        categories.setdefault(tc.category, []).append(tc)

    total = passed = 0
    failed_list: list[tuple[str, str, str]] = []

    for cat, cat_tests in categories.items():
        print(f"\n{'─'*60}")
        print(f"  {cat} ({len(cat_tests)} testov)")
        print(f"{'─'*60}")
        cat_pass = 0
        for tc in cat_tests:
            ok, detail = await run_tc(tc, brand, verbose=args.verbose)
            total += 1
            if ok:
                passed += 1
                cat_pass += 1
                print(f"  ✓ {tc.name}")
            else:
                print(f"  ✗ {tc.name}")
                print(f"      → {detail}")
                failed_list.append((cat, tc.name, detail))
                if args.fail_fast:
                    print("\n[FAIL-FAST] Ustavitev.")
                    return 1
        print(f"  → {cat_pass}/{len(cat_tests)} passed")

    print(f"\n{'═'*60}")
    print(f"  SKUPAJ: {passed}/{total} passed  ({total - passed} FAIL)")
    print(f"{'═'*60}")

    if failed_list:
        print("\nNeuspešni testi:")
        for cat, name, detail in failed_list:
            print(f"  [{cat}] {name}: {detail}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
