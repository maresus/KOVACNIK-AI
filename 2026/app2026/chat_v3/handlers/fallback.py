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
    # Traktor hallucination trap — catch even when LLM falls below confidence threshold
    msg_l = (message or "").lower()
    if "traktor" in msg_l:
        return {
            "reply": (
                "Traktor je del naše kmetijske mehanizacije — vožnja za goste ni v ponudbi.\n"
                "Za aktivnosti z otroki priporočamo jahanje na ponijih Malajka in Marsi (5 € na krog)."
            )
        }
    return {"reply": answer_mod.answer(message, session, brand)}
