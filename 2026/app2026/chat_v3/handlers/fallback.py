from __future__ import annotations

from app2026.chat import answer as answer_mod
from app2026.chat_v3.schemas import InterpretResult


async def execute(result: InterpretResult, message: str, session, brand) -> dict[str, str]:
    if result.intent == "GREETING":
        return {"reply": "Pozdravljeni! Kako vam lahko pomagam?"}
    if result.intent == "THANKS":
        return {"reply": "Prosim, z veseljem. Če želite, lahko nadaljujeva."}
    if result.intent == "SMALLTALK":
        return {"reply": "Z veseljem pomagam glede ponudbe, rezervacij in informacij o kmetiji."}
    if result.needs_clarification and result.clarification_question:
        return {"reply": result.clarification_question}
    # Keyword traps — catch deterministic cases even when LLM confidence is low
    msg_l = (message or "").lower()
    if "traktor" in msg_l:
        return {
            "reply": (
                "Traktor je del naše kmetijske mehanizacije — vožnja za goste ni v ponudbi.\n"
                "Za aktivnosti z otroki priporočamo jahanje na ponijih Malajka in Marsi (5 € na krog)."
            )
        }
    if any(kw in msg_l for kw in ("dežj", "deže", "deževn", "slabo vreme", "dežuje")):
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
    return {"reply": answer_mod.answer(message, session, brand)}
