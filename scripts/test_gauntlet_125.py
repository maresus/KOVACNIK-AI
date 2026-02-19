#!/usr/bin/env python3
"""125 gauntlet: typos · sleng · multi-turn · rezervacije (125 sekvenc).

Kategorije:
  JAHANJE (10) · OSEBE (10) · SHOP (15) · VINA (6) · ZIVALI (5)
  LOKACIJA (5) · SLENG (8) · KRATKO (8) · KLIMA_DEZ_ZIMA (8)
  REZ_SOBA (25) · REZ_MIZA (15) · EDGE (10)

Zagon:
    PYTHONPATH=. python scripts/test_gauntlet_125.py
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
    # JAHANJE (10)
    # ════════════════════════════════════════
    TC("J01 direktno", "JAHANJE", [
        Turn("jahanje?", any_=["jahanj", "poni", "5", "krog", "mogoče"]),
    ]),
    TC("J02 slang kolk stane", "JAHANJE", [
        Turn("kolk stane en krog na poniju", any_=["5", "€", "krog", "jahanj"]),
    ]),
    TC("J03 brez diakritik", "JAHANJE", [
        Turn("ali je jahanje mogoce", any_=["jahanj", "poni", "5", "krog"]),
    ]),
    TC("J04 CAPS", "JAHANJE", [
        Turn("JAHANJE ALI JE MOZNO", any_=["jahanj", "poni", "5", "krog"]),
    ]),
    TC("J05 otroci slang", "JAHANJE", [
        Turn("mam 5letnega otroka al lahk jaha", any_=["jahanj", "poni", "otroc", "5"]),
    ]),
    TC("J06 brezplacno", "JAHANJE", [
        Turn("je brezplacno jahanje", any_=["5", "€", "krog", "poni"]),
    ]),
    TC("J07 poni kratica", "JAHANJE", [
        Turn("cena za poni", any_=["5", "€", "jahanj", "krog"]),
    ]),
    TC("J08 Malajka Marsi", "JAHANJE", [
        Turn("kdo sta Malajka in Marsi", any_=["poni", "jahanj", "Malajka", "Marsi", "5"]),
    ]),
    TC("J09 sekvenca poni info", "JAHANJE", [
        Turn("Imate ponuje za jahanje?", any_=["poni", "jahanj", "Malajka", "5", "krog"]),
        Turn("Koliko stane en krog?", any_=["5", "€", "krog"]),
    ]),
    TC("J10 rezervacija jahanja slang", "JAHANJE", [
        Turn("bi rad jahanje rezerviral za jutri",
             any_=["jahanj", "poni", "5", "prihod", "krog", "031"],
             not_=["vnaprej rezervir"]),
    ]),

    # ════════════════════════════════════════
    # OSEBE (10)
    # ════════════════════════════════════════
    TC("O01 kdo vodi", "OSEBE", [
        Turn("kdo vodi kmetijo", any_=["Danilo", "Barbara", "Štern", "druž", "gospod"]),
    ]),
    TC("O02 Danilo direktno", "OSEBE", [
        Turn("kdo je Danilo", any_=["Danilo", "gospodar", "kmetij"]),
    ]),
    TC("O03 Danilo tel slang", "OSEBE", [
        Turn("Danilova tel stevilka", any_=["031", "Barbara", "kontakt", "pokliče"]),
    ]),
    TC("O04 partnerica Aljaza", "OSEBE", [
        Turn("kdo je partnerica Aljaza", any_=["Kaja", "partner", "razvedri"]),
    ]),
    TC("O05 Julija direktno", "OSEBE", [
        Turn("kdo je Julija", any_=["Julija", "hči", "animat", "živali"]),
    ]),
    TC("O06 animatorka typo", "OSEBE", [
        Turn("al je Julija animatorica na kmetiji", any_=["Julija", "animat", "živali"]),
    ]),
    TC("O07 babica", "OSEBE", [
        Turn("kdo je babica na kmetiji", any_=["Angelca", "babic", "gospodinj"]),
    ]),
    TC("O08 Barbara kontakt", "OSEBE", [
        Turn("Barbara za rezervacije kontakt", any_=["Barbara", "031", "kontakt", "rezervac"]),
    ]),
    TC("O09 Kaja kdo", "OSEBE", [
        Turn("Kaja - kdo je to", any_=["Kaja", "partner", "Aljaž", "razvedri"]),
    ]),
    TC("O10 druzina nato kontakt", "OSEBE", [
        Turn("kdo je v druzini Stern", any_=["Danilo", "Barbara", "Aljaž", "Julija", "Angelca"]),
        Turn("Danila kontakt prosim", any_=["031", "Barbara", "kontakt", "pokliče"]),
    ]),

    # ════════════════════════════════════════
    # SHOP (15)
    # ════════════════════════════════════════
    TC("S01 marmelada kratko", "SHOP", [
        Turn("marmelada?", any_=["marmelad", "jagoda", "malina", "5,50", "od 5"]),
    ]),
    TC("S02 marmelad slang cena", "SHOP", [
        Turn("marmelad kolko stane", any_=["5,50", "od 5", "marmelad", "€"]),
    ]),
    TC("S03 kate marmelade", "SHOP", [
        Turn("kate marmelade imate", any_=["jagoda", "malina", "aronija", "5,50"]),
    ]),
    TC("S04 liker direktno", "SHOP", [
        Turn("likerji - kaj imate", any_=["borovničev", "žajbljev", "tepkovec", "13"]),
    ]),
    TC("S05 liker brez diakritik", "SHOP", [
        Turn("borovnicev liker cena", any_=["13", "borovničev", "liker", "€"]),
    ]),
    TC("S06 trgvina typo", "SHOP", [
        Turn("kaj mate v trgvini", any_=["bunka", "salama", "marmelad", "liker", "spletna"]),
    ]),
    TC("S07 bunka slang", "SHOP", [
        Turn("bunk za domov", any_=["bunka", "18", "21", "mesni", "€"]),
    ]),
    TC("S08 bunka cena slang", "SHOP", [
        Turn("pohorska bunk kolko kosta", any_=["18", "21", "bunka", "€"]),
    ]),
    TC("S09 salama cena", "SHOP", [
        Turn("suha salama kolko stane", any_=["16", "salama", "€"]),
    ]),
    TC("S10 sirupi kate", "SHOP", [
        Turn("sirupi kate imate", any_=["bezgov", "metin", "6,50", "sirup"]),
    ]),
    TC("S11 namaz domac", "SHOP", [
        Turn("namaz domac imate", any_=["bučni", "namaz", "7", "čemažev"]),
    ]),
    TC("S12 kajin paket typo", "SHOP", [
        Turn("kaj je v kajnem paketu", any_=["sirup", "čaj", "marmelada", "17", "Kajin"]),
    ]),
    TC("S13 darilni paket za mamo", "SHOP", [
        Turn("darilni paket za mamo iscem", any_=["paket", "darilni", "Angelce", "Kajin", "17"]),
    ]),
    TC("S14 potica narociti", "SHOP", [
        Turn("potico bi narocila", any_=["potica", "30", "sladke", "kovacnik"]),
    ]),
    TC("S15 shop sekvenca", "SHOP", [
        Turn("kaj prodajate", any_=["bunka", "salama", "marmelad", "liker"]),
        Turn("koliko stane Kajin paket", any_=["17", "17,50", "Kajin", "€"]),
    ]),

    # ════════════════════════════════════════
    # VINA (6)
    # ════════════════════════════════════════
    TC("V01 vino kratko", "VINA", [
        Turn("vino?", any_=["bela", "rdeč", "penečih", "Greif", "Frešer", "vino"]),
    ]),
    TC("V02 rdece brez diakritik", "VINA", [
        Turn("rdece vino", any_=["rdeč", "rdečih", "Greif", "vino"]),
    ]),
    TC("V03 penece", "VINA", [
        Turn("penece vino imate", any_=["peneč", "Doppler", "Opok", "Leber"]),
    ]),
    TC("V04 muskat", "VINA", [
        Turn("muskat vino imate", any_=["Muškat", "muskat", "polsladko", "Greif", "Skuber"]),
    ]),
    TC("V05 likerji ne vino", "VINA", [
        Turn("kere likerje mate", any_=["borovničev", "žajbljev", "tepkovec", "liker", "13"]),
    ]),
    TC("V06 vino nato nakup", "VINA", [
        Turn("bela vina", any_=["Greif", "Frešer", "bela", "Laški", "Sauvignon"]),
        Turn("ali prodajate steklenice za domov",
             any_=["spletna", "kovacnik.com", "nakup", "031", "dogovor"]),
    ]),

    # ════════════════════════════════════════
    # ŽIVALI (5)
    # ════════════════════════════════════════
    TC("Z01 zivali brez diakritik", "ZIVALI", [
        Turn("zivali na kmetiji", any_=["živali", "konj", "poni", "prašič", "ovca", "kokoš"]),
    ]),
    TC("Z02 kere zivali slang", "ZIVALI", [
        Turn("kere zivali imate", any_=["živali", "poni", "konj", "Malajka", "Marsi"]),
    ]),
    TC("Z03 Carli typo", "ZIVALI", [
        Turn("Carli kdo je to", any_=["Čarli", "konj", "poni", "živali"]),
    ]),
    TC("Z04 kokosi", "ZIVALI", [
        Turn("imate koke ali kokosi", any_=["kokoš", "živali", "koke", "kmetij"]),
    ]),
    TC("Z05 krave", "ZIVALI", [
        Turn("krave imate", any_=["živali", "ni", "ne", "konj", "poni", "kmetij"]),
    ]),

    # ════════════════════════════════════════
    # LOKACIJA (5)
    # ════════════════════════════════════════
    TC("L01 kje ste", "LOKACIJA", [
        Turn("kje ste", any_=["Partinjska", "Pohorje", "Zreče", "naslov", "Loče"]),
    ]),
    TC("L02 naslov", "LOKACIJA", [
        Turn("naslov kmetije", any_=["Partinjska", "Zreče", "naslov", "Pohorje"]),
    ]),
    TC("L03 kolk dalec Maribor", "LOKACIJA", [
        Turn("kolk dalec od Maribora", any_=["km", "minut", "Maribor", "vožnja"]),
    ]),
    TC("L04 GPS", "LOKACIJA", [
        Turn("GPS koordinate prosim", any_=["Google", "Maps", "Partinjska", "naslov", "koordinat"]),
    ]),
    TC("L05 avtobus", "LOKACIJA", [
        Turn("kako pridem z avtobusom", any_=["031", "pokliče", "prevoz", "avtobus", "Barbara"]),
    ]),

    # ════════════════════════════════════════
    # SLENG (8)
    # ════════════════════════════════════════
    TC("SL01 cajt za jed", "SLENG", [
        Turn("cajt za jed kdaj delate", any_=["12", "15", "kosilo", "ura", "delovn", "čas"]),
    ]),
    TC("SL02 nocitev kolk kosta", "SLENG", [
        Turn("nocitev kolk kosta", any_=["50", "EUR", "€", "osebo", "nastanit"]),
    ]),
    TC("SL03 un poni cajt", "SLENG", [
        Turn("un poniji cajt kdaj lahk jahajo", any_=["jahanj", "poni", "5", "krog", "prihod"]),
    ]),
    TC("SL04 majo likerje", "SLENG", [
        Turn("majo v ponudbi likerje", any_=["borovničev", "liker", "13", "€"]),
    ]),
    TC("SL05 soba kolk kosta", "SLENG", [
        Turn("soba kolk kosta nocitev", any_=["50", "EUR", "€", "nastanit", "osebo"]),
    ]),
    TC("SL06 otroci kej grejo", "SLENG", [
        Turn("mam otroke kej grejo", any_=["poni", "jahanj", "Julija", "animat", "živali"]),
    ]),
    TC("SL07 stela bi sobo", "SLENG", [
        Turn("stela bi sobo za vikend", any_=["datum", "kdaj", "prihod", "termin"]),
        Turn("prihod 14. junija", any_=["noč", "koliko", "odhod", "trajanj"]),
    ]),
    TC("SL08 nocitiva za 2", "SLENG", [
        Turn("nocitiva za 2 osebe", any_=["datum", "kdaj", "prihod", "termin"]),
        Turn("22. julija", any_=["noč", "oseb", "koliko", "odhod"]),
    ]),

    # ════════════════════════════════════════
    # KRATKO (8)
    # ════════════════════════════════════════
    TC("K01 cena", "KRATKO", [
        Turn("cena?", any_=["50", "EUR", "€", "cena", "nastanit", "soba"]),
    ]),
    TC("K02 soba", "KRATKO", [
        Turn("soba?", any_=["soba", "nastanit", "50", "rezerv", "datum"]),
    ]),
    TC("K03 meni", "KRATKO", [
        Turn("meni?", any_=["kosilo", "meni", "€", "hodni", "degust"]),
    ]),
    TC("K04 kontakt", "KRATKO", [
        Turn("kontakt?", any_=["031", "Barbara", "031 330 113", "kontakt"]),
    ]),
    TC("K05 rezervacija", "KRATKO", [
        Turn("rezervacija?", any_=["rezerv", "datum", "kdaj", "soba", "miza"]),
    ]),
    TC("K06 vino kratko", "KRATKO", [
        Turn("vino?", any_=["bela", "rdeč", "penečih", "vino", "Greif", "Frešer"]),
    ]),
    TC("K07 jahanje kratko", "KRATKO", [
        Turn("jahanje?", any_=["jahanj", "poni", "5", "krog", "mogoče"]),
    ]),
    TC("K08 kosilo kratko", "KRATKO", [
        Turn("kosilo?", any_=["kosilo", "meni", "€", "12", "ob"]),
    ]),

    # ════════════════════════════════════════
    # KLIMA / DEŽ / ZIMA (8)
    # ════════════════════════════════════════
    TC("KDZ01 klima kratko", "KLIMA_DEZ_ZIMA", [
        Turn("klima?", any_=["klima", "klimat", "Da", "sobe"]),
    ]),
    TC("KDZ02 klimatizacija sobe", "KLIMA_DEZ_ZIMA", [
        Turn("klimatizacija v sobah", any_=["klima", "klimat", "Da", "udobn"]),
    ]),
    TC("KDZ03 dez kaj narest", "KLIMA_DEZ_ZIMA", [
        Turn("dez kaj narest", any_=["živali", "degustat", "liker", "pokličite", "ogled"]),
    ]),
    TC("KDZ04 slabo vreme", "KLIMA_DEZ_ZIMA", [
        Turn("slabo vreme kaj naredimo", any_=["živali", "degustat", "ogled", "pokličite"]),
    ]),
    TC("KDZ05 pozimi kratko", "KLIMA_DEZ_ZIMA", [
        Turn("pozimi kaj", any_=["smučišč", "Areh", "Mariborsko", "Pohorje", "minut"]),
    ]),
    TC("KDZ06 Areh smucisce", "KLIMA_DEZ_ZIMA", [
        Turn("smucisce areh kako dalec", any_=["Areh", "minut", "25", "35", "smučišč"]),
    ]),
    TC("KDZ07 zima aktivnosti", "KLIMA_DEZ_ZIMA", [
        Turn("zima aktivnosti pri vas", any_=["smučišč", "Areh", "Pohorje", "Mariborsko"]),
    ]),
    TC("KDZ08 dezuje cel dan", "KLIMA_DEZ_ZIMA", [
        Turn("kaj ce dezuje cel dan", any_=["živali", "degustat", "liker", "pokličite"]),
    ]),

    # ════════════════════════════════════════════
    # REZERVACIJE SOBA (25)
    # ════════════════════════════════════════════

    # RS01: Klasičen 5-turn happy path
    TC("RS01 klasicen happy path", "REZ_SOBA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod", "Kdaj"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod", "trajanj", "dni"]),
        Turn("3 noci",
             any_=["oseb", "Koliko", "odrasl", "gost"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "Ime", "koga", "priimek"]),
        Turn("Marko Novak",
             any_=["031", "Barbara", "rezervac", "pokliče", "potrdi"]),
    ]),

    # RS02: Typos v vsakem sporočilu
    TC("RS02 typos v vsakem", "REZ_SOBA", [
        Turn("zelim rezervirati sobo proosim",
             any_=["datum", "kdaj", "prihod"]),
        Turn("20ga septembra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasla in 1 otrok",
             any_=["ime", "naziv", "Ime", "koga"]),
        Turn("Novak Petra",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS03: Vse v enem sporočilu
    TC("RS03 vse v enem sporocilu", "REZ_SOBA", [
        Turn("Rad bi rezerviral sobo od 1. do 3. septembra za 2 osebi, ime Kovač Jure.",
             any_=["031", "Barbara", "rezervac", "pokliče", "potrdi", "hvala"]),
    ]),

    # RS04: Tematska prekinitev — jahanje med booking
    TC("RS04 prekinitev jahanje", "REZ_SOBA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Ali je jahanje mogoče?",
             any_=["poni", "jahanj", "5", "krog", "rezervac", "Nadaljuj"]),
        Turn("Ok, prihod 10. julija.",
             any_=["noč", "koliko", "odhod", "prihod"]),
    ]),

    # RS05: Z otroki
    TC("RS05 z otroki", "REZ_SOBA", [
        Turn("Soba za 2 odrasli in 2 otroka.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Prihod 5. julija.",
             any_=["noč", "koliko", "odhod"]),
        Turn("4 noci.",
             any_=["oseb", "Koliko", "odrasl", "ime"]),
        Turn("2 odrasli in 2 otroka 6 in 9 let",
             any_=["ime", "naziv", "otrok", "popust", "koga"]),
        Turn("Horvat Maja",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS06: Cena poizvedba potem rezervacija
    TC("RS06 cena nato rezerv", "REZ_SOBA", [
        Turn("Koliko stane soba na noc?",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
        Turn("Ok rad bi rezerviral. Prihod 20. julija 2 noci 2 osebi ime Kranjc Bojan.",
             any_=["031", "Barbara", "rezervac", "pokliče", "potrdi"]),
    ]),

    # RS07: Zelo kratka sporočila
    TC("RS07 kratka sporocila", "REZ_SOBA", [
        Turn("zelim rezervirati sobo",
             any_=["datum", "kdaj", "prihod"]),
        Turn("september 25",
             any_=["noč", "koliko", "odhod"]),
        Turn("2n",
             any_=["oseb", "Koliko", "odrasl", "ime"]),
        Turn("2 os",
             any_=["ime", "naziv", "koga", "Ime"]),
        Turn("Janez K",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS08: Preklic po koraku 2
    TC("RS08 preklic", "REZ_SOBA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Prihod 12. avgusta.",
             any_=["noč", "koliko", "odhod"]),
        Turn("Preklicem, hvala.",
             any_=["hvala", "Prosim", "veseljem", "pomoč", "bomo", "preklic"]),
    ]),

    # RS09: Za 4 osebe
    TC("RS09 stiri osebe", "REZ_SOBA", [
        Turn("Rezervacija sobe za 4 osebe.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("15. avgusta",
             any_=["noč", "koliko", "odhod"]),
        Turn("5 noci",
             any_=["oseb", "Koliko", "odrasl", "ime"]),
        Turn("4 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Zupancic Ana",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS10: Dolgo bivanje 7 noči
    TC("RS10 dolgo bivanje", "REZ_SOBA", [
        Turn("Bi radi ostali teden dni.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("od 1.8. do 8.8.",
             any_=["noč", "koliko", "oseb", "odrasl", "ime"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Krek Matjaz",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS11: Vikend — minimalno bivanje
    TC("RS11 vikend min noci", "REZ_SOBA", [
        Turn("Rad bi prisel za en vikend.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Prihod v soboto 5. septembra.",
             any_=["noč", "koliko", "odhod", "minimalno", "2"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Pecnik Tomaz",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS12: Datum od-do oblika
    TC("RS12 specificna soba Aljaz", "REZ_SOBA", [
        Turn("Rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod", "soba"]),
        Turn("Od 20.8. do 23.8.",
             any_=["noč", "oseb", "odrasl", "Koliko"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Novak Petra",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS13: Zajtrk vprašanje potem rezervacija
    TC("RS13 zajtrk potem rezerv", "REZ_SOBA", [
        Turn("Ali je zajtrk vkljucen v ceno sobe?",
             any_=["zajtk", "vključen", "50", "cena", "EUR"]),
        Turn("Super rad bi rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("3. septembra 2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Krajnc Luka",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS14: Hišni ljubljenček
    TC("RS14 hisni ljubljencek", "REZ_SOBA", [
        Turn("Ali sprejmete pse - imam psa.",
             any_=["031", "Barbara", "pokliče", "dogovor", "kontakt", "ne", "žival"]),
        Turn("Kljub temu bi rad rezerviral sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("18. julija 3 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Bernik Rok",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS15: Posebna prehrana
    TC("RS15 posebna prehrana", "REZ_SOBA", [
        Turn("Imam alergijo na gluten, ali imate brezglutensko hrano?",
             any_=["031", "pokliče", "dogovor", "Barbara", "kontakt", "posebn", "prehran"]),
        Turn("Hvala. Rad bi rezerviral sobo za 15. avgusta 3 noci 2 osebi Cemazar Vid.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS16: Neformalni jezik
    TC("RS16 neformalen jezik", "REZ_SOBA", [
        Turn("hej bi rad uzal eno sobo za vikend",
             any_=["datum", "kdaj", "prihod"]),
        Turn("8. novembra",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasla 1 otrok",
             any_=["ime", "naziv", "koga"]),
        Turn("Golob Tim",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS17: Relativni datum
    TC("RS17 relativni datum", "REZ_SOBA", [
        Turn("Rad bi prisel naslednji vikend.",
             any_=["datum", "kdaj", "prihod", "kateri"]),
        Turn("od 20.3. do 22.3.",
             any_=["noč", "koliko", "odhod"]),
        Turn("2 noci",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 odrasli",
             any_=["ime", "naziv", "koga"]),
        Turn("Uhan Miha",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS18: Check-in ura
    TC("RS18 checkin ura", "REZ_SOBA", [
        Turn("Kdaj je mozen prihod check-in?",
             any_=["14", "prihod", "ura", "upoštev", "popoldne"]),
        Turn("Rezervacija za 5. avgusta 2 noci 2 osebi Potocnik Sara.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS19: Wifi vprašanje
    TC("RS19 wifi vprasanje", "REZ_SOBA", [
        Turn("Imate wifi v sobah?",
             any_=["wifi", "031", "pokliče", "Barbara", "kontakt", "internet", "brezžič"]),
        Turn("Dobro rad bi rezerviral sobo za 15. avgusta 3 noci 2 osebi Mlakar Jan.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS20: VSE CAPS
    TC("RS20 CAPS sporocila", "REZ_SOBA", [
        Turn("ZELIM REZERVIRATI SOBO",
             any_=["datum", "kdaj", "prihod"]),
        Turn("PRIHOD 22. JULIJA",
             any_=["noč", "koliko", "odhod"]),
        Turn("3 NOCI",
             any_=["oseb", "Koliko", "odrasl"]),
        Turn("2 ODRASLA",
             any_=["ime", "naziv", "koga"]),
        Turn("BRAJNIK VESNA",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS21: Angleška sporočila
    TC("RS21 angleski gost", "REZ_SOBA", [
        Turn("Do you have rooms available?",
             any_=["soba", "sob", "datum", "kdaj", "rezerv", "nastanit"]),
        Turn("We would like August 12th for 3 nights 2 adults.",
             any_=["ime", "naziv", "koga", "031", "Barbara"]),
    ]),

    # RS22: Popust za otroke
    TC("RS22 popust otroci", "REZ_SOBA", [
        Turn("Koliko stane za 2 odrasli in 2 otroka?",
             any_=["50", "popust", "otrok", "EUR", "cena", "brezplačno"]),
        Turn("Super. Rezervacija za 12. avgusta 4 noci Lenart Maja.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RS23: Prekinitev z vprašanjem o meniju
    TC("RS23 prekinitev meni", "REZ_SOBA", [
        Turn("Rezerviral bi sobo.",
             any_=["datum", "kdaj", "prihod"]),
        Turn("Kaksne meni imate za vikend?",
             any_=["meni", "kosilo", "degust", "€", "hodni", "rezervac", "Nadaljuj"]),
        Turn("Prihod 5. julija.",
             any_=["noč", "koliko", "odhod"]),
    ]),

    # RS24: Dve sobi (skupina)
    TC("RS24 dve sobi skupina", "REZ_SOBA", [
        Turn("Rabimo dve sobi za 2 para.",
             any_=["datum", "kdaj", "prihod", "031", "Barbara", "pokliče"]),
    ]),

    # RS25: Info → info → booking
    TC("RS25 info info booking", "REZ_SOBA", [
        Turn("Koliko stane jahanje?",
             any_=["5", "€", "poni", "krog", "jahanj"]),
        Turn("In soba koliko stane?",
             any_=["50", "EUR", "€", "osebo", "nastanit"]),
        Turn("Dobro rezerviral bi sobo. Prihod 20. septembra 2 noci 2 osebi Gregoric Natasa.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # ════════════════════════════════════════════
    # REZERVACIJE MIZA (15)
    # ════════════════════════════════════════════

    # RM01: Klasičen 4-turn
    TC("RM01 klasicen 4-turn", "REZ_MIZA", [
        Turn("Rad bi rezerviral mizo.",
             any_=["datum", "kdaj", "termin", "Kdaj"]),
        Turn("21. marca",
             any_=["ura", "ob", "Koliko", "oseb", "kdaj"]),
        Turn("ob 12h nas bo 4",
             any_=["ime", "naziv", "Ime", "koga"]),
        Turn("Sustar Tone",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM02: Z typi
    TC("RM02 z typi", "REZ_MIZA", [
        Turn("zelim mizo za kosilo",
             any_=["datum", "kdaj", "termin"]),
        Turn("sobota 12ga julija",
             any_=["ura", "ob", "Koliko", "oseb"]),
        Turn("ob 13 ura 6 oseb",
             any_=["ime", "naziv", "koga"]),
        Turn("Kos Irena",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM03: Velika skupina
    TC("RM03 velika skupina 10", "REZ_MIZA", [
        Turn("Rezervacija mize za 10 oseb.",
             any_=["datum", "kdaj", "031", "Barbara", "pokliče", "skupin"]),
    ]),

    # RM04: Meni poizvedba potem rezervacija
    TC("RM04 meni nato rezerv", "REZ_MIZA", [
        Turn("Kaksne meni imate za vikend?",
             any_=["meni", "kosilo", "degust", "€", "hodni"]),
        Turn("Ok rada bi rezervirala mizo za 12. aprila ob 12h za 4 osebe Jure Oblak.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM05: Vegetarijansko
    TC("RM05 vegetarijansko", "REZ_MIZA", [
        Turn("Imate vegetarijansko hrano?",
             any_=["031", "pokliče", "dogovor", "Barbara", "posebn", "meni", "kontakt"]),
        Turn("Hvala. Mizo za 8. marca ob 13h za 3 osebe Resman Teja.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM06: Kratka sporočila
    TC("RM06 kratka sporocila", "REZ_MIZA", [
        Turn("mizo prosim",
             any_=["datum", "kdaj", "termin"]),
        Turn("10. maj",
             any_=["ura", "ob", "Koliko", "oseb"]),
        Turn("12h 4os",
             any_=["ime", "naziv", "koga"]),
        Turn("Petan G",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM07: Vse v enem sporočilu
    TC("RM07 vse v enem", "REZ_MIZA", [
        Turn("Mizo bi rezerviral za 25. maja ob 12:30 za 5 oseb ime Vovk Simon.",
             any_=["031", "Barbara", "rezervac", "pokliče", "potrdi", "hvala"]),
    ]),

    # RM08: Jutri (last-minute)
    TC("RM08 jutri", "REZ_MIZA", [
        Turn("Miza za jutri prosim.",
             any_=["ura", "ob", "Koliko", "oseb", "datum", "jutri", "kdaj", "031"]),
    ]),

    # RM09: Specifična ura
    TC("RM09 specificna ura", "REZ_MIZA", [
        Turn("Imate mizo ob 13:30?",
             any_=["datum", "kdaj", "termin", "Koliko", "ura"]),
        Turn("14. junija",
             any_=["ura", "ob", "Koliko", "oseb"]),
        Turn("ob 13:30 nas bo 3",
             any_=["ime", "naziv", "koga"]),
        Turn("Oblak Maja",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM10: Z otroki
    TC("RM10 z otroki", "REZ_MIZA", [
        Turn("Mizo za 2 odrasli in 2 otroka.",
             any_=["datum", "kdaj", "termin"]),
        Turn("19. aprila ob 12h",
             any_=["ime", "naziv", "koga", "oseb", "Koliko"]),
        Turn("4 skupaj 2 odrasli 2 otroka",
             any_=["ime", "naziv", "koga"]),
        Turn("Bertoncelj Petra",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM11: Degustacijski meni potem rezervacija
    TC("RM11 degustat nato rezerv", "REZ_MIZA", [
        Turn("Koliko stane degustacijski meni?",
             any_=["degust", "meni", "€", "hodni", "cena"]),
        Turn("Ok mizo za 20. aprila ob 12h za 4 osebe Klinc Marjan.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM12: Sleng
    TC("RM12 sleng booking", "REZ_MIZA", [
        Turn("bi uzal mizo za vikendski kosil",
             any_=["datum", "kdaj", "termin"]),
        Turn("naslednja sobota",
             any_=["ura", "ob", "Koliko", "oseb", "kdaj"]),
        Turn("ob 12 5 nas bo",
             any_=["ime", "naziv", "koga"]),
        Turn("Furlan Blaz",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM13: Vino k meniju
    TC("RM13 vino k meniju", "REZ_MIZA", [
        Turn("Ali imate domaca vina k meniju?",
             any_=["vino", "bela", "rdeč", "penečih", "Greif", "Frešer"]),
        Turn("Super. Mizo za 5. maja ob 13h za 6 oseb Kos Andrej.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # RM14: Menjava datuma med tokom
    TC("RM14 menjava datuma", "REZ_MIZA", [
        Turn("Mizo za 15. marca.",
             any_=["ura", "ob", "Koliko", "oseb"]),
        Turn("Pravzaprav raje 22. marca ob 12h za 4 osebe Perko Tina.",
             any_=["031", "Barbara", "rezervac", "pokliče", "potrdi"]),
    ]),

    # RM15: Soba nato miza
    TC("RM15 soba nato miza", "REZ_MIZA", [
        Turn("Imate prosto sobo za 10. maja?",
             any_=["datum", "kdaj", "prihod", "soba", "noč", "50", "rezerv"]),
        Turn("Hvala a imate mizo za kosilo ponedeljek ob 12h za 2 osebi ime Simenc Eva.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),

    # ════════════════════════════════════════
    # EDGE (10)
    # ════════════════════════════════════════
    TC("E01 trampolini halucin", "EDGE", [
        Turn("Ali imate trampolinski park?",
             any_=["ni", "ne", "poni", "jahanj", "Julija", "živali", "ponuj"],
             not_=["trampolinsk park je", "organiziramo trampolinsk"]),
    ]),
    TC("E02 banane halucin", "EDGE", [
        Turn("Prodajate banane?",
             any_=["ni", "ne", "domač", "bunka", "marmelad", "spletna"],
             not_=["kilogram banan", "banane so"]),
    ]),
    TC("E03 anglescina soba", "EDGE", [
        Turn("Do you have rooms available?",
             any_=["soba", "sob", "datum", "kdaj", "rezerv", "nastanit"]),
    ]),
    TC("E04 mesani jeziki", "EDGE", [
        Turn("Can I book una soba za vikend?",
             any_=["datum", "kdaj", "prihod", "soba", "termin"]),
    ]),
    TC("E05 jahanje nato booking", "EDGE", [
        Turn("Ali je jahanje mogoce?",
             any_=["poni", "jahanj", "5", "krog", "Malajka"]),
        Turn("In bi rad rezerviral sobo za 15. oktobra 2 noci 2 osebi Oblak Maja.",
             any_=["031", "Barbara", "rezervac", "pokliče"]),
    ]),
    TC("E06 dolgo sporocilo 5 vprasanj", "EDGE", [
        Turn(
            "Zdravo zanima me vasa kmetija. Imam otroke zena je vegetarijanka sam rad pijem vino. "
            "Imate jahanje? Kaksne je meni? Imate sobo za 4 osebe? Kdaj ste odprti?",
            any_=["jahanj", "poni", "meni", "soba", "50", "vino", "€", "degust"],
        ),
    ]),
    TC("E07 isto vprasanje 2x", "EDGE", [
        Turn("Ali je jahanje mogoce?",
             any_=["poni", "jahanj", "5", "krog"]),
        Turn("Ali je jahanje mogoce?",
             any_=["poni", "jahanj", "5", "krog"]),
    ]),
    TC("E08 traktor IN jahanje", "EDGE", [
        Turn("Ponujate voznje s traktorjem ali jahanje?",
             any_=["poni", "jahanj", "5", "mehanizaci"],
             not_=["vožnja s traktorjem je možna", "organiziramo traktor"]),
    ]),
    TC("E09 frustracija", "EDGE", [
        Turn("Vaš chatbot ne dela prav! Hocem informacije!",
             any_=["pomagam", "ponudbi", "031", "Barbara", "informac", "Prosim", "veseljem"]),
    ]),
    TC("E10 pet vprasanj naenkrat", "EDGE", [
        Turn("Zanima me: cena sobe, meni za vikend, jahanje, likerji, in ali imate wifi.",
             any_=["50", "meni", "jahanj", "liker", "€", "poni"]),
    ]),
]

assert len(TESTS) == 125, f"Expected 125 TCs, got {len(TESTS)}"


async def main() -> int:
    brand = get_brand()
    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    print()
    print("════════════════════════════════════════════════════════════════════")
    print("  GAUNTLET 125 — typos · sleng · multi-turn · rezervacije")
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
