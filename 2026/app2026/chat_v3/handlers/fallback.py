from __future__ import annotations

import re

from app2026.chat import answer as answer_mod
from app2026.chat_v3.schemas import InterpretResult


async def execute(result: InterpretResult, message: str, session, brand) -> dict[str, str]:
    if result.intent == "GREETING":
        return {
            "reply": (
                "Pozdravljeni na Domačiji Kovačnik!\n\n"
                "Z veseljem vam pomagam pri:\n"
                "  • Rezervaciji sobe (imamo 3 družinske sobe)\n"
                "  • Rezervaciji mize za kosilo (sob/ned)\n"
                "  • Informacijah o ponudbi in kmetiji\n\n"
                "Kako vam lahko pomagam?"
            )
        }
    if result.intent == "THANKS":
        return {"reply": "Prosim, z veseljem! Če vas zanima še kaj, sem tu."}
    if result.intent == "SMALLTALK":
        return {
            "reply": (
                "Jaz sem virtualni pomočnik Domačije Kovačnik.\n\n"
                "Pomagam pri rezervacijah sob in miz ter odgovarjam na vprašanja o kmetiji.\n"
                "Če potrebujete osebni pogovor, pokličite Barbaro: 031 330 113"
            )
        }
    # Keyword traps — catch deterministic cases even when LLM confidence is low
    # IMPORTANT: these run BEFORE needs_clarification so deterministic content always wins
    msg_l = (message or "").lower()
    if "traktor" in msg_l:
        return {
            "reply": (
                "Traktor je del naše kmetijske mehanizacije — vožnja za goste ni v ponudbi.\n"
                "Za aktivnosti z otroki priporočamo jahanje na ponijih Malajka in Marsi (5 € na krog)."
            )
        }
    # Vremenska napoved — chatbot NIMA dostopa do vremenskih podatkov
    # Mora ujeti: "kako bo vreme", "kakšno bo vreme", "vreme jutri", "vreme naslednji teden"
    if any(kw in msg_l for kw in (
        "kako bo vreme", "kakšno bo vreme", "kaksno bo vreme", "kakšno vreme", "kaksno vreme",
        "bo vreme", "napoved vreme", "vremenska napoved", "vreme naslednji", "vreme ta vikend",
        "vreme jutri", "vreme danes", "ali bo lep", "ali bo deževal", "ali bo dezeval",
        "bo deževalo", "bo dezevalo", "vreme v ", "vreme za "
    )) or (re.search(r"\bvreme\b", msg_l) and any(kw in msg_l for kw in ("kdaj", "naslednji", "vikend", "jutri", "danes", "teden"))):
        return {
            "reply": (
                "Žal vremenskih napovedi nimam — nisem povezan z vremenskimi servisi.\n"
                "Za napoved priporočam yr.no ali ARSO.\n\n"
                "Lahko pa pomagam z rezervacijo ali informacijami o kmetiji!"
            )
        }
    if any(kw in msg_l for kw in ("dežj", "deže", "deževn", "slabo vreme", "dežuje", "dez ", "dezuje", "dežuje")):
        return {
            "reply": (
                "Ob dežju je kmetija prav tako prijetna!\n"
                "  • Ogled živali v hlevu — Julija jih rada pokaže otrokom\n"
                "  • Degustacija domačih likerjev, sirupov in marmelad\n"
                "  • Degustacijski meni (po dogovoru)\n"
                "  • Degustacija vin v prijetnem domačem vzdušju\n"
                "Pokličite nas: 031 330 113"
            )
        }
    # "dez" alone (no diacritics) — match only as standalone word or start of token
    if re.search(r"\bdez\b", msg_l):
        return {
            "reply": (
                "Ob dežju je kmetija prav tako prijetna!\n"
                "  • Ogled živali v hlevu — Julija jih rada pokaže otrokom\n"
                "  • Degustacija domačih likerjev, sirupov in marmelad\n"
                "  • Degustacijski meni (po dogovoru)\n"
                "Pokličite nas: 031 330 113"
            )
        }
    if any(kw in msg_l for kw in ("pozim", "zimsk", "pozimi", "zima ", "zimsk")) or re.search(r"\bzima\b", msg_l):
        return {
            "reply": (
                "Najbližji smučišči sta Mariborsko Pohorje in Areh — od nas je do obeh nekje 25–35 minut vožnje.\n"
                "Odlična izbira za poldnevni ali celodnevni izlet med bivanjem pri nas.\n"
                "Če potrebujete nasvet o pristopu ali kje je manj gneče, vam z veseljem povemo."
            )
        }
    if any(kw in msg_l for kw in ("animaci", "animator")):
        return {
            "reply": (
                "Na kmetiji skrbi za zabavo in animacijo Julija — animatorka, ki otrokom z veseljem pokaže živali.\n"
                "Otroci se lahko uredijo na ponijih (jahanje: 5 € na krog — Malajka in Marsi).\n"
                "Za skupinsko animacijo nas pokličite: 031 330 113"
            )
        }
    if any(kw in msg_l for kw in ("prodajate", "prodajte", "prodaja", "kaj prodaj")):
        return {
            "reply": (
                "Naši domači izdelki (v spletni trgovini in ob obisku):\n"
                "  • Pohorska bunka, 500 g — 18–21 €\n"
                "  • Suha salama, 650 g — 16 €\n"
                "  • Frešerjev zorjen sirček\n"
                "  • Bučni namaz, 212 ml — 7 €\n"
                "  • Marmelade — od 5,50 €\n"
                "  • Likerji (borovničev, žajbljev) — 13 €\n"
                "🛒 https://kovacnik.com/kovacnikova-spletna-trgovina/"
            )
        }
    # Mesni izdelki / bunka — brez diakritik ("bunk za domov")
    if any(kw in msg_l for kw in ("bunk", "pohorsk bunk", "domaca bunka")):
        return {
            "reply": (
                "Mesni izdelki Kovačnik:\n"
                "  • Pohorska bunka, 500 g — 18–21 €\n"
                "  • Suha salama, 650 g — 16 €\n"
                "  • Hišna suha klobasa, 180 g — 7 €\n"
                "🛒 https://kovacnik.com/kovacnikova-spletna-trgovina/"
            )
        }
    # Jahanje za otroke — slang "jaha" / "jahanje" / "lahk jaha"
    if re.search(r"\bjaha", msg_l) or any(kw in msg_l for kw in ("lahk jaha", "lahko jaha", "jahamo", "jahanj")):
        return {
            "reply": (
                "Jahanje s ponijem je mogoče! 🐴\n"
                "Na kmetiji imata Malajka in Marsi rada najmlajše goste.\n"
                "Cena: 5 € na krog. Ob prihodu povejte, da bi radi jahali.\n"
                "Ni vnaprej rezervirano."
            )
        }
    # Otroci — aktivnosti za otroke (slang "kej grejo", "kam grejo")
    if any(kw in msg_l for kw in ("otroke", "otroci", "otrok")) and \
       any(kw in msg_l for kw in ("kej", "kje", "grejo", "kam", "aktivnost", "zabav", "kaj narest", "kaj naredit")):
        return {
            "reply": (
                "Z otroki je na kmetiji veliko za početi:\n"
                "  • Jahanje na ponijih Malajka in Marsi (5 € na krog)\n"
                "  • Julija z veseljem pokaže živali v hlevu\n"
                "  • Sprehodi po kmetiji in naravi\n"
                "Pokličite: 031 330 113"
            )
        }
    # Božanje živali — petting farm animals (NOT bringing pets)
    # Must fire BEFORE pet policy so "božamo mačke" doesn't trigger pet rejection
    if any(kw in msg_l for kw in ("bož", "pobož", "božam", "božamo", "boham", "bohamo")):
        if any(kw in msg_l for kw in ("mačk", "muck", "muce", "zajc", "poni", "konj", "krav", "žival", "mucek", "macke", "macek")):
            return {
                "reply": (
                    "Seveda! Naše živali lahko pobožate ob obisku.\n"
                    "Julija z veseljem pokaže živali otrokom in odraslim."
                )
            }
    # Hišni ljubljenčki / psi — razširjen za typo variante
    if any(kw in msg_l for kw in ("psa", "pse", "pes ", " pes", "psicko", "psičko")) or re.search(r"\bpes\b", msg_l):
        if any(kw in msg_l for kw in ("dovol", "prepo", "sme", "lahko", "lahk", "prinest", "pripelj", "prpelj", "sprejmete", "sprejma", "imam", "vzam", "peljem", "pelem")):
            return {
                "reply": (
                    "Žal hišnih ljubljenčkov pri nas ne sprejemamo.\n"
                    "Če vas zanimajo živali na naši kmetiji, jih ob obisku z veseljem pokažemo! "
                    "Pokličite Barbaro za dogovor: 031 330 113"
                )
            }
    # Check-in IN check-out skupaj
    if ("check-in" in msg_l or "checkin" in msg_l or "prihod" in msg_l) and \
       ("check-out" in msg_l or "checkout" in msg_l or "odhod" in msg_l):
        return {
            "reply": (
                "Ure prihoda in odhoda:\n"
                "  • Check-in (prihod): od 14:00 naprej\n"
                "  • Check-out (odhod): do 10:00\n"
                "Če potrebujete zgodnejši prihod ali kasnejši odhod, nas pokličite vnaprej: 031 330 113"
            )
        }
    # Alergije / posebna prehrana
    if any(kw in msg_l for kw in ("alergij", "alergijo", "brezglutensko", "brezgluten", "celiakij", "laktozni", "vegansk", "vegetarijan")):
        return {
            "reply": (
                "Za posebne prehranske zahteve (alergije, vegetarijansko, brezglutensko) "
                "nas pokličite vnaprej — Barbara bo poskrbela za vaše potrebe.\n"
                "Pokličite: 031 330 113 ali pišite: info@kovacnik.com"
            )
        }
    # Posebne rezervacije — degustacije, dogodki, team building, praznovanja
    # Te zahtevajo osebni pogovor, chatbot jih ne more obdelati
    if any(kw in msg_l for kw in (
        "degustacij", "team building", "teambuilding", "tim bilding", "dogodek", "dogodk",
        "zabav", "praznovan", "rojstni dan", "rojstnidan", "obletnic", "poroka", "porok",
        "predstavitev", "seminar", "delavnic", "workshop", "zasebna", "zasebno",
        "firma", "podjetj", "korporativ", "poslovna", "poslovn"
    )) and any(kw in msg_l for kw in ("rezerv", "naroč", "organizir", "priredit", "bi rad", "bi radi", "želim", "zelim", "hočem", "hocem")):
        return {
            "reply": (
                "Za degustacije, dogodke in posebna praznovanja se obrnite direktno na Barbaro, "
                "da skupaj oblikujeta popolno izkušnjo.\n\n"
                "Pokličite: 031 330 113\n"
                "ali pišite: info@kovacnik.com"
            )
        }
    # Catch-all: rezervacija nečesa, kar JASNO ni soba/miza → usmeri na kontakt
    # Če je samo "rezerv" brez konteksta, pusti LLM da vpraša "sobo ali mizo?"
    non_room_table_items = (
        "narezk", "narezek", "pijač", "tort", "peciv", "sladico", "sladice",
        "hran", "jedilnik", "menu", "piknik", "zajtrk", "večerj", "malico"
    )
    if any(kw in msg_l for kw in ("rezerv", "naroč")) and any(item in msg_l for item in non_room_table_items):
        return {
            "reply": (
                "Za ta tip rezervacije nas kontaktirajte direktno:\n"
                "031 330 113 ali info@kovacnik.com"
            )
        }
    # Clarification from LLM — only after all deterministic traps have been checked
    if result.needs_clarification and result.clarification_question:
        return {"reply": result.clarification_question}
    return {"reply": answer_mod.answer(message, session, brand)}
