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
        # Try exact key match first
        candidates_all = set(PERSONS.keys()) | set(ROOMS.keys()) | set(ANIMALS.keys())
        if direct in candidates_all:
            return direct
        # Genitive/case fallback: first 5 chars prefix match (e.g. "danila"→"danilo")
        for key in sorted(candidates_all, key=len, reverse=True):
            if len(key) >= 5 and len(direct) >= 5 and key[:5] == direct[:5]:
                return key
        return direct
    # Normalize message so "čarli" matches key "carli" etc.
    text = _normalize_text(message)
    candidates = set(PERSONS.keys()) | set(ROOMS.keys()) | set(ANIMALS.keys())
    for key in sorted(candidates, key=len, reverse=True):
        if key in text:
            return key
    # Case form fallback: first 5 chars prefix match for genitive forms (e.g. "danila"→"danilo")
    for word in sorted(re.findall(r"[a-z]+", text), key=len, reverse=True):
        if len(word) < 5:
            continue
        for key in sorted(candidates, key=len, reverse=True):
            if len(key) >= 5 and key[:5] == word[:5]:
                return key
    return ""


def _format_person(data: dict[str, Any], show_phone: bool = False) -> str:
    name = data.get("name", "Ta oseba")
    role = data.get("role")
    phone = data.get("phone")
    notes = data.get("notes") or []
    parts = [f"{name} je {role} na domačiji." if role else f"{name} je del naše družine."]
    if notes:
        parts.append(", ".join(str(n) for n in notes) + ".")
    if phone and show_phone:
        parts.append(f"Pokličete ga/jo na: {phone}.")
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
        msg_l = (message or "").lower()
        _want_phone = any(kw in msg_l for kw in ("telefon", "kontakt", "pokliče", "poklič", "številk"))
        if name and _resolved_type == "person":
            person_data = PERSONS.get(name)
            if person_data:
                return {"reply": _format_person(person_data, show_phone=_want_phone)}
        elif name and _resolved_type == "room":
            room_data = ROOMS.get(name)
            if room_data:
                return {"reply": _format_room(room_data)}
        elif name:
            resolved = resolve_entity(name)
            if resolved.get("action") == "clarify":
                return {"reply": str(resolved.get("question"))}
            if resolved.get("type") == "person":
                return {"reply": _format_person(resolved.get("data") or {}, show_phone=_want_phone)}
            if resolved.get("type") == "room":
                return {
                    "reply": f"Ali vas zanima soba {resolved.get('data', {}).get('name', '').strip()} ali oseba z istim imenom?"
                }
        # Check if the name is actually an animal (LLM misclassified as INFO_PERSON)
        if name and name in ANIMALS:
            adata = ANIMALS[name]
            aname = adata.get("name", name)
            atype = adata.get("type", "")
            return {"reply": f"{aname} je {atype} na naši kmetiji." if atype else f"{aname} je žival na naši kmetiji."}
        # No specific name — score persons by token overlap with message
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
            return {"reply": _format_person(best_person, show_phone=_want_phone)}
        # List all family members as fallback
        lines = ["Domačijo Kovačnik vodi družina Štern:"]
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
        # Photos / gallery queries
        if any(kw in msg_l for kw in ("fotograf", "galerij", "slika", "slik")):
            website = CONTACT.get("website", "www.kovacnik.si")
            return {"reply": f"Fotografije sob si oglejte na spletni strani: {website}"}
        # Large group / capacity check (misclassified restaurant queries)
        _m_grp = re.search(r"\b(\d{2,})\s*oseb", msg_l)
        if _m_grp and int(_m_grp.group(1)) > 20:
            return {
                "reply": (
                    f"Za večje skupine ({_m_grp.group(1)} oseb) pokličite nas neposredno na 031 330 113 — "
                    "skupaj bomo uredili mize in meni po vaših željah."
                )
            }
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
        lines = ["Imamo tri sobe, vsaka poimenovana po enem od naših otrok:"]
        for rdata in ROOMS.values():
            rname = rdata["name"]
            cap = rdata.get("capacity", "")
            price = rdata.get("price_per_person_eur", "")
            feats = ", ".join(rdata.get("features", [])[:3])
            lines.append(f"  • {rname}: {cap} osebe, {price} EUR/osebo/noč — {feats}")
        lines.append("\nV ceno je vključen zajtrk. Prijava ob 14:00, odjava ob 10:00.")
        return {"reply": "\n".join(lines)}

    if intent == "INFO_WINE":
        sparkling = WINES.get("sparkling") or []
        white = WINES.get("white") or []
        red = WINES.get("red") or []

        _msg_norm = _normalize_text(message)
        _msg_words = set(re.findall(r"[a-z0-9]+", _msg_norm))

        # Check if user asked about a specific wine — match by token overlap.
        _all_wines = (
            [("Peneča", w) for w in sparkling]
            + [("Bela", w) for w in white]
            + [("Rdeča", w) for w in red]
        )
        _best_score = 0
        _best: tuple | None = None
        for _cat, _w in _all_wines:
            _wine_words = set(re.findall(r"[a-z0-9]+", _normalize_text(_w.get("name", ""))))
            _score = len(_msg_words & _wine_words)
            if _score > _best_score:
                _best_score = _score
                _best = (_cat, _w)
        if _best_score >= 2 and _best:
            _cat, _w = _best
            _lines = [f"{_w['name']} ({_w.get('type', '')}) — {_cat} vino"]
            if _w.get("grape"):
                _lines.append(f"Sorta: {_w['grape']}")
            if _w.get("price"):
                _lines.append(f"Cena: {_w['price']:.0f} EUR")
            if _w.get("desc"):
                _lines.append(f"Opis: {_w['desc']}")
            return {"reply": "\n".join(_lines)}

        # Category filter: only show the requested category if specified.
        _want_sparkling = any(kw in _msg_norm for kw in ("penec", "penin", "sparkling", "prosec", "cava", "frizant"))
        _want_white = any(kw in _msg_norm for kw in ("bela", "belo", "beli"))
        _want_red = any(kw in _msg_norm for kw in ("rdec", "rdeca", "rdece", "rdeci"))

        parts: list[str] = []
        if _want_sparkling and not _want_white and not _want_red:
            if sparkling:
                names = [f"{w['name']} ({w.get('type', '')})" for w in sparkling]
                parts.append("Peneča vina: " + ", ".join(names))
            else:
                return {"reply": "Peneča vina trenutno nimamo na karti."}
        elif _want_white and not _want_red and not _want_sparkling:
            if white:
                names = [f"{w['name']} ({w.get('type', '')})" for w in white]
                parts.append("Bela vina: " + ", ".join(names))
            else:
                return {"reply": "Belih vin trenutno nimamo na karti."}
        elif _want_red and not _want_white and not _want_sparkling:
            if red:
                names = [f"{w['name']} ({w.get('type', '')})" for w in red]
                parts.append("Rdeča vina: " + ", ".join(names))
            else:
                return {"reply": "Rdečih vin trenutno nimamo na karti."}
        else:
            # No specific category or multiple — show full list.
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
            return {"reply": "Naša vinska karta:\n" + "\n".join(parts)}
        return {"reply": "Žal nimam aktualnih podatkov o vinski karti."}

    if intent in ("INFO_MENU", "INFO_MENU_DETAIL"):
        msg_lower = (message or "").lower()

        # --- Last arrival / closing time redirects (misclassified from INFO_HOURS) ---
        if any(kw in msg_lower for kw in ("zadnji prihod", "zadnji čas", "do kdaj", "kdaj je zadnji", "do katere ure")):
            return {"reply": "Zadnji prihod na kosilo je ob 15:00. Svetujemo, da pridete čim prej, saj se mize zapolnijo hitro."}

        # --- Minimum people for degustation ---
        if any(kw in msg_lower for kw in ("koliko oseb", "minimalno oseb", "min oseb", "vsaj oseb", "min. oseb")) and \
           any(kw in msg_lower for kw in ("degustat", "degustacij", "teden", "hodni")):
            rules = WEEKDAY_DEGUSTATION.get("rules", {})
            min_p = rules.get("min_people", 6)
            return {"reply": f"Za tedensko degustacijo je minimalno {min_p} oseb. Rezervacija obvezna: 031 330 113"}

        # --- Večerja pri sobah (misclassified as INFO_MENU) ---
        if any(kw in msg_lower for kw in ("večerja", "večerjo", "večer")) and \
           not any(kw in msg_lower for kw in ("meni", "menij", "degust", "hodni", "kosilo")):
            return {"reply": "Večerja je na voljo po naročilu: 25 EUR na osebo. Prijavite se ob rezervaciji ali dan prej."}

        # --- Aktivnosti / outdoor / produkti misclassified as INFO_MENU ---
        if any(kw in msg_lower for kw in ("liker", "žganje", "bunka", "sirek", "sirček", "salama", "marmelad", "pridelk", "nakup", "prodaj")):
            phone = CONTACT.get("mobile", "031 330 113")
            return {
                "reply": (
                    "Naši domači izdelki:\n"
                    "  • Pohorska bunka (sušeno meso)\n"
                    "  • Hišna suha salama\n"
                    "  • Frešerjev zorjen sirček\n"
                    "  • Domači liker\n"
                    "  • Marmelade in namazi\n"
                    f"Za nakup pokličite Barbaro: {phone}"
                )
            }
        if any(kw in msg_lower for kw in ("kolesarj", "koles", "pohod", "aktivnost", "poletne", "poletj", "zimske", "letne", "izlet")) and \
           not any(kw in msg_lower for kw in ("kosilo", "meni", "vikend", "degust", "hodni")):
            return {
                "reply": (
                    "Aktivnosti v okolici kmetije:\n"
                    "  • Pohodništvo po Pohorju in slap Skalca\n"
                    "  • Kolesarjenje (izposoja po dogovoru)\n"
                    "  • Jahanje na ponijih\n"
                    "  • Smučišče Areh in Mariborsko Pohorje (25–35 min)\n"
                    "  • Terme Zreče (30–40 min)"
                )
            }

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
        if any(kw in msg_lower for kw in ("teden", "tedenski", "tednom", "degustat", "degustacij", "sreda", "četrtek", "cetrtek", "petek", "hodni")):
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

    if intent == "INFO_PRICING":
        msg_l = (message or "").lower()
        # Large group inquiry misclassified as INFO_PRICING
        _m_grp_p = re.search(r"\b(\d{2,})\s*oseb", msg_l)
        if _m_grp_p and int(_m_grp_p.group(1)) > 20:
            return {
                "reply": (
                    f"Za večje skupine ({_m_grp_p.group(1)} oseb) pokličite nas neposredno na 031 330 113 — "
                    "skupaj bomo uredili mize in meni po vaših željah."
                )
            }
        # Menu price query → redirect to menu pricing
        if any(kw in msg_l for kw in ("meni", "kosilo", "vikend", "teden", "degustat", "degustacij", "hodni")):
            return {
                "reply": (
                    "Cene menijev na Domačiji Kovačnik:\n"
                    "  • Vikend kosilo (sob/ned): 36 EUR/odrasli, otroci 4–12 let -50%\n"
                    "  • 4-hodni degustacijski meni: 36 EUR (+15 EUR vinska degustacija)\n"
                    "  • 5-hodni: 43 EUR (+20 EUR)\n"
                    "  • 6-hodni: 53 EUR (+25 EUR)\n"
                    "  • 7-hodni: 62 EUR (+29 EUR)\n"
                    "Za rezervacijo: 031 330 113"
                )
            }
        # Room/accommodation price query
        price = next(iter(ROOMS.values()), {}).get("price_per_person_eur", 50)
        return {
            "reply": (
                f"Nastanitev na Domačiji Kovačnik:\n"
                f"  • Cena: {price} EUR na osebo/noč (z zajtrkom)\n"
                f"  • Otroci do 5 let: brezplačno\n"
                f"  • Otroci 5–12 let: 50% popust\n"
                f"  • Minimalno 3 nočitve (junij–avgust), 2 nočitvi (ostale mesece)\n"
                f"  • Večerja: 25 EUR/osebo (po naročilu)\n"
                f"Za rezervacijo: 031 330 113"
            )
        }

    if intent == "INFO_ANIMAL":
        # Check if user is asking about bringing pets (not about our farm animals).
        msg_l = (message or "").lower()
        _pet_keywords = ("ljubljenč", "hišn", "dovoljeni", "dovoljen", "prepovedan", "pripelj", "prines")
        _pet_animals = ("pes", "psa", "psi", "psov", "mačk", "mucek")
        _is_pet_question = any(kw in msg_l for kw in _pet_keywords) or (
            any(kw in msg_l for kw in _pet_animals) and any(kw in msg_l for kw in ("dovol", "prepo", "sme", "lahko"))
        )
        if _is_pet_question:
            return {
                "reply": (
                    "Žal hišnih ljubljenčkov pri nas ne sprejemamo.\n"
                    "Če vas zanimajo živali na naši kmetiji, jih ob obisku z veseljem pokažemo! "
                    "Na kmetiji imamo konjička Malajko in Marsija, pujsko Pepo, ovčka Čarlija, "
                    "psičko Luno in še mnogo več."
                )
            }
        if any(kw in msg_l for kw in ("ljubljenč", "hišn")):
            return {
                "reply": (
                    "Žal hišnih ljubljenčkov pri nas ne sprejemamo.\n"
                    "Če vas zanimajo živali na naši kmetiji, jih ob obisku z veseljem pokažemo! "
                    "Na kmetiji imamo konjička Malajko in Marsija, pujsko Pepo, ovčka Čarlija, "
                    "psičko Luno in še mnogo več."
                )
            }
        # Check for a specific animal in the message
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
        # "Which person cares for animals?" queries misclassified as INFO_ANIMAL
        if any(kw in msg_l for kw in ("katera oseba", "kdo skrbi", "kdo hranj", "kdo pazi", "kdo se ukvarja")):
            msg_tokens = set(t for t in re.findall(r"[a-zšžčćđ]+", msg_l) if len(t) >= 4)
            best_score, best_person = 0, None
            for pdata in PERSONS.values():
                notes_str = " ".join(str(n) for n in (pdata.get("notes") or [])).lower()
                role_str = (pdata.get("role") or "").lower()
                name_str = (pdata.get("name") or "").lower()
                combined = f"{name_str} {role_str} {notes_str}"
                score = sum(1 for tok in msg_tokens if tok in combined)
                if score > best_score:
                    best_score, best_person = score, pdata
            if best_score > 0 and best_person:
                return {"reply": _format_person(best_person)}
        # Animation/activities queries misclassified as INFO_ANIMAL
        if any(kw in msg_l for kw in ("animacij", "animator", "aktivnost za otroke")):
            julija = PERSONS.get("julija", {})
            return {
                "reply": (
                    "Animatorske aktivnosti za otroke vodi naša hči Julija — skrbi za živali in animira otroke. "
                    "Aktivnosti: jahanje na ponijih Malajka in Marsi, hranjenje živali, kmečka opravila."
                )
            }
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

    if intent == "INFO_HOURS":
        msg_l = (message or "").lower()
        # Breakfast / dinner time — MUST be first
        if any(kw in msg_l for kw in ("zajtrk", "zajtrka", "zajutrkovat")):
            return {"reply": "Zajtrk postrežemo med 8:00 in 10:00 zjutraj, v jedilnici ali na balkonu."}
        if any(kw in msg_l for kw in ("večerja", "večerjo", "večer")):
            # "ob ponedeljkih/torkih" with evening query → closed
            if any(kw in msg_l for kw in ("ponedelj", "torek")):  # ponedeljek / ponedeljkih etc.
                return {
                    "reply": (
                        "Ob ponedeljkih in torkih smo zaprti. "
                        "Večerje so na voljo od srede do nedelje, po naročilu: 031 330 113"
                    )
                }
            return {"reply": "Večerja je na voljo po naročilu: 18:00–20:00. Prijavite se vnaprej: 031 330 113"}
        # Last arrival for lunch — MUST come before generic "prihod" check
        if any(kw in msg_l for kw in ("zadnji prihod", "zadnji čas", "kdaj je zadnji", "do katere ure pridemo")):
            return {"reply": "Zadnji prihod na kosilo je ob 15:00. Svetujemo, da pridete čim prej."}
        # Kosila med tednom misclassified as INFO_HOURS
        if any(kw in msg_l for kw in ("med tednom", "sreda", "četrtek", "petek")) and \
           any(kw in msg_l for kw in ("kosilo", "jemo", "kosila", "degust")):
            return {
                "reply": (
                    "Med tednom (sreda–petek) strežemo degustacijske menije po predhodni rezervaciji, "
                    "minimalno 6 oseb. Ob sobotah in nedeljah vikend kosila od 12:00 naprej.\n"
                    "Za rezervacijo: 031 330 113"
                )
            }
        # Check-in / check-out
        if any(kw in msg_l for kw in ("check-out", "check out", "odjava", "odhod", "do kdaj moram")):
            if any(kw in msg_l for kw in ("pozn", "kasn", "podaljš", "flexibl", "dogovor")):
                return {"reply": "Standardni check-out je do 10:00. Podaljšanje je možno po dogovoru: 031 330 113"}
            return {"reply": "Check-out je do 10:00. Prosimo, da nas pravočasno obvestite o morebitnih zamudah."}
        if any(kw in msg_l for kw in ("check-in", "check in", "prijava", "kdaj pridem", "od kdaj")):
            if any(kw in msg_l for kw in ("pozn", "kasn", "flexibl", "dogovor", "zuna", "zgodn")):
                return {"reply": "Check-in je od 14:00 naprej. Za zgodnji ali pozni dogovor pokličite: 031 330 113"}
            return {"reply": "Check-in je od 14:00 naprej. V primeru kasnejšega prihoda nas predhodno obvestite."}
        # Early check-in / late check-out
        if any(kw in msg_l for kw in ("zgodnji", "zgodaj", "earlier", "early")):
            return {"reply": "Zgodnji check-in je možen po dogovoru. Pokličite nas: 031 330 113"}
        # Mon/Tue closed
        if any(kw in msg_l for kw in ("ponedeljek", "torek", "kdaj ste zaprti", "kdaj zaprti")):
            return {
                "reply": (
                    "Restavracija je zaprta ob ponedeljkih in torkih. "
                    "Kosila strežemo od srede do nedelje (sob/ned 12:00–21:00, sre–pet po rezervaciji). "
                    "Sobe so na voljo od srede do nedelje."
                )
            }
        # General opening hours
        if any(kw in msg_l for kw in ("ura", "delovni čas", "kdaj", "odprt", "odpri", "ure", "kdaj delate")):
            return {
                "reply": (
                    "Delovni čas Domačije Kovačnik:\n"
                    "  • Restavracija: sob–ned 12:00–21:00, med tednom po rezervaciji\n"
                    "  • Zaprto: ponedeljek in torek\n"
                    "  • Sobe: sreda–nedelja (check-in od 14:00, check-out do 10:00)\n"
                    "Za rezervacije: 031 330 113"
                )
            }
        # Fallback hours response
        return {
            "reply": (
                "Restavracija deluje ob sobotah in nedeljah (12:00–21:00), "
                "med tednom po predhodni rezervaciji. "
                "Zaprto ob ponedeljkih in torkih. Za info: 031 330 113"
            )
        }

    if intent == "INFO_GENERAL":
        msg_l = (message or "").lower()
        farm_name = CONTACT.get("name", "Domačija Kovačnik")
        phone = CONTACT.get("mobile", "031 330 113")
        # Contact info queries misclassified as INFO_GENERAL
        if any(kw in msg_l for kw in ("email", "e-pošt", "e-mail", "mail")):
            email = CONTACT.get("email", "info@kovacnik.si")
            return {"reply": f"Naš e-naslov: {email}"}
        if any(kw in msg_l for kw in ("spletna stran", "spletno stran", "spletni", "www", "website", "fotograf")):
            website = CONTACT.get("website", "www.kovacnik.si")
            return {"reply": f"Spletna stran: {website}"}
        if any(kw in msg_l for kw in ("telefonsk", "telefon", "pokliči", "klic", "tel.", "po telefonu", "telefonsk")):
            return {"reply": f"Pokličite nas na: {phone}"}
        # Darilni boni / paketi
        if any(kw in msg_l for kw in ("daril", "darilo", "bon", "voucher", "paket", "poklono")):
            return {
                "reply": (
                    "Darilne bone in pakete nudimo po dogovoru — idealen darilo za obisk kmetije, "
                    "degustacijo ali vikend kosilo. Pokličite Barbaro: " + phone
                )
            }
        # "All family members" queries misclassified as INFO_GENERAL
        if any(kw in msg_l for kw in ("vsi člani", "vso druz", "vsi v druz", "vsa druz", "celotna druz", "kdo so vsi", "vsem druz")) or \
           (any(kw in msg_l for kw in ("druzin", "familia", "familij")) and any(kw in msg_l for kw in ("vsi", "vsa", "vsem", "vseh", "kdo so", "kdo so v", "o vaš", "o naš", "povejt"))):
            lines = ["Domačijo Kovačnik vodi družina Štern:"]
            for pdata in PERSONS.values():
                lines.append(f"  • {_format_person(pdata)}")
            return {"reply": "\n".join(lines)}
        # Min people for degustacija (misclassified as INFO_GENERAL)
        if any(kw in msg_l for kw in ("koliko oseb", "minimalno oseb", "min oseb", "vsaj oseb")) and \
           any(kw in msg_l for kw in ("degustat", "degustacij")):
            rules = WEEKDAY_DEGUSTATION.get("rules", {})
            min_p = rules.get("min_people", 6)
            return {"reply": f"Za tedensko degustacijo je minimalno {min_p} oseb. Rezervacija obvezna: 031 330 113"}
        # Animal queries misclassified as INFO_GENERAL → delegate to ANIMAL logic
        if any(kw in msg_l for kw in ("živali", "živaĺi", "zivali", "konjič", "konjiček", "pujsk", "psič", "mucke", "ovca", "govedo")):
            names = [v.get("name") for v in ANIMALS.values() if v.get("name")]
            if names:
                return {"reply": "Na kmetiji imamo: " + ", ".join(names) + "."}
        # Large group inquiry
        _m_group = re.search(r"\b(\d{2,})\s*oseb", msg_l)
        if _m_group and int(_m_group.group(1)) > 20:
            return {
                "reply": (
                    f"Za večje skupine ({_m_group.group(1)} oseb) pokličite nas neposredno "
                    "na 031 330 113 — skupaj bomo uredili prostor, mize in meni po vaših željah."
                )
            }
        # Hours / closing days misclassified as INFO_GENERAL
        if any(kw in msg_l for kw in ("ponedeljek", "torek", "kdaj zaprt", "kdaj odprt", "delovni čas", "ure")):
            return {
                "reply": (
                    "Restavracija je zaprta ob ponedeljkih in torkih. "
                    "Kosila strežemo od srede do nedelje. "
                    "Sobe so na voljo od srede do nedelje (check-in od 14:00)."
                )
            }
        # Early/late check-in/out misclassified
        if any(kw in msg_l for kw in ("check-in", "check in", "check-out", "check out", "odjava", "prijava")):
            if any(kw in msg_l for kw in ("pozn", "zgodn", "kasn", "flexibl")):
                return {"reply": "Zgodnji check-in / pozni check-out je možen po dogovoru. Pokličite: 031 330 113"}
        # Parking
        if any(kw in msg_l for kw in ("parking", "parkirišč", "parkir", "avto")):
            return {"reply": "Seveda — imamo brezplačno parkirišče kar ob hiši, dovolj prostora za 10+ avtov."}
        # WiFi (general, outside room context)
        if any(kw in msg_l for kw in ("wifi", "wi-fi", "brezžičn", "internet")):
            return {"reply": "WiFi je brezplačno na voljo v vseh sobah in skupnih prostorih."}
        # Shipping / delivery queries
        if any(kw in msg_l for kw in ("po pošti", "pošilj", "dostav", "dostavit", "naroč po")):
            return {"reply": f"Domačih izdelkov po pošti žal ne pošiljamo, so pa na voljo ob obisku kmetije. Za naročilo po dogovoru pokličite Barbaro: {phone}"}
        # Domači izdelki / shop
        if any(kw in msg_l for kw in ("domač", "salama", "bunk", "marmelad", "sirek", "liker", "pridelk", "nakup", "trgovin", "prodaj")):
            return {
                "reply": (
                    "Z veseljem! Naši domači izdelki:\n"
                    "  • Pohorska bunka (sušeno meso)\n"
                    "  • Hišna suha salama\n"
                    "  • Frešerjev zorjen sirček\n"
                    "  • Domači namazi (bučni, zeliščni)\n"
                    "  • Marmelade in kompoti\n"
                    "  • Hišni liker\n"
                    f"Za nakup pokličite Barbaro: {phone}"
                )
            }
        # Skiing / Areh / Mariborsko Pohorje / winter activities (incl. "pozimi")
        if any(kw in msg_l for kw in ("smučišč", "smucišč", "smuc", "smuč", "areh", "mariborsko pohorje", "ski", "skijaš", "sneg", "žičnič", "zicnic", "zimsk", "pozim")):
            return {
                "reply": (
                    "Najbližji smučišči sta Mariborsko Pohorje in Areh — od nas je do obeh nekje 25–35 minut vožnje.\n"
                    "Odlična izbira za poldnevni ali celodnevni izlet med bivanjem pri nas. "
                    "Če potrebujete nasvet o pristopu ali kje je manj gneče, vam z veseljem povemo."
                )
            }
        # Terme / spa / sauna
        if any(kw in msg_l for kw in ("terme", "toplice", "spa", "wellness", "sauna", "savna", "savno")):
            return {
                "reply": (
                    "Najbližje terme so Terme Zreče in Terme Ptuj — od nas jih dosežete v 30–40 minutah.\n"
                    "Lepa kombinacija: dopoldne Pohorje, popoldne terme. 😊"
                )
            }
        # Summer / seasonal activities
        if any(kw in msg_l for kw in ("poletne", "letne", "sezon")) and \
           any(kw in msg_l for kw in ("aktivnost", "počet", "počitek", "ponudb", "prij")):
            return {
                "reply": (
                    "Poletne aktivnosti pri Kovačniku:\n"
                    "  • Jahanje na ponijih Malajka in Marsi\n"
                    "  • Pohodi in kolesarjenje po Pohorju\n"
                    "  • Ogled in hranjenje živali\n"
                    "  • Animacijske aktivnosti za otroke (Julija)\n"
                    "  • Slap Skalca — kratki sprehod\n"
                    "  • Vikend kosila in degustacijski meniji"
                )
            }
        # Nature / hiking / cycling / walks
        if any(kw in msg_l for kw in ("pohod", "izlet", "sprehod", "narav", "gozd", "pot", "slap", "skalc", "kolesarj", "koles")):
            return {
                "reply": (
                    "Okolica je res lepa za izlete! Tukaj je, kaj priporočamo:\n"
                    "  • Sprehodi in pohodi po Pohorju — gozdne poti, razgledne točke\n"
                    "  • Slap Skalca — prijeten sprehod ob potočku, v bližini\n"
                    "  • Kolesarjenje (izposoja koles možna po dogovoru)\n"
                    "Za konkretne predloge glede na čas in kondicijo nam kar povejte!"
                )
            }
        # Animation / animatorske aktivnosti
        if any(kw in msg_l for kw in ("animacij", "animator", "animira")):
            return {
                "reply": (
                    "Animatorske aktivnosti za otroke vodi naša hči Julija — jahanje na ponijih, "
                    "hranjenje živali, kmečka opravila in igre v naravi."
                )
            }
        # Aktivnosti
        if any(kw in msg_l for kw in ("aktivnost", "počet", "jahanj", "poni", "ogled", "doživetj", "počitek")):
            return {
                "reply": (
                    "Pri nas je vedno kaj za početi:\n"
                    "  • Jahanje na ponijih Malajka in Marsi\n"
                    "  • Ogled in hranjenje živali (pujska Pepa, ovca Čarli, psička Luna...)\n"
                    "  • Pohodi in kolesarjenje po Pohorju\n"
                    "  • Ogled kmečkih opravil\n"
                    "  • Animatorske aktivnosti za otroke\n"
                    f"Pokličite nas za kakšen nasvet: {phone}"
                )
            }
        # Children / family friendly
        if any(kw in msg_l for kw in ("otrok", "otroci", "druzin", "primern", "mlad")):
            return {
                "reply": (
                    "Domačija Kovačnik je prava domačija za družine! "
                    "Otroci se imajo pri nas res lepo — igrajo se z živalmi, jahajo na ponijih Malajka in Marsi, "
                    "spoznajo kmečko življenje in so v naravi. "
                    "V vikend meniju otroci (4–12 let) plačajo le polovično ceno. "
                    f"Za rezervacijo pokličite: {phone}"
                )
            }
        # General farm info / name
        return {
            "reply": (
                f"Dobrodošli na {farm_name}! "
                "Smo turistična kmetija na pohorski strani, nad Framom — mirno, naravno, domače.\n"
                f"Naslov: {CONTACT.get('address', 'Planica 9, 2313 Fram')}\n"
                "Ponujamo: vikend kosila, tedenski degustacijski meniji, nastanitev v sobah (z zajtrkom), "
                "domači izdelki, jahanje, ogled živali.\n"
                f"Za vse informacije: {phone}"
            )
        }

    # INFO_LOCATION: handle outdoor/nearby locations before falling to v2.
    if intent == "INFO_LOCATION":
        msg_l = (message or "").lower()
        phone = CONTACT.get("mobile", "031 330 113")
        phone2 = CONTACT.get("phone", "02 603 6033")
        email = CONTACT.get("email", "info@kovacnik.si")
        website = CONTACT.get("website", "www.kovacnik.si")
        # Large group inquiry misclassified as INFO_LOCATION
        _m_grp_l = re.search(r"\b(\d{2,})\s*oseb", msg_l)
        if _m_grp_l and int(_m_grp_l.group(1)) > 20:
            return {
                "reply": (
                    f"Za večje skupine ({_m_grp_l.group(1)} oseb) pokličite nas neposredno na {phone} — "
                    "skupaj bomo uredili mize in meni po vaših željah."
                )
            }
        # Contact info misclassified as INFO_LOCATION
        if any(kw in msg_l for kw in ("telefonsk", "telefon", "pokliči", "klic", "tel.")):
            return {"reply": f"Pokličete nas na: {phone} (Barbara) ali {phone2}"}
        if any(kw in msg_l for kw in ("email", "e-pošt", "e-mail", "mail")):
            return {"reply": f"Naš e-naslov: {email}"}
        if any(kw in msg_l for kw in ("spletna stran", "spletno stran", "spletni", "www", "website", "fotograf")):
            return {"reply": f"Spletna stran: {website}"}
        # Parking
        if any(kw in msg_l for kw in ("parking", "parkirišč", "parkir")):
            return {"reply": "Seveda — imamo brezplačno parkirišče kar ob hiši, dovolj prostora za 10+ avtov."}
        if any(kw in msg_l for kw in ("smučišč", "smucišč", "smuc", "smuč", "areh", "mariborsko pohorje", "ski", "sneg", "žičnič", "zicnic")):
            return {
                "reply": (
                    "Najbližji smučišči sta Mariborsko Pohorje in Areh — od nas je do obeh nekje 25–35 minut vožnje.\n"
                    "Odlična izbira za poldnevni ali celodnevni izlet med bivanjem pri nas."
                )
            }
        if any(kw in msg_l for kw in ("terme", "toplice", "spa", "wellness", "sauna", "savna", "savno")):
            return {
                "reply": "Najbližje terme so Terme Zreče in Terme Ptuj — od nas jih dosežete v 30–40 minutah."
            }
        if any(kw in msg_l for kw in ("pohod", "slap", "skalc", "izlet", "gozd", "kolesarj", "koles", "narav", "pot")):
            return {
                "reply": (
                    "V okolici je lepo za izlete:\n"
                    "  • Pohodi in sprehodi po Pohorju — gozdne poti, razgledne točke\n"
                    "  • Slap Skalca — prijeten sprehod ob potočku\n"
                    "  • Kolesarjenje (izposoja koles možna po dogovoru)\n"
                    f"Za konkretne predloge nas pokličite: {phone}"
                )
            }
        if any(kw in msg_l for kw in ("aktivnost", "počet", "jahanj", "poni", "animacij", "animator")):
            return {
                "reply": (
                    "Pri nas je vedno kaj za početi:\n"
                    "  • Jahanje na ponijih Malajka in Marsi\n"
                    "  • Ogled in hranjenje živali\n"
                    "  • Pohodi in kolesarjenje po Pohorju\n"
                    "  • Animatorske aktivnosti za otroke (vodi Julija)\n"
                    f"Za rezervacijo: {phone}"
                )
            }
        # Products / shop queries misclassified as INFO_LOCATION
        if any(kw in msg_l for kw in ("kupim", "kupiti", "kupit", "nakup", "prodaja", "pridelk", "domač", "liker", "bunka", "sirek")):
            return {
                "reply": (
                    "Domače izdelke (bunka, salama, sirček, liker, marmelade) kupite pri nas ob obisku kmetije. "
                    f"Za naročilo vnaprej pokličite Barbaro: {phone}"
                )
            }
        # Default: farm location
        return {
            "reply": (
                f"Nahajamo se na naslovu {CONTACT.get('address', 'Planica 9, 2313 Fram')} — "
                "na pohorski strani, nad Framom. Iz avtoceste A1 izvoz Fram, nato cca. 15 min.\n"
                f"Koordinate: {CONTACT.get('coordinates', '46.5234, 15.6123')}"
            )
        }

    # Fallback to existing v2 info flow for remaining INFO intents.
    return {"reply": info_flow.handle(message, brand, session)}
