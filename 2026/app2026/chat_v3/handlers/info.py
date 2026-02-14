from __future__ import annotations

from typing import Any

from app.rag.knowledge_base import KNOWLEDGE_CHUNKS
from app2026.chat.flows import info as info_flow
from app2026.chat_v3.schemas import InterpretResult


def _snippet_from_chunks(chunks: list[Any]) -> str | None:
    if not chunks:
        return None
    top = chunks[0]
    text = (top.paragraph or "").strip()
    if len(text) > 420:
        text = text[:420].rsplit(" ", 1)[0] + "..."
    if top.url:
        return f"{text}\n\nVeč: {top.url}"
    return text


def _search_filtered(query: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> list[Any]:
    q = query.lower()
    out = []
    for chunk in KNOWLEDGE_CHUNKS:
        title = (chunk.title or "").lower()
        body = (chunk.paragraph or "").lower()
        full = f"{title} {body}"
        if include and not any(tok in full for tok in include):
            continue
        if exclude and any(tok in full for tok in exclude):
            continue
        if any(tok in full for tok in q.split() if len(tok) >= 3):
            out.append(chunk)
    return out[:3]


async def execute(result: InterpretResult, message: str, session: Any, brand: Any) -> dict[str, str]:
    intent = result.intent

    if intent == "INFO_PERSON":
        name = str(result.entities.get("name", "")).strip()
        chunks = _search_filtered(
            query=f"družina zgodovina {name}",
            include=("družina", "zgodovina", "gospodar", "sin", "hči", "hci"),
            exclude=("soba", "nastanitev"),
        )
        text = _snippet_from_chunks(chunks)
        return {"reply": text or f"Žal nimam potrjenih podatkov o osebi {name}."}

    if intent == "INFO_ROOM":
        name = str(result.entities.get("name", "")).strip()
        chunks = _search_filtered(
            query=f"soba nastanitev {name}",
            include=("soba", "nastanitev"),
            exclude=("zgodovina", "družina"),
        )
        text = _snippet_from_chunks(chunks)
        return {"reply": text or "Žal nimam potrjenih podatkov o tej sobi."}

    if intent == "INFO_ANIMAL":
        chunks = _search_filtered(
            query=message,
            include=("živali", "zivali", "poni", "ovnom", "mucke", "psička", "psicka"),
            exclude=(),
        )
        text = _snippet_from_chunks(chunks)
        if text:
            return {"reply": text}

    # Fallback to existing v2 info flow for remaining INFO intents.
    return {"reply": info_flow.handle(message, brand, session)}
