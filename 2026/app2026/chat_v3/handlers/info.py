from __future__ import annotations

import datetime
import re
from typing import Any

from app.rag.knowledge_base import KNOWLEDGE_CHUNKS
from app2026.brand.kovacnik_data import (
    ANIMALS,
    CONTACT,
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


def _normalize_text(text: str) -> str:
    """Lowercase + strip Slovene diacritics for key matching."""
    return (
        (text or "").lower()
        .replace("ž", "z").replace("š", "s").replace("č", "c")
        .replace("ć", "c").replace("đ", "d")
    )


def _extract_name(result: InterpretResult, message: str) -> str:
    # Normalize diacritics so LLM's "čarli" matches key "carli" etc.
    direct = _normalize_text(str((result.entities or {}).get("name", ""))).strip()
    if direct:
        return direct
    # Normalize message so "čarli" matches key "carli" etc.
    text = _normalize_text(message)
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
        # Check if the name is actually an animal (LLM misclassified as INFO_PERSON)
        if name and name in ANIMALS:
            adata = ANIMALS[name]
            aname = adata.get("name", name)
            atype = adata.get("type", "")
            return {"reply": f"{aname} je {atype}." if atype else f"{aname} je žival na naši kmetiji."}
        # No specific name — score persons by token overlap with message
        msg_l = (message or "").lower()
        msg_tokens = set(t for t in re.findall(r"[a-zšžčćđ]+", msg_l) if len(t) >= 4)
        best_score = 0
        best_person: dict[str, Any] | None = None
        for pdata in PERSONS.values():
            notes_str = " ".join(str(n) for n in (pdata.get("notes") or [])).lower()
            role_str = (pdata.get("role") or "").lower()
            name_str = (pdata.get("name") or "").lower()
            combined = f"{name_str} {role_str} {notes_str}"
            score = sum(1 for tok in msg_tokens if tok in combined)
            if score > best_score:
                best_score = score
                best_person = pdata
        if best_score > 0 and best_person:
            return {"reply": _format_person(best_person)}
        # List all family members as fallback
        lines = ["Naša družina:"]
        for pdata in PERSONS.values():
            lines.append(f"  • {_format_person(pdata)}")
        return {"reply": "\n".join(lines)}

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
        # No specific room name — check for feature keywords or list all rooms
        msg_l = (message or "").lower()
        if any(kw in msg_l for kw in ("wifi", "wi-fi", "brezžičn", "internet", "wireless")):
            return {"reply": "Da, vse naše sobe imajo brezžično omrežje (WiFi) brezplačno."}
        if any(kw in msg_l for kw in ("klima", "klimat", "hlajenje", "ogrevanje")):
            return {"reply": "Da, vse naše sobe imajo klimatizacijo."}
        if any(kw in msg_l for kw in ("satelit", "telev", " tv ", "televizij")):
            return {"reply": "Da, vse naše sobe imajo satelitsko televizijo."}
        if any(kw in msg_l for kw in ("balkon",)):
            return {"reply": "Sobe ALJAŽ in JULIJA imata balkon. Soba ANA ima dve spalnici."}
        if any(kw in msg_l for kw in ("kopalnic", "tuš", "banjic")):
            return {"reply": "Vse sobe imajo lastno kopalnico s tušem."}
        # Generic room listing
        lines = ["Imamo 3 sobe, poimenovane po naših otrocih:"]
        for rdata in ROOMS.values():
            rname = rdata["name"]
            cap = rdata.get("capacity", "")
            price = rdata.get("price_per_person_eur", "")
            feats = ", ".join(rdata.get("features", [])[:3])
            lines.append(f"  • {rname}: kapaciteta {cap}, {price} EUR/osebo/noč — {feats}")
        lines.append("\nVse cene vključujejo zajtrk. Check-in 14:00, check-out 10:00.")
        return {"reply": "\n".join(lines)}

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

    if intent in ("INFO_MENU", "INFO_MENU_DETAIL"):
        msg_lower = (message or "").lower()

        # --- Specific X-hodni menu (from entities or from message text) ---
        _course_num: int | None = None
        _courses_entity = (result.entities or {}).get("courses")
        if isinstance(_courses_entity, int) and 4 <= _courses_entity <= 7:
            _course_num = _courses_entity
        else:
            _m = re.search(r"\b([4-7])\s*[-]?\s*hodni\b", msg_lower)
            if _m:
                _course_num = int(_m.group(1))

        if _course_num:
            _key = f"{_course_num}-hodni"
            _menus = WEEKDAY_DEGUSTATION.get("menus", {})
            _menu = _menus.get(_key)
            if _menu:
                _rules = WEEKDAY_DEGUSTATION.get("rules", {})
                _name = _menu.get("name", _key.upper())
                _price = _menu.get("price_eur", "")
                _wine_p = _menu.get("wine_pairing_eur", "")
                _courses_list = _menu.get("courses", [])
                _lines = [f"{_name}: {_price} EUR (vinska degustacija +{_wine_p} EUR)"]
                for _c in _courses_list:
                    _dish = _c.get("dish", "")
                    _wine = _c.get("wine")
                    if _wine:
                        _lines.append(f"  • {_dish}  ←  {_wine}")
                    else:
                        _lines.append(f"  • {_dish}")
                _lines.append(
                    f"\nDni: {_rules.get('days', '')}, {_rules.get('time', '')}, "
                    f"min. {_rules.get('min_people', 6)} oseb."
                )
                return {"reply": "\n".join(_lines)}

        # --- General weekday degustation menu list ---
        if any(kw in msg_lower for kw in ("teden", "tedenski", "degustat", "sreda", "četrtek", "cetrtek", "petek", "hodni")):
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
        # Check for a specific animal in the message
        msg_l = (message or "").lower()
        specific: dict[str, Any] | None = None
        for key, adata in ANIMALS.items():
            aname = (adata.get("name") or "").lower()
            if key in msg_l or (aname and aname in msg_l):
                specific = adata
                break
        if specific:
            aname = specific.get("name", "Žival")
            atype = specific.get("type", "")
            acount = specific.get("count", "")
            desc = f"{aname} je {atype}" if atype else aname
            if acount:
                desc += f" ({acount})"
            return {"reply": desc + "."}
        # List all animals
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

    if intent == "INFO_GENERAL":
        msg_l = (message or "").lower()
        farm_name = CONTACT.get("name", "Domačija Kovačnik")
        phone = CONTACT.get("mobile", "031 330 113")
        # Parking
        if any(kw in msg_l for kw in ("parking", "parkirišč", "parkir", "avto")):
            return {"reply": "Da, imamo brezplačno parkirišče neposredno ob kmetiji."}
        # WiFi (general, outside room context)
        if any(kw in msg_l for kw in ("wifi", "wi-fi", "brezžičn", "internet")):
            return {"reply": "Da, WiFi je brezplačno na voljo v vseh sobah in skupnih prostorih."}
        # Domači izdelki / shop
        if any(kw in msg_l for kw in ("domač", "salama", "bunk", "marmelad", "sirek", "liker", "pridelk", "nakup", "trgovin", "prodaj")):
            return {
                "reply": (
                    "Naši domači izdelki:\n"
                    "  • Pohorska bunka (sušeno meso)\n"
                    "  • Hišna suha salama\n"
                    "  • Frešerjev zorjen sirček\n"
                    "  • Domači namazi (bučni, zeliščni)\n"
                    "  • Marmelade in kompoti\n"
                    "  • Hišni liker\n"
                    f"Za nakup pokličite: {phone}"
                )
            }
        # Aktivnosti
        if any(kw in msg_l for kw in ("aktivnost", "počet", "jahanj", "poni", "kolesarj", "pohod", "izlet", "ogled", "doživetj")):
            return {
                "reply": (
                    "Aktivnosti na Domačiji Kovačnik:\n"
                    "  • Jahanje na ponijih Malajka in Marsi\n"
                    "  • Ogled in hranjenje živali (pujska Pepa, ovca Čarli, psička Luna...)\n"
                    "  • Pohodništvo in kolesarjenje po Pohorju\n"
                    "  • Ogled kmečkih opravil in pridelave\n"
                    "  • Animatorske aktivnosti za otroke\n"
                    f"Več info: {phone}"
                )
            }
        # Children / family friendly
        if any(kw in msg_l for kw in ("otrok", "otroci", "druzin", "primern", "mlad")):
            return {
                "reply": (
                    f"{farm_name} je odlična destinacija za družine z otroki! "
                    "Otroci se lahko igrajo z živalmi, jahajo na ponijih, "
                    "spoznajo kmečko življenje in uživajo v naravnem okolju Pohorja. "
                    "V vikend meniju otroci (4–12 let) plačajo le 50% cene. "
                    f"Pokličite: {phone}"
                )
            }
        # General farm info / name
        return {
            "reply": (
                f"Dobrodošli na {farm_name}!\n"
                f"Nahajamo se na: {CONTACT.get('address', 'Planica 9, 2313 Fram')} (Pohorje)\n"
                f"Kontakt: {phone} / {CONTACT.get('phone', '02 601 54 00')}\n"
                "Ponujamo: vikend kosila, tedenski degustacijski meniji, nastanitev v sobah, "
                "domači izdelki, jahanje, ogled živali."
            )
        }

    # Fallback to existing v2 info flow for remaining INFO intents.
    return {"reply": info_flow.handle(message, brand, session)}
