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
    return {"reply": answer_mod.answer(message, session, brand)}
