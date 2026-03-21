from __future__ import annotations

from typing import Any

from app.rag.knowledge_base import generate_llm_answer


def answer(message: str, session, brand: Any) -> str:
    history = getattr(session, "history", None)
    try:
        return generate_llm_answer(message, history=history or [])
    except Exception as e:
        print(f"[answer.py] LLM napaka: {type(e).__name__}: {e}")
        return (
            "Na to vprašanje nimam dobrega odgovora.\n\n"
            "Z veseljem pomagam pri:\n"
            "  • Rezervaciji sobe ali mize\n"
            "  • Informacijah o kmetiji, sobah, jedilnici\n"
            "  • Cenah in ponudbi\n\n"
            "Ali vas zanima kaj od tega?"
        )
