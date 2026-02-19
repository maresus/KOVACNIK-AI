from __future__ import annotations

import re

from app2026.chat import answer as answer_mod
from app2026.chat_v3.schemas import InterpretResult


async def execute(result: InterpretResult, message: str, session, brand) -> dict[str, str]:
    if result.intent == "GREETING":
        return {"reply": "Pozdravljeni! Kako vam lahko pomagam?"}
    if result.intent == "THANKS":
        return {"reply": "Prosim, z veseljem. Če želite, lahko nadaljujeva."}
    if result.intent == "SMALLTALK":
        return {"reply": "Z veseljem pomagam glede ponudbe, rezervacij in informacij o kmetiji."}
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
    # Hišni ljubljenčki / psi
    if any(kw in msg_l for kw in ("psa", "pse", "pes ", " pes", "psicko", "psičko")) or re.search(r"\bpes\b", msg_l):
        if any(kw in msg_l for kw in ("dovol", "prepo", "sme", "lahko", "prinest", "pripelj", "sprejmete", "sprejma", "imam")):
            return {
                "reply": (
                    "Žal hišnih ljubljenčkov pri nas ne sprejemamo.\n"
                    "Če vas zanimajo živali na naši kmetiji, jih ob obisku z veseljem pokažemo! "
                    "Pokličite Barbaro za dogovor: 031 330 113"
                )
            }
    # Alergije / posebna prehrana
    if any(kw in msg_l for kw in ("alergij", "alergijo", "brezglutensko", "brezgluten", "celiakij", "laktozni", "vegansk", "vegetarijan")):
        return {
            "reply": (
                "Za posebne prehranske zahteve (alergije, vegetarijansko, brezglutensko) "
                "nas pokličite vnaprej — Barbara bo poskrbela za vaše potrebe.\n"
                "Pokličite: 031 330 113 ali pišite: info@kovacnik.si"
            )
        }
    # Clarification from LLM — only after all deterministic traps have been checked
    if result.needs_clarification and result.clarification_question:
        return {"reply": result.clarification_question}
    return {"reply": answer_mod.answer(message, session, brand)}
