from __future__ import annotations

import datetime
from typing import Any

from app.rag.knowledge_base import KNOWLEDGE_CHUNKS
from app2026.brand.kovacnik_data import (
    ANIMALS,
    PERSONS,
    ROOMS,
    SEASONAL_WEEKEND_MENUS,
    WEEKDAY_DEGUSTATION,
    WINES,
    resolve_entity,
)
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
        _resolved_type = (result.entities or {}).get("_resolved")
        if name and _resolved_type == "person":
            person_data = PERSONS.get(name)
            if person_data:
                return {"reply": _format_person(person_data)}
        elif name and _resolved_type == "room":
            room_data = ROOMS.get(name)
            if room_data:
                return {"reply": _format_room(room_data)}
        elif name:
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
        _resolved_type = (result.entities or {}).get("_resolved")
        if name and _resolved_type == "room":
            room_data = ROOMS.get(name)
            if room_data:
                return {"reply": _format_room(room_data)}
        elif name and _resolved_type == "person":
            person_data = PERSONS.get(name)
            if person_data:
                return {"reply": _format_person(person_data)}
        elif name:
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

    if intent == "INFO_WINE":
        sparkling = WINES.get("sparkling") or []
        white = WINES.get("white") or []
        red = WINES.get("red") or []
        parts: list[str] = []
        if sparkling:
            names = [f"{w['name']} ({w.get('type', '')})" for w in sparkling]
            parts.append("Peneča vina: " + ", ".join(names))
        if white:
            names = [f"{w['name']} ({w.get('type', '')})" for w in white]
            parts.append("Bela vina: " + ", ".join(names))
        if red:
            names = [f"{w['name']} ({w.get('type', '')})" for w in red]
            parts.append("Rdeča vina: " + ", ".join(names))
        if parts:
            return {
                "reply": (
                    "Naša vinska karta:\n"
                    + "\n".join(parts)
                    + "\n\nZa podrobnosti (letnik, opis, cena) z veseljem povem več!"
                )
            }
        return {"reply": "Žal nimam aktualnih podatkov o vinski karti."}

    if intent == "INFO_MENU":
        msg_lower = (message or "").lower()
        # Weekday degustation menu
        if any(kw in msg_lower for kw in ("teden", "tedenski", "degustat", "sreda", "četrtek", "cetrtek", "petek")):
            rules = WEEKDAY_DEGUSTATION.get("rules", {})
            menus = WEEKDAY_DEGUSTATION.get("menus", {})
            days = rules.get("days", "")
            time_ = rules.get("time", "")
            min_p = rules.get("min_people", 6)
            lines = [f"Tedenski degustacijski meniji ({days}, {time_}, min. {min_p} oseb):"]
            for menu_name, m in menus.items():
                price = m.get("price_eur", "")
                lines.append(f"  • {menu_name}: {price} EUR")
            lines.append("\nZa rezervacijo pokličite: 031 330 113")
            return {"reply": "\n".join(lines)}
        # Current seasonal weekend menu
        current_month = datetime.datetime.now().month
        current_menu = None
        current_label = None
        for label, menu_data in SEASONAL_WEEKEND_MENUS.items():
            months = menu_data.get("months", [])
            if current_month in months:
                current_menu = menu_data
                current_label = label
                break
        if current_menu:
            items = current_menu.get("items") or []
            lines = [f"Aktualni vikend meni — {current_label}:"]
            for item in items:
                lines.append(f"  • {item}")
            lines.append("\nMeniji potekajo ob sobotah in nedeljah od 12:00 naprej.")
            return {"reply": "\n".join(lines)}
        return {"reply": "Žal nimam podatkov o aktualnem meniju. Za informacije pokličite: 031 330 113"}

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
