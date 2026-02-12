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


def handle(message: str, brand: Any) -> str:
    # 1) Hard truth from brand config
    key = detect_info_key(message, brand)
    if key:
        responses = getattr(brand, "INFO_RESPONSES", {})
        if isinstance(responses, dict) and key in responses:
            return _cleanup_info_text(str(responses[key]))
    hard = _hard_info(message, brand)
    if hard:
        return _cleanup_info_text(hard)

    # 2) RAG fallback (light)
    rag = _semantic_info_answer(message)
    if rag:
        return _cleanup_info_text(rag)

    # 3) Unknown
    return "Za to nimam podatka."


def _cleanup_info_text(text: str) -> str:
    # UI renders plain text, so strip markdown emphasis markers.
    return (text or "").replace("**", "").strip()


def detect_info_key(message: str, brand: Any) -> Optional[str]:
    text = (message or "").lower().strip()
    responses = getattr(brand, "INFO_RESPONSES", {}) or {}

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
