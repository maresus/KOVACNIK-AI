from __future__ import annotations

from typing import Any

from app.rag.knowledge_base import KNOWLEDGE_CHUNKS
from app2026.brand.kovacnik_data import ANIMALS, PERSONS, ROOMS, resolve_entity
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


def _extract_name(result: InterpretResult, message: str) -> str:
    direct = str((result.entities or {}).get("name", "")).strip().lower()
    if direct:
        return direct
    text = (message or "").lower()
    candidates = set(PERSONS.keys()) | set(ROOMS.keys()) | set(ANIMALS.keys())
    for key in sorted(candidates, key=len, reverse=True):
        if key in text:
            return key
    return ""


def _format_person(data: dict[str, Any]) -> str:
    name = data.get("name", "Ta oseba")
    role = data.get("role")
    phone = data.get("phone")
    notes = data.get("notes") or []
    parts = [f"{name} je {role} na domačiji." if role else f"{name} je del družine na domačiji."]
    if notes:
        parts.append("Posebnost: " + ", ".join(str(n) for n in notes) + ".")
    if phone:
        parts.append(f"Kontakt: {phone}.")
    return " ".join(parts)


def _format_room(data: dict[str, Any]) -> str:
    name = data.get("name", "Soba")
    capacity = data.get("capacity", "")
    price = data.get("price_per_person_eur")
    features = data.get("features") or []
    parts = [f"{name} je družinska soba (kapaciteta {capacity})." if capacity else f"{name} je družinska soba."]
    if isinstance(price, (int, float)):
        parts.append(f"Cena je {price} EUR na osebo/noč z zajtrkom.")
    if features:
        parts.append("Vključuje: " + ", ".join(str(f) for f in features[:5]) + ".")
    return " ".join(parts)


async def execute(result: InterpretResult, message: str, session: Any, brand: Any) -> dict[str, str]:
    intent = result.intent

    if intent == "INFO_PERSON":
        name = _extract_name(result, message)
        if name:
            resolved = resolve_entity(name)
            if resolved.get("action") == "clarify":
                return {"reply": str(resolved.get("question"))}
            if resolved.get("type") == "person":
                return {"reply": _format_person(resolved.get("data") or {})}
            if resolved.get("type") == "room":
                return {
                    "reply": f"Ali vas zanima soba {resolved.get('data', {}).get('name', '').strip()} ali oseba z istim imenom?"
                }
        chunks = _search_filtered(
            query=f"družina zgodovina {name}",
            include=("družina", "zgodovina", "gospodar", "sin", "hči", "hci"),
            exclude=("soba", "nastanitev"),
        )
        text = _snippet_from_chunks(chunks)
        return {"reply": text or f"Žal nimam potrjenih podatkov o osebi {name}."}

    if intent == "INFO_ROOM":
        name = _extract_name(result, message)
        if name:
            resolved = resolve_entity(name)
            if resolved.get("action") == "clarify":
                return {"reply": str(resolved.get("question"))}
            if resolved.get("type") == "room":
                return {"reply": _format_room(resolved.get("data") or {})}
            if resolved.get("type") == "person":
                return {
                    "reply": f"Ali vas zanimajo informacije o osebi {resolved.get('data', {}).get('name', '').strip()} ali o sobi z istim imenom?"
                }
        chunks = _search_filtered(
            query=f"soba nastanitev {name}",
            include=("soba", "nastanitev"),
            exclude=("zgodovina", "družina"),
        )
        text = _snippet_from_chunks(chunks)
        return {"reply": text or "Žal nimam potrjenih podatkov o tej sobi."}

    if intent == "INFO_ANIMAL":
        names = [v.get("name") for v in ANIMALS.values() if v.get("name")]
        if names:
            return {"reply": "Na kmetiji imamo: " + ", ".join(names) + "."}
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
