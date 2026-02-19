#!/usr/bin/env python3
"""100 new unique e2e gauntlet tests.

Kategorije:
  TYPO (15) · SLENG2 (10) · TEMA (15) · KIDS (10)
  ANGLESCINA (5) · GRESKE (10) · KOMPLEX (15)
  INFO_EDGE (10) · DEZ2 (5) · FRUSTRAC (5)

Zagon:
    PYTHONPATH=. python scripts/test_gauntlet_100_new.py
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

    # ════════════════════════════════════════
    # TYPO (15) — extreme typos, phonetic, transpositions
    # ════════════════════════════════════════
    TC("T01 typo rezervacija sobe", "TYPO", [
        Turn("rezeravicja sobe prosim",
             any_=["datum", "kdaj", "prihod"]),
    ]),
    TC("T02 typo jahanje cena", "TYPO", [
        Turn("jahnje cena za en krog",
             any_=["5", "€", "jahanj", "krog", "poni"]),
    ]),
    TC("T03 typo kolk stane nocitev", "TYPO", [
        Turn("kolk stnae nocitev",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
    ]),
    TC("T04 typo marmelada", "TYPO", [
        Turn("marmelad kakšne mate pri vas",
             any_=["jagoda", "malina", "marmelad", "5,50", "aronija"]),
    ]),
    TC("T05 typo smucisce razdalja", "TYPO", [
        Turn("smbucisce areh razdalaj",
             any_=["Areh", "km", "minut", "smučišč", "25"]),
    ]),
    TC("T06 typo zivali ogled", "TYPO", [
        Turn("zivali hlev poglet",
             any_=["Malajka", "Marsi", "Svinje", "Kokoši", "poni", "konj", "živali"]),
    ]),
    TC("T07 typo Barbara kontakt", "TYPO", [
        Turn("Barbra za rezervc kontkt",
             any_=["Barbara", "031", "kontakt", "rezervac"]),
    ]),
    TC("T08 typo Danilo kdo", "TYPO", [
        Turn("danillo kdo jee na kmetji",
             any_=["Danilo", "gospodar", "kmetij"]),
    ]),
    TC("T09 typo checkin cas", "TYPO", [
        Turn("checin cajt kdaj mogoce",
             any_=["14", "prihod", "ura", "popoldne", "check"]),
    ]),
    TC("T10 typo liker cena", "TYPO", [
        Turn("liker borovnicv cena",
             any_=["borovničev", "13", "liker", "€"]),
    ]),
    TC("T11 typo bela vina", "TYPO", [
        Turn("kere wina imate bela",
             any_=["bela", "Greif", "Frešer", "vino", "Laški", "Sauvignon"]),
    ]),
    TC("T12 typo miza booking", "TYPO", [
        Turn("mizo bi rezerivral za kosil",
             any_=["datum", "kdaj", "termin"]),
    ]),
    TC("T13 typo slabo vreme brez telefona", "TYPO", [
        Turn("slabo vreme kaj nardiomo",
             any_=["živali", "degustat", "liker", "ogled"],
             not_=["031 330 113"]),
    ]),
    TC("T14 typo jahanje otroci", "TYPO", [
        Turn("poniji jahnje za otrce",
             any_=["poni", "jahanj", "5", "krog", "otroc"]),
    ]),
    TC("T15 typo potica", "TYPO", [
        Turn("potica naoroct se da",
             any_=["potica", "30", "kovacnik", "sladke"]),
    ]),

    # ════════════════════════════════════════
    # SLENG2 (10) — youth slang, dialect, shorthand
    # ════════════════════════════════════════
    TC("SL2_01 kr povejte kaj ste", "SLENG2", [
        Turn("kr mi povejte kj ste",
             any_=["kmetij", "Kovačnik", "Partinjska", "Pohorje", "nastanit", "jahanj"]),
    ]),
    TC("SL2_02 cajt check-in za sobo", "SLENG2", [
        Turn("kej je check-in cajt za sobo",
             any_=["14", "prihod", "ura", "popoldne", "check"]),
    ]),
    TC("SL2_03 kolk kosta prenoc", "SLENG2", [
        Turn("kolk kosta ena prenoc",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
    ]),
    TC("SL2_04 ujamem se pr vas", "SLENG2", [
        Turn("ujamem se pr vas za vikend",
             any_=["datum", "kdaj", "prihod", "termin", "rezerv", "soba"]),
    ]),
    TC("SL2_05 kej popit domac", "SLENG2", [
        Turn("kej se da popit domac",
             any_=["liker", "vino", "borovničev", "bela", "rdeč", "penečih"]),
    ]),
    TC("SL2_06 kej za pojes", "SLENG2", [
        Turn("kej za pojes pri vas",
             any_=["meni", "kosilo", "degust", "€", "hodni"]),
    ]),
    TC("SL2_07 kej se da pocet za otrce", "SLENG2", [
        Turn("kej se da pocet za otrce pri vas aktivnosti",
             any_=["poni", "jahanj", "Julija", "animat", "živali", "meni"]),
    ]),
    TC("SL2_08 da mi kontakt Barbara", "SLENG2", [
        Turn("da mi kontakt za Barbara",
             any_=["031", "Barbara", "kontakt", "pokliče"]),
    ]),
    TC("SL2_09 dogovorit za sobe", "SLENG2", [
        Turn("mamo se dogovorit za sobe",
             any_=["datum", "kdaj", "prihod", "termin", "soba", "rezerv"]),
    ]),
    TC("SL2_10 ce dez kva boste", "SLENG2", [
        Turn("ce dez prdem kva boste",
             any_=["živali", "degustat", "liker", "ogled"]),
    ]),

    # ════════════════════════════════════════
    # TEMA (15) — topic switching mid-flow
    # ════════════════════════════════════════
    TC("TM01 jahanje nato booking soba", "TEMA", [
        Turn("Ali je jahanje mogoce pri vas?",
             any_=["poni", "jahanj", "5", "krog"]),
        Turn("Super. Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("12. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Novak Rok",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM02 booking nato zivali nato nadaljuj", "TEMA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Katere zivali imate?",
             any_=["živali", "poni", "konj", "prašič", "kokoš", "datum", "rezervac"]),
        Turn("Prihod 20. avgusta.",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Petek Maja",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM03 cena vino miza", "TEMA", [
        Turn("Koliko stane nocitev?",
             any_=["50", "EUR", "€", "osebo"]),
        Turn("Imate domaca vina?",
             any_=["bela", "rdeč", "vino", "Greif", "Frešer"]),
        Turn("Mizo bi rezerviral za 15. maja ob 12h za 3 osebe Kolar Jan.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM04 booking nato popust otroci", "TEMA", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("Koliko stane za otroke?",
             any_=["otrok", "popust", "50", "brezplačno", "EUR", "noč", "koliko"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Hrovat Janez",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM05 booking nato zima", "TEMA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("18. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("Pozimi kaj delate tam?",
             any_=["smučišč", "Areh", "Mariborsko", "Pohorje"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Krek Luka",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM06 shop nato booking soba", "TEMA", [
        Turn("Kaj prodajate?",
             any_=["bunka", "marmelad", "liker", "salama", "spletna"]),
        Turn("Rad bi sobo. Prihod 5. septembra 2 noci 2 osebi Oblak Miha.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM07 booking nato dez nato nadaljuj", "TEMA", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("22. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("Ce bo dežuje kaj bomo poceli?",
             any_=["živali", "degustat", "liker", "ogled"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Peterlin Teja",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM08 Danilo nato booking", "TEMA", [
        Turn("Kdo je Danilo?",
             any_=["Danilo", "gospodar", "kmetij"]),
        Turn("Super. Rad bi sobo za 3. septembra 2 noci 2 osebi Mlakar Vid.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM09 meni nato booking miza", "TEMA", [
        Turn("Kaksne meni imate?",
             any_=["meni", "kosilo", "degust", "€", "hodni"]),
        Turn("Ok mizo bi rada za 18. aprila ob 13h za 4 osebe Kramar Sonja.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM10 soba na mizo preusmeritev", "TEMA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Pravzaprav raje mizo za kosilo.",
             any_=["datum", "kdaj", "termin", "miza", "prihod"]),
        Turn("10. maja",
             any_=["ura", "ob", "oseb", "Koliko"]),
        Turn("ob 12h za 4 osebe",
             any_=["ime", "naziv", "koga", "031", "Barbara"]),
        Turn("Bric Andrej",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM11 zivali shop nato booking", "TEMA", [
        Turn("Katere zivali imate?",
             any_=["Malajka", "Marsi", "Svinje", "Kokoši", "poni", "konj"]),
        Turn("Kaj prodajate?",
             any_=["bunka", "marmelad", "liker", "salama"]),
        Turn("Rad bi sobo za 8. novembra 2 noci 2 osebi Sitar Rok.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM12 lokacija nato booking", "TEMA", [
        Turn("Kje ste?",
             any_=["Partinjska", "Pohorje", "Zreče", "naslov"]),
        Turn("Super! Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Potokar Zoran",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM13 checkin checkout nato booking", "TEMA", [
        Turn("Kdaj je check-in?",
             any_=["14", "prihod", "ura", "popoldne"]),
        Turn("In kdaj je check-out?",
             any_=["10", "odhod", "ura", "dopoldne", "izhod", "checkout"]),
        Turn("Rad bi sobo za 20. septembra 2 noci 2 osebi Bele Sara.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM14 Angelca info nato miza", "TEMA", [
        Turn("Kdo je Angelca?",
             any_=["Angelca", "babic", "gospodinj"]),
        Turn("Mizo bi rezerviral za 12. marca ob 12h za 4 osebe Kovacic Rok.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("TM15 napaka pri noceh nato nadaljuj", "TEMA", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("ne razumem",
             any_=["noč", "koliko", "dni", "trajanj", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Strus Ana",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # ════════════════════════════════════════
    # KIDS (10) — otroci v rezervacijskem toku (nova logika)
    # ════════════════════════════════════════
    TC("KID01 stiri skupaj ne otroci", "KIDS", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("4 osebe",
             any_=["otrok", "pripeljete"]),
        Turn("ne",
             any_=["ime", "naziv", "koga", "Ime"]),
        Turn("Turk Matej",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID02 tri skupaj en otrok z vprašanjem", "KIDS", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("22. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("3 osebe",
             any_=["otrok", "pripeljete"]),
        Turn("ja",
             any_=["Koliko", "otrok"]),
        Turn("1 otrok",
             any_=["star", "stari", "otroc", "Koliko"]),
        Turn("8 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Zupan Matija",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID03 stiri skupaj nimam otrok", "KIDS", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("5. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("4 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("4 osebe",
             any_=["otrok", "pripeljete"]),
        Turn("nimam otrok",
             any_=["ime", "naziv", "koga"]),
        Turn("Pesec Franc",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID04 tri skupaj otrok brez starosti", "KIDS", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("20. septembra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("3 osebe",
             any_=["otrok", "pripeljete"]),
        Turn("1 otrok",
             any_=["star", "stari", "otroc", "Koliko"]),
        Turn("7 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Brus Alenka",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID05 dve osebi brez otroskega vprasanja", "KIDS", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("8. novembra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 osebi",
             any_=["ime", "naziv", "koga"]),
        Turn("Majcen Rok",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID06 stiri samo stevilka ne otroci", "KIDS", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("18. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("4",
             any_=["otrok", "pripeljete"]),
        Turn("ne",
             any_=["ime", "naziv", "koga"]),
        Turn("Vovk Simon",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID07 otroci z razclenitvijo starosti", "KIDS", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("20. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasla 2 otroka",
             any_=["star", "stari", "otroc", "Koliko"]),
        Turn("6 in 9 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Saric Petra",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID08 stiri skupaj z dvema otrokoma", "KIDS", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("5. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("4 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("4 osebe",
             any_=["otrok", "pripeljete"]),
        Turn("ja",
             any_=["Koliko", "otrok"]),
        Turn("2 otroka",
             any_=["star", "stari", "otroc", "Koliko"]),
        Turn("5 in 7 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Pregelj Miha",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID09 tri skupaj en otrok z letom", "KIDS", [
        Turn("Sobo bi rezerviral.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. oktobra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("3 osebe",
             any_=["otrok", "pripeljete"]),
        Turn("1 otrok 3 leta",
             any_=["ime", "naziv", "koga"]),
        Turn("Pisk Andrej",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KID10 stiri skupaj dva otroka z leti", "KIDS", [
        Turn("Sobo bi rezerviral.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("3. septembra",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("4 skupaj",
             any_=["otrok", "pripeljete"]),
        Turn("2 otroka 4 in 7 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Tomsic Blaz",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # ════════════════════════════════════════
    # ANGLESCINA (5) — English & mixed-language
    # ════════════════════════════════════════
    TC("ANG01 hello horses ponies", "ANGLESCINA", [
        Turn("hello do you have horses or ponies?",
             any_=["poni", "jahanj", "Malajka", "Marsi", "5", "krog"]),
    ]),
    TC("ANG02 price overnight", "ANGLESCINA", [
        Turn("what is the price for overnight stay?",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
    ]),
    TC("ANG03 book table", "ANGLESCINA", [
        Turn("I'd like to book a table for lunch",
             any_=["datum", "kdaj", "termin", "miza"]),
    ]),
    TC("ANG04 bring children", "ANGLESCINA", [
        Turn("can we bring children with us?",
             any_=["otrok", "poni", "jahanj", "animat", "Julija", "popust", "brezplač"]),
    ]),
    TC("ANG05 mesani jeziki booking", "ANGLESCINA", [
        Turn("hej, I would like to book a soba for 2 noci in september",
             any_=["datum", "kdaj", "prihod", "termin", "september"]),
    ]),

    # ════════════════════════════════════════
    # GRESKE (10) — user errors, corrections, edge inputs
    # ════════════════════════════════════════
    TC("GR01 prevelika skupina 13", "GRESKE", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("13 oseb",
             any_=["12", "email", "kontakt", "tri", "sobe"]),
    ]),
    TC("GR02 preklic med booking", "GRESKE", [
        Turn("Zelim sobo prosim.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("10. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("Nehajmo. Hvala.",
             any_=["hvala", "Prosim", "veseljem", "pomoč", "preklic"]),
    ]),
    TC("GR03 napacen vnos pri datumu", "GRESKE", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("xxxxxxx",
             any_=["datum", "kdaj", "prihod", "kateri", "termin", "pomagam", "natančneje", "Oprostite", "razumela", "prosim"]),
        Turn("22. julija",
             any_=["noč", "koliko", "odhod"]),
    ]),
    TC("GR04 nula noci", "GRESKE", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("18. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("0 noci",
             any_=["noč", "koliko", "minimum", "vsaj", "dni", "trajanj", "2"]),
    ]),
    TC("GR05 stevilka namesto datuma", "GRESKE", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("42",
             any_=["datum", "kdaj", "prihod", "kateri", "pomagam", "natančno", "prosim", "bolj"]),
        Turn("15. oktobra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 osebi",
             any_=["ime", "naziv", "koga"]),
        Turn("Horvat Rok",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("GR06 gibberish pri osebah", "GRESKE", [
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("22. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("asdfgh",
             any_=["oseb", "Koliko", "odrasl", "gost", "npr", "pomagam", "veseljem", "pojasnite", "prosim"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Korosec Miha",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("GR07 booking po dveh info vprasanjih", "GRESKE", [
        Turn("Koliko stane jahanje?",
             any_=["5", "€", "krog", "poni"]),
        Turn("In koliko stane soba?",
             any_=["50", "EUR", "€", "osebo"]),
        Turn("Rad bi sobo za 22. julija 3 noci 2 osebi Kern Rok.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("GR08 dolg nesmisel nato booking", "GRESKE", [
        Turn("Bla bla ne vem kaj bi rekel sploh nekako...",
             any_=["pomagam", "ponudbi", "031", "Barbara", "veseljem", "pomoč", "Morda", "poveste", "pomagal"]),
        Turn("Ok rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 osebi",
             any_=["ime", "naziv", "koga"]),
        Turn("Rozman Irena",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("GR09 info nato zbogom hvala", "GRESKE", [
        Turn("Koliko stane jahanje?",
             any_=["5", "€", "krog", "poni"]),
        Turn("Hvala, to je vse.",
             any_=["hvala", "veseljem", "pomoč", "Prosim"]),
    ]),
    TC("GR10 miza brez ure", "GRESKE", [
        Turn("Mizo za 15. marca za 4 osebe ime Koren Ivo.",
             any_=["ura", "ob", "031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # ════════════════════════════════════════
    # KOMPLEX (15) — od pozdrava do odzdrava
    # ════════════════════════════════════════
    TC("KO01 zdravo jahanje cena booking", "KOMPLEX", [
        Turn("Zdravo!",
             any_=["Zdravo", "Pozdravljeni", "kmetij", "Kovačnik", "pomagam", "pomoč"]),
        Turn("Imate jahanje?",
             any_=["poni", "jahanj", "5", "krog"]),
        Turn("Koliko stane nocitev?",
             any_=["50", "EUR", "€", "osebo"]),
        Turn("Ok rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("5. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("4 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Levstek Rok",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO02 zivali jahanje vino miza", "KOMPLEX", [
        Turn("Katere živali imate?",
             any_=["Malajka", "Marsi", "Svinje", "Kokoši", "poni", "konj"]),
        Turn("Super! In cena jahanja?",
             any_=["5", "€", "krog", "poni"]),
        Turn("In domaca vina imate?",
             any_=["bela", "rdeč", "vino", "Greif", "Frešer"]),
        Turn("Super. Mizo bi rezerviral za 20. maja ob 12h za 4 osebe Zupanc Franci.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO03 dez zima nato booking", "KOMPLEX", [
        Turn("Ce dežuje kaj bomo poceli?",
             any_=["živali", "degustat", "liker", "ogled"]),
        Turn("Pozimi kaj imate?",
             any_=["smučišč", "Areh", "Mariborsko", "Pohorje"]),
        Turn("Rad bi sobo za 15. avgusta 3 noci 2 osebi Zagar Natasa.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO04 cena otroci popust booking", "KOMPLEX", [
        Turn("Koliko stane nocitev?",
             any_=["50", "EUR", "€", "osebo"]),
        Turn("In za otroke?",
             any_=["otrok", "popust", "brezplačno", "50"]),
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("20. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasla 2 otroka",
             any_=["star", "stari", "otroc", "Koliko"]),
        Turn("5 in 8 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Primozic Eva",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO05 Danilo Barbara nato booking", "KOMPLEX", [
        Turn("Kdo je Danilo Štern?",
             any_=["Danilo", "gospodar", "kmetij"]),
        Turn("In Barbara?",
             any_=["Barbara", "031", "kontakt", "rezervac"]),
        Turn("Rad bi sobo za 18. julija 3 noci 2 odrasli Bende Vid.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO06 shop vino miza komplet", "KOMPLEX", [
        Turn("Kaj prodajate v vaši trgovini?",
             any_=["bunka", "marmelad", "liker", "salama"]),
        Turn("Katera vina priporocate?",
             any_=["bela", "rdeč", "vino", "Greif", "Frešer"]),
        Turn("Mizo za 8. marca ob 13h za 3 osebe Crnic Ivo.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO07 lokacija avto nato booking", "KOMPLEX", [
        Turn("Kje se nahajate?",
             any_=["Partinjska", "Pohorje", "Zreče", "naslov"]),
        Turn("Koliko je km od Maribora?",
             any_=["km", "minut", "Maribor", "vožnja"]),
        Turn("Rad bi sobo za 3. septembra 2 noci 2 osebi Kerin Andrej.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO08 jahanje animator miza", "KOMPLEX", [
        Turn("Imate jahanje za otroke?",
             any_=["poni", "jahanj", "5", "krog", "otroc"]),
        Turn("In animatorka za otroke?",
             any_=["Julija", "animat", "živali"]),
        Turn("Super. Mizo bi rezerviral za 21. marca ob 12:30 za 5 oseb Kovac Tin.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO09 multi info nato booking soba", "KOMPLEX", [
        Turn("Zanima me cena sobe, jahanje in vaši likerji.",
             any_=["50", "jahanj", "liker", "5", "EUR"]),
        Turn("Hvala. Sobo bi rad rezerviral.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. oktobra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 osebi",
             any_=["ime", "naziv", "koga"]),
        Turn("Sitar Blazka",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO10 angleski pozdrav slov booking", "KOMPLEX", [
        Turn("Hello, good morning!",
             any_=["Zdravo", "Pozdravljeni", "kmetij", "pomagam", "pomoč", "Kovačnik", "Kovacnik"]),
        Turn("Ali imate sobe?",
             any_=["soba", "nastanit", "50", "datum", "rezerv"]),
        Turn("Rad bi sobo za 22. julija 3 noci 2 osebi Kern Eva.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO11 checkin checkout booking", "KOMPLEX", [
        Turn("Kdaj je check-in?",
             any_=["14", "prihod", "ura", "popoldne"]),
        Turn("In check-out?",
             any_=["10", "odhod", "ura", "dopoldne", "izhod", "checkout"]),
        Turn("Rad bi sobo za 5. avgusta 4 noci 2 osebi Juhart Rok.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO12 jeza nato booking", "KOMPLEX", [
        Turn("Grozno! Vaš chatbot sploh ne dela!",
             any_=["pomagam", "031", "Barbara", "veseljem", "Prosim"]),
        Turn("Ok rad bi sobo za 20. septembra 2 noci 2 osebi Lokar Rok.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO13 potica liker marmelada miza", "KOMPLEX", [
        Turn("Ali imate potico?",
             any_=["potica", "30", "sladke", "kovacnik"]),
        Turn("In likerje?",
             any_=["borovničev", "liker", "13", "€", "žajbljev"]),
        Turn("In marmelado?",
             any_=["jagoda", "malina", "marmelad", "5,50"]),
        Turn("Mizo za 10. maja ob 12h za 2 osebi Plevnik Gal.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO14 babica Kaja booking", "KOMPLEX", [
        Turn("Kdo je babica na kmetiji?",
             any_=["Angelca", "babic", "gospodinj"]),
        Turn("In Kaja kdo je?",
             any_=["Kaja", "partner", "razvedri"]),
        Turn("Rad bi sobo za 18. julija 3 noci 2 osebi Mohar Tine.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("KO15 polna pot otroci booking", "KOMPLEX", [
        Turn("Dober dan!",
             any_=["Zdravo", "Pozdravljeni", "kmetij", "Kovačnik", "pomagam", "dober", "pomoč"]),
        Turn("Imate možnost jahanja za otroke?",
             any_=["poni", "jahanj", "5", "krog", "otroc"]),
        Turn("Priporocate vino k obedu?",
             any_=["bela", "rdeč", "vino", "Greif", "Frešer"]),
        Turn("Rad bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("5. julija",
             any_=["noč", "koliko", "odhod"]),
        Turn("4 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("4 skupaj",
             any_=["otrok", "pripeljete"]),
        Turn("2 otroka 6 in 9 let",
             any_=["ime", "naziv", "koga"]),
        Turn("Brvar Lea",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # ════════════════════════════════════════
    # INFO_EDGE (10) — edge cases informacij
    # ════════════════════════════════════════
    TC("IE01 bazen hallucin", "INFO_EDGE", [
        Turn("Ali imate bazen?",
             any_=["ni", "ne", "nima", "žal", "nimamo"],
             not_=["da, imamo bazen"]),
    ]),
    TC("IE02 jacuzzi hallucin", "INFO_EDGE", [
        Turn("imate jacuzzi?",
             any_=["ni", "ne", "nima", "žal", "nimamo"]),
    ]),
    TC("IE03 koliko sob imate", "INFO_EDGE", [
        Turn("koliko sob imate",
             any_=["soba", "tri", "sob", "031", "nastanit", "dve"]),
    ]),
    TC("IE04 kdaj ste odprti", "INFO_EDGE", [
        Turn("kdaj ste odprti",
             any_=["ponedeljek", "torek", "zaprto", "sreda", "delovnik", "031"]),
    ]),
    TC("IE05 terasa zunaj kosilo", "INFO_EDGE", [
        Turn("al se da jest zunaj na terasi",
             any_=["031", "Barbara", "kontakt", "pokliče", "terasa", "zunaj", "ni", "ne"]),
    ]),
    TC("IE06 kosilo ob kateri uri", "INFO_EDGE", [
        Turn("kdaj je kosilo ob kateri uri",
             any_=["12", "ob", "ura", "kosilo", "meni", "13"]),
    ]),
    TC("IE07 wifi v sobah", "INFO_EDGE", [
        Turn("imate WiFi v sobah",
             any_=["wifi", "internet", "031", "Barbara", "brezžič", "kontakt"]),
    ]),
    TC("IE08 kako dalec od Celja", "INFO_EDGE", [
        Turn("kako dalec od Celja",
             any_=["km", "minut", "vožnja", "031", "Pohorje", "Zreče"]),
    ]),
    TC("IE09 telovadnica hallucin", "INFO_EDGE", [
        Turn("imate telovadnico",
             any_=["ni", "ne", "nima", "žal", "nimamo"]),
    ]),
    TC("IE10 priti z vlakom", "INFO_EDGE", [
        Turn("ali se da priti z vlakom",
             any_=["031", "Barbara", "prevoz", "pokliče", "kontakt", "avtobus", "km"]),
    ]),

    # ════════════════════════════════════════
    # DEZ2 (5) — vreme, dez, zima — dodatni scenariji
    # ════════════════════════════════════════
    TC("DZ2_01 dez kaj doma brez telefona", "DEZ2", [
        Turn("dezuje kaj pocnemo doma",
             any_=["živali", "degustat", "liker", "ogled"],
             not_=["031 330 113"]),
    ]),
    TC("DZ2_02 zima smucisce direktno", "DEZ2", [
        Turn("zima smucisce",
             any_=["smučišč", "Areh", "Mariborsko", "Pohorje"]),
    ]),
    TC("DZ2_03 klima aircondition", "DEZ2", [
        Turn("klima aircondition v sobah",
             any_=["klima", "klimat", "udobn", "Da"]),
    ]),
    TC("DZ2_04 sneg aktivnosti", "DEZ2", [
        Turn("kaj ce pada sneg kaj pocnemo",
             any_=["smučišč", "Areh", "Mariborsko", "Pohorje", "sneg", "zasnež", "živali"]),
    ]),
    TC("DZ2_05 odprti pozimi", "DEZ2", [
        Turn("ali ste odprti pozimi",
             any_=["smučišč", "Areh", "Pohorje", "kmetij", "nastanit", "soba", "odprto", "031"]),
    ]),

    # ════════════════════════════════════════
    # FRUSTRAC (5) — frustracija in negativni toni
    # ════════════════════════════════════════
    TC("FR01 chatbot grozno", "FRUSTRAC", [
        Turn("vaš chatbot je grozno in sploh ne dela!",
             any_=["pomagam", "031", "Barbara", "Prosim", "veseljem"]),
    ]),
    TC("FR02 ne razumete me", "FRUSTRAC", [
        Turn("ne razumete me!",
             any_=["pomagam", "031", "Barbara", "Prosim", "veseljem", "pomoč"]),
    ]),
    TC("FR03 to ni odgovor", "FRUSTRAC", [
        Turn("to ni odgovor na moje vprašanje",
             any_=["pomagam", "031", "Barbara", "Prosim", "veseljem", "ponudbi"]),
    ]),
    TC("FR04 bot ne razume slovenscine", "FRUSTRAC", [
        Turn("vaš bot ne razume slovenščine!",
             any_=["pomagam", "031", "Barbara", "Prosim", "veseljem"]),
    ]),
    TC("FR05 hvala za informacije", "FRUSTRAC", [
        Turn("Hvala za informacije!",
             any_=["hvala", "veseljem", "pomoč", "Prosim", "kmetij", "031"]),
    ]),
]

assert len(TESTS) == 100, f"Expected 100 TCs, got {len(TESTS)}"


async def main() -> int:
    brand = get_brand()
    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    print()
    print("════════════════════════════════════════════════════════════════════")
    print("  GAUNTLET 100 NEW — typos · sleng · otroci · kompleksni scenariji")
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
    sys.exit(asyncio.run(main()))
