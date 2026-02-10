from __future__ import annotations

from typing import Any

from app.rag.knowledge_base import generate_llm_answer


def answer(message: str, session, brand: Any) -> str:
    history = getattr(session, "history", None)
    try:
        return generate_llm_answer(message, history=history or [])
    except Exception:
        return "Trenutno nimam jasnega odgovora. Lahko vprašanje malo drugače?"
