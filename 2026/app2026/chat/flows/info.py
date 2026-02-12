from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from app.rag.knowledge_base import search_knowledge_scored


SEMANTIC_THRESHOLD = 0.68
SEMANTIC_STOPWORDS = {
    "a", "ali", "al", "pa", "in", "na", "za", "se", "so", "je", "smo", "ste",
    "sem", "biti", "bo", "bi", "da", "ne", "ni", "niso", "si", "mi", "ti",
    "vi", "vas", "vam", "nas", "ga", "jo", "jih", "te", "to", "ta", "tisto",
    "kdo", "kaj", "kdaj", "kje", "kako", "kolik", "koliko", "ker", "pač",
    "pri", "od", "do", "v", "iz", "z", "ob", "kot", "naj", "tudi", "lahko",
    "moj", "moja", "moje", "tvoj", "tvoja", "tvoje", "njihov", "njihova",
    "the", "and", "or", "to", "is", "are", "a", "an", "for", "in", "of",
}


def handle(message: str, brand: Any, session: Any | None = None) -> str:
    # 1) Hard truth from structured brand config (priority over generic canned replies)
    hard = _hard_info(message, brand)
    if hard:
        return _apply_style(message, _cleanup_info_text(hard), session)

    # 2) Generic brand responses
    key = detect_info_key(message, brand)
    if key:
        responses = getattr(brand, "INFO_RESPONSES", {})
        if isinstance(responses, dict) and key in responses:
            return _apply_style(message, _cleanup_info_text(str(responses[key])), session)

    # 3) RAG fallback (light)
    rag = _semantic_info_answer(message)
    if rag:
        return _apply_style(message, _cleanup_info_text(rag), session)

    # 4) Unknown
    return "Za to nimam podatka."


def _apply_style(message: str, text: str, session: Any | None) -> str:
    if not session or not text or text.startswith("Za to nimam podatka."):
        return text

    lowered = (message or "").lower()
    if any(token in lowered for token in ["točen", "tocen", "natančen", "natancen", "celoten", "celotni"]):
        return text

    if any(k in lowered for k in ["jedil", "meni", "kosil", "ponudb"]):
        topic = "menu"
    elif any(k in lowered for k in ["vino", "vina", "vinska", "penin"]):
        topic = "wine"
    elif any(k in lowered for k in ["žival", "zival", "pes", "mačk", "poni"]):
        topic = "animals"
    else:
        topic = "generic"

    intros = {
        "menu": [
            "Seveda.",
            "Z veseljem.",
            "Jasno.",
            "Odlično vprašanje.",
        ],
        "wine": [
            "Seveda, z veseljem.",
            "Super vprašanje.",
            "Jasno.",
            "Z veseljem.",
        ],
        "animals": [
            "Seveda.",
            "Z veseljem pojasnim.",
            "Jasno.",
            "Seveda, z veseljem.",
        ],
        "generic": [
            "Seveda.",
            "Z veseljem.",
            "Odlično vprašanje.",
            "Jasno.",
        ],
    }

    outros = {
        "menu": [
            "Če želite, dodam še predlog pijače k meniju.",
            "Če želite, vam takoj pripravim še rezervacijo mize.",
            "Lahko dodam še predlog za otroke ali brezmesno različico.",
        ],
        "wine": [
            "Če želite, priporočim vino glede na izbrano jed.",
            "Lahko pripravim tudi izbor po cenovnem razredu.",
            "Če želite, dodam še predlog za aperitiv.",
        ],
        "animals": [
            "Če želite, povem še katere živali so najpogosteje na ogled.",
            "Lahko dodam še priporočilo, kdaj je obisk z otroki najbolj zanimiv.",
        ],
        "generic": [
            "Če želite, nadaljujeva še z rezervacijo.",
            "Lahko dodam še bolj konkretne podatke za vaš termin.",
        ],
    }

    templates = (
        "{intro}\n{text}",
        "{text}\n{outro}",
        "{intro}\n{text}\n{outro}",
        "{text}",
    )

    style_state = session.data.setdefault("style_state", {})
    counters = style_state.setdefault("info_counter_by_topic", {})
    counter = int(counters.get(topic, 0))
    intro_list = intros.get(topic, intros["generic"])
    outro_list = outros.get(topic, outros["generic"])
    template = templates[counter % len(templates)]
    intro = intro_list[counter % len(intro_list)]
    outro = outro_list[counter % len(outro_list)]
    rendered = template.format(intro=intro, text=text, outro=outro).strip()

    last_by_topic = style_state.setdefault("last_info_reply_by_topic", {})
    if rendered == last_by_topic.get(topic):
        counter += 1
        template = templates[counter % len(templates)]
        intro = intro_list[counter % len(intro_list)]
        outro = outro_list[counter % len(outro_list)]
        rendered = template.format(intro=intro, text=text, outro=outro).strip()

    counters[topic] = counter + 1
    last_by_topic[topic] = rendered
    return rendered


def _cleanup_info_text(text: str) -> str:
    # UI renders plain text, so strip markdown emphasis markers.
    return (text or "").replace("**", "").strip()


def detect_info_key(message: str, brand: Any) -> Optional[str]:
    text = (message or "").lower().strip()
    responses = getattr(brand, "INFO_RESPONSES", {}) or {}

    if any(w in text for w in ["čez teden", "cez teden", "med tednom", "tedenska ponudba", "tedenski meni"]):
        return "jedilnik" if "jedilnik" in responses else None

    if any(w in text for w in ["kako ste", "kako si", "kako gre", "kako vam gre", "kako vam grejo stvari"]):
        return "smalltalk" if "smalltalk" in responses else None
    if any(w in text for w in ["kdaj ste odprti", "odpiralni", "delovni čas", "kdaj odprete"]):
        return "odpiralni_cas" if "odpiralni_cas" in responses else None
    if "zajtrk" in text and "večerj" not in text:
        return "zajtrk" if "zajtrk" in responses else None
    if any(w in text for w in ["koliko stane večerja", "cena večerje", "večerja", "vecerja", "večerjo"]):
        return "vecerja" if "vecerja" in responses else None
    if any(
        w in text
        for w in [
            "cena sobe",
            "cena nočit",
            "cena nocit",
            "koliko stane noč",
            "koliko stane noc",
            "cenik",
            "koliko stane soba",
            "koliko stane nočitev",
        ]
    ):
        return "cena_sobe" if "cena_sobe" in responses else None
    if any(w in text for w in ["koliko sob", "kakšne sobe", "koliko oseb v sobo", "kolko oseb v sobo", "kapaciteta sob"]):
        return "sobe" if "sobe" in responses else None
    if "klim" in text:
        return "klima" if "klima" in responses else None
    if "wifi" in text or "wi-fi" in text or "internet" in text:
        return "wifi" if "wifi" in responses else None
    if any(w in text for w in ["prijava", "odjava", "check in", "check out"]):
        return "prijava_odjava" if "prijava_odjava" in responses else None
    if any(w in text for w in ["parkir", "parking"]):
        return "parking" if "parking" in responses else None
    if re.search(r"(?<!\w)(pes|psa|psi|psov|kuž|kuz|dog)(?!\w)", text) or any(
        w in text for w in ["mačk", "žival", "ljubljenč"]
    ):
        return "zivali" if "zivali" in responses else None
    if any(w in text for w in ["plačilo", "kartic", "gotovina"]):
        return "placilo" if "placilo" in responses else None
    if any(w in text for w in ["kontakt", "telefon", "telefonsko", "številka", "stevilka", "gsm", "mobitel", "mobile", "phone"]):
        return "kontakt" if "kontakt" in responses else None
    if any(w in text for w in ["email", "e-mail", "epošta", "e-pošta", "mail"]):
        return "kontakt" if "kontakt" in responses else None
    if any(
        w in text
        for w in [
            "kje ste",
            "kje se nahajate",
            "naslov",
            "lokacija",
            "kje ste doma",
            "kje ste locirani",
            "kako pridem",
            "kako pridem do vas",
            "kako pridem do domačije",
            "kako pridem do kmetije",
            "navodila za pot",
        ]
    ):
        return "lokacija" if "lokacija" in responses else None
    if any(w in text for w in ["minimal", "najmanj noči", "najmanj nočitev", "min nočitev"]):
        return "min_nocitve" if "min_nocitve" in responses else None
    if any(w in text for w in ["koliko miz", "kapaciteta"]):
        return "kapaciteta_mize" if "kapaciteta_mize" in responses else None
    if any(w in text for w in ["alergij", "gluten", "lakto", "vegan"]):
        return "alergije" if "alergije" in responses else None
    if any(w in text for w in ["vino", "vina", "vinsko", "vinska", "wine", "wein", "vinci"]):
        return "vina" if "vina" in responses else None
    if any(w in text for w in ["smučišče", "smucisce", "smučanje", "smucanje", "ski"]):
        return "smucisce" if "smucisce" in responses else None
    if any(w in text for w in ["terme", "termal", "spa", "wellness"]):
        return "terme" if "terme" in responses else None
    if any(
        w in text
        for w in [
            "izlet",
            "izleti",
            "znamenitost",
            "naravne",
            "narava",
            "pohod",
            "pohodni",
            "okolici",
            "bližini",
            "pohorje",
            "slap",
            "jezero",
            "vintgar",
            "razgled",
            "bistriški",
            "ščrno jezero",
            "šumik",
        ]
    ):
        return "turizem" if "turizem" in responses else None
    if any(w in text for w in ["kolo", "koles", "kolesar", "bike", "e-kolo", "ekolo", "bicikl"]):
        return "kolesa" if "kolesa" in responses else None
    if "skalca" in text or ("slap" in text and "skalc" in text):
        return "skalca" if "skalca" in responses else None
    if "darilni bon" in text or ("bon" in text and "daril" in text):
        return "darilni_boni" if "darilni_boni" in responses else None
    if ("vikend" in text or "ponudba" in text) and any(
        w in text for w in ["vikend", "ponudba", "kosilo", "meni", "menu", "jedil"]
    ):
        return "jedilnik" if "jedilnik" in responses else None
    if any(
        w in text
        for w in [
            "jedilnik",
            "jedilnk",
            "jedilnku",
            "jedlnik",
            "meni",
            "menij",
            "meniju",
            "menu",
            "kaj imate za jest",
            "kaj imate za kosilo",
            "kaj ponujate",
            "kaj strežete",
            "kaj je za kosilo",
            "kaj je za večerjo",
            "kaj je za vecerjo",
            "koslo",
        ]
    ):
        return "jedilnik" if "jedilnik" in responses else None
    if any(w in text for w in ["zadnji prihod", "zadnji prihod na kosilo"]):
        return "odpiralni_cas" if "odpiralni_cas" in responses else None
    if any(w in text for w in ["družin", "druzina", "druzino"]):
        return "druzina" if "druzina" in responses else None
    if "kmetij" in text or "kmetijo" in text:
        return "kmetija" if "kmetija" in responses else None
    if "gibanic" in text:
        if any(tok in text for tok in ["kaj je", "pohorska gibanica", "kaj pomeni"]) and "imate" not in text:
            return "gibanica" if "gibanica" in responses else None
        return None
    if "priporoč" in text or "priporoc" in text:
        return "priporocilo" if "priporocilo" in responses else None
    return None


def _hard_info(message: str, brand: Any) -> Optional[str]:
    lowered = message.lower()
    farm_info = getattr(brand, "FARM_INFO", {})
    if not farm_info:
        return None

    seasonal_menus = getattr(brand, "SEASONAL_MENUS", []) or []
    weekly_menus = getattr(brand, "WEEKLY_MENUS", {}) or {}
    weekly_info = getattr(brand, "WEEKLY_INFO", {}) or {}
    wine_list = getattr(brand, "WINE_LIST", {}) or {}
    wine_keywords = set(getattr(brand, "WINE_KEYWORDS", set()) or set())

    month_map = {
        "januar": 1,
        "februar": 2,
        "marec": 3,
        "april": 4,
        "maj": 5,
        "junij": 6,
        "julij": 7,
        "avgust": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "december": 12,
    }

    def _find_menu_by_month(month_num: int) -> Optional[dict]:
        for entry in seasonal_menus:
            months = set(entry.get("months") or set())
            if month_num in months:
                return entry
        return None

    # Tedenski degustacijski (4-7 hodni) meni
    h_match = re.search(r"([4-7])\s*[- ]?\s*hod", lowered)
    if h_match:
        h_count = int(h_match.group(1))
        menu = weekly_menus.get(h_count)
        if not menu:
            return None

        def _format_course_line(idx: int, dish: str, wine: Optional[str]) -> str:
            if wine:
                return f"{idx}. {dish}\n   Vino: {wine}"
            return f"{idx}. {dish}"

        def _glass_word(n: int) -> str:
            if n % 100 in {2, 3, 4} and n % 100 not in {12, 13, 14}:
                return "kozarci"
            if n % 10 == 1 and n % 100 != 11:
                return "kozarec"
            return "kozarcev"

        lines = [f"{menu.get('name', f'{h_count}-hodni meni')}"]
        courses = [c for c in (menu.get("courses", []) or []) if (c or {}).get("dish")]
        if courses and "pozdrav iz kuhinje" in courses[0].get("dish", "").lower():
            welcome = courses[0]
            w_wine = welcome.get("wine")
            lines.append("")
            lines.append("Dobrodošlica:")
            lines.append(f"- {welcome.get('dish')}")
            if w_wine:
                lines.append(f"  Vino: {w_wine}")
            courses = courses[1:]

        lines.append("")
        lines.append("Hodi:")
        for i, course in enumerate(courses, start=1):
            lines.append(_format_course_line(i, course.get("dish", "").strip(), course.get("wine")))

        lines.append("")
        lines.append(f"Cena: {menu.get('price')} EUR / odrasla oseba.")
        if menu.get("wine_pairing"):
            glasses = int(menu.get("wine_glasses") or 0)
            lines.append(
                f"Vinska spremljava: {menu.get('wine_pairing')} EUR ({glasses} {_glass_word(glasses)})."
            )
        return "\n".join(lines)

    # Med tednom: degustacijski meniji 4-7 hodov
    is_weekly_question = any(
        token in lowered
        for token in [
            "čez teden",
            "cez teden",
            "med tednom",
            "tedenska ponudba",
            "tedenski meni",
        ]
    )
    if is_weekly_question and weekly_menus:
        ordered = sorted((k, v) for k, v in weekly_menus.items() if isinstance(k, int))
        lines = ["Med tednom ponujamo degustacijske menije za skupine:"]
        for count, menu in ordered:
            price = menu.get("price")
            lines.append(f"- {count}-hodni meni: {price} EUR / osebo")
        if weekly_info:
            days = weekly_info.get("days", "")
            min_people = weekly_info.get("min_people", "")
            time_txt = str(weekly_info.get("time", "")).strip()
            lines.append(
                f"Termin: {days}, za skupine {min_people}+ oseb, {time_txt}."
            )
        lines.append("Če želite, pošljem točen 4-, 5-, 6- ali 7-hodni meni.")
        return "\n".join(lines)

    # Vikend / sezonski jedilnik po mesecih
    is_menu_question = any(
        token in lowered
        for token in [
            "vikend",
            "kosilo",
            "jedilnik",
            "meni",
            "ponudb",
        ]
    )
    if is_menu_question and seasonal_menus:
        asked_month = None
        for month_name, month_num in month_map.items():
            if month_name in lowered:
                asked_month = month_num
                break
        if asked_month is None:
            asked_month = datetime.now().month

        seasonal = _find_menu_by_month(asked_month)
        if seasonal:
            lines = [f"{seasonal.get('label', 'Sezonski jedilnik')}:"] + list(
                seasonal.get("items", [])
            )
            return "\n".join(lines)

    # Vina (konkreten izbor iz konfiguracije)
    if any(word in lowered for word in wine_keywords):
        picks = []
        for section in ["penece", "bela", "rdeca"]:
            for wine in wine_list.get(section, [])[:2]:
                name = wine.get("name", "").strip()
                wtype = wine.get("type", "").strip()
                price = wine.get("price")
                if not name:
                    continue
                suffix = f" – {wtype}" if wtype else ""
                price_part = f" ({price:.2f} EUR)" if isinstance(price, (int, float)) else ""
                picks.append(f"- {name}{suffix}{price_part}")
        if picks:
            return (
                "Ponujamo izbor lokalnih vin iz okolice Pohorja:\n"
                + "\n".join(picks[:6])
                + "\nČe želite, priporočim vino glede na jed."
            )

    if any(word in lowered for word in ["telefon", "številka", "stevilka", "kontakt", "email", "mail"]):
        phone = farm_info.get("phone", "")
        mobile = farm_info.get("mobile", "")
        email = farm_info.get("email", "")
        return f"Kontakt: {phone}, {mobile}, {email}".strip().strip(",")

    if any(word in lowered for word in ["naslov", "lokacija", "kje", "nahajate"]):
        return f"Nahajamo se na: {farm_info.get('address', '')}."

    if any(word in lowered for word in ["odprti", "odpiralni", "urnik", "kdaj", "ura", "delovni čas"]):
        opening = farm_info.get("opening_hours", {})
        return (
            f"Kosila: {opening.get('restaurant', '')} | "
            f"Sobe: {opening.get('rooms', '')} | "
            f"Trgovina: {opening.get('shop', '')} | "
            f"Zaprto: {opening.get('closed', '')}"
        ).strip()

    return None


def _semantic_info_answer(question: str) -> Optional[str]:
    scored = search_knowledge_scored(question, top_k=1)
    if not scored:
        return None
    score, chunk = scored[0]
    if score < SEMANTIC_THRESHOLD:
        return None
    if not _semantic_overlap_ok(question, chunk):
        return None
    return _format_semantic_snippet(chunk)


def _format_semantic_snippet(chunk: Any) -> str:
    snippet = (chunk.paragraph or "").strip()
    if len(snippet) > 500:
        snippet = snippet[:500].rsplit(". ", 1)[0] + "."
    url_line = f"\n\nVeč: {chunk.url}" if chunk.url else ""
    return f"{snippet}{url_line}"


def _semantic_overlap_ok(question: str, chunk: Any) -> bool:
    q_tokens = _tokenize_text(question)
    if not q_tokens:
        return True
    c_tokens = _tokenize_text(f"{chunk.title or ''} {chunk.paragraph or ''}")
    overlap = q_tokens & c_tokens
    if len(q_tokens) >= 6:
        return len(overlap) >= 2 and (len(overlap) / len(q_tokens)) >= 0.25
    return len(overlap) >= 2 or (len(overlap) / len(q_tokens)) >= 0.5


def _tokenize_text(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-zČŠŽčšžĐđĆć0-9]+", (text or "").lower())
    return {t for t in tokens if len(t) >= 3 and t not in SEMANTIC_STOPWORDS}
