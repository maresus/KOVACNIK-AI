from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from app.core.llm_client import get_llm_client

BASE_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_PATH = BASE_DIR / "knowledge.jsonl"


@dataclass
class KnowledgeChunk:
    url: str
    title: str
    paragraph: str


IMPORTANT_TERMS = (
    "jahanje",
    "jahamo",
    "ponij",
    "bunka",
    "marmelad",
    "salama",
    "klobasa",
    "liker",
)


def _split_into_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []
    for raw in normalized.split("\n"):
        chunk = raw.strip()
        if not chunk:
            continue
        lowered = chunk.lower()
        # kratke vrstice obdržimo, če imajo pomembne izraze (jahanje, bunka, salama …)
        if len(chunk) < 40 and not any(term in lowered for term in IMPORTANT_TERMS):
            continue
        paragraphs.append(chunk)
    return paragraphs


def load_knowledge_chunks() -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    if not KNOWLEDGE_PATH.exists():
        print(f"[knowledge_base] Datoteka {KNOWLEDGE_PATH} ne obstaja. Vračam prazen seznam.")
        return chunks

    with KNOWLEDGE_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = record.get("url", "") or ""
            title = record.get("title", "") or ""
            content = record.get("content", "") or ""
            if not (url or title or content):
                continue
            for paragraph in _split_into_paragraphs(content):
                chunks.append(KnowledgeChunk(url=url, title=title, paragraph=paragraph))

    print(f"[knowledge_base] Naloženih {len(chunks)} odstavkov")
    return chunks


KNOWLEDGE_CHUNKS: List[KnowledgeChunk] = load_knowledge_chunks()

CONTACT = {
    "phone": "+386 41 123 456",
    "email": "info@kovacnik.com",
}


def _tokenize(text: str) -> Set[str]:
    lowered = text.lower()
    cleaned = re.sub(r"[^\w]+", " ", lowered)
    return {token for token in cleaned.split() if len(token) >= 3}


def _score_chunk(tokens: Set[str], chunk: KnowledgeChunk) -> float:
    paragraph_tokens = _tokenize(chunk.paragraph)
    if not paragraph_tokens:
        return 0.0
    title_tokens = _tokenize(chunk.title)
    overlap_para = len(tokens & paragraph_tokens)
    overlap_title = len(tokens & title_tokens)
    return overlap_para + 0.5 * overlap_title


def search_knowledge(query: str, top_k: int = 5) -> list[KnowledgeChunk]:
    tokens = _tokenize(query)
    if not tokens:
        return []
    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk in KNOWLEDGE_CHUNKS:
        score = _score_chunk(tokens, chunk)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


KEYWORD_RULES = {
    "salama": ["salama", "salamo", "salame", "klobasa", "klobaso", "mesni izdelki", "klobase"],
    "bunka": ["bunka", "bunko", "bunke", "pohorska bunka"],
    "marmelada": ["marmelada", "marmelado", "marmelade", "marmeldo", "džem", "namaz", "marmelad"],
    "liker": ["liker", "likerje", "žganje", "žganja", "tepkovec"],
    "jahanje": ["jahanje", "jahati", "jahamo", "poni", "ponij", "ponija", "ponijem"],
    "nočitev": ["nočitev", "nočitve", "noči"],
    "kosilo": ["vikend kosilo", "degustacijski", "degustacijo", "kosilo"],
}


def _collect_focus_terms(question: str) -> list[str]:
    lowered = question.lower()
    focus: list[str] = []
    for patterns in KEYWORD_RULES.values():
        if any(term in lowered for term in patterns):
            focus.extend(patterns)
    if not focus:
        focus.extend(IMPORTANT_TERMS)
    return list({term for term in focus if len(term) >= 3})


def _trim_content(content: str, focus_terms: list[str]) -> str:
    if len(content) <= 700:
        return content
    content_lower = content.lower()
    for term in focus_terms:
        idx = content_lower.find(term)
        if idx != -1:
            start = max(0, idx - 200)
            end = min(len(content), idx + 500)
            snippet = content[start:end]
            start_dot = snippet.find(". ")
            if start > 0 and start_dot != -1:
                snippet = snippet[start_dot + 1 :]
            return snippet.strip()
    snippet = content[:700]
    last_dot = snippet.rfind(".")
    if last_dot > 200:
        snippet = snippet[: last_dot + 1]
    return snippet


def _build_context_snippet(question: str, paragraphs: List[KnowledgeChunk]) -> str:
    focus_terms = _collect_focus_terms(question)
    parts: list[str] = []
    for chunk in paragraphs:
        lines: list[str] = []
        if chunk.title:
            lines.append(f"Naslov: {chunk.title}")
        if chunk.url:
            lines.append(f"URL: {chunk.url}")
        content = _trim_content(chunk.paragraph.strip(), focus_terms)
        lines.append(f"Vsebina: {content}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def _keyword_chunks(question: str, limit: int = 6) -> list[KnowledgeChunk]:
    lowered = question.lower()
    selected: list[KnowledgeChunk] = []
    seen = set()
    for keyword, patterns in KEYWORD_RULES.items():
        if any(term in lowered for term in patterns):
            for chunk in KNOWLEDGE_CHUNKS:
                chunk_text = f"{chunk.title.lower()} {chunk.paragraph.lower()} {chunk.url.lower()}"
                if any(term in chunk_text for term in patterns):
                    key = (chunk.url, chunk.paragraph[:80])
                    if key not in seen:
                        selected.append(chunk)
                        seen.add(key)
                        if len(selected) >= limit:
                            return selected
            if len(selected) >= limit:
                break
    return selected


def _gather_relevant_chunks(question: str, base_top_k: int = 6) -> list[KnowledgeChunk]:
    lowered = question.lower()
    is_bunka = any(word in lowered for word in ["bunka", "bunko", "bunke"])
    is_salama = any(
        word in lowered for word in ["salama", "salamo", "salame", "klobasa", "klobase", "klobaso"]
    )
    is_marmelada = any(word in lowered for word in ["marmelad", "marmelado", "marmelade", "marmeldo", "džem"])
    is_jahanje = any(
        word in lowered for word in ["jahanje", "jahati", "jahamo", "poni", "ponij", "ponija", "ponijem"]
    )

    # mesnine (bunka / salama)
    if is_bunka or is_salama:
        chunks = [
            chunk
            for chunk in KNOWLEDGE_CHUNKS
            if "/izdelek/" in chunk.url.lower()
            and (
                "bunka" in chunk.title.lower()
                or "bunka" in chunk.paragraph.lower()
                or "salama" in chunk.title.lower()
                or "salama" in chunk.paragraph.lower()
                or "mesni izdelki" in chunk.paragraph.lower()
            )
        ]
        return chunks[:4]

    # marmelade
    if is_marmelada:
        chunks = [
            chunk
            for chunk in KNOWLEDGE_CHUNKS
            if "/marmelada" in chunk.url.lower()
            or "marmelad" in chunk.title.lower()
            or "kategorija: marmelade" in chunk.paragraph.lower()
        ]
        return chunks[:4]

    # jahanje / poni – če ni v bazi, dodamo ročni fallback
    if is_jahanje:
        chunks = [
            chunk
            for chunk in KNOWLEDGE_CHUNKS
            if "jahanje" in chunk.paragraph.lower() or "ponij" in chunk.paragraph.lower()
        ]
        if chunks:
            return chunks[:4]
        return [
            KnowledgeChunk(
                url="https://kovacnik.com/cenik/",
                title="Jahanje s ponijem",
                paragraph="Jahanje s ponijem / 1 krog – 5,00 € (glej cenik Domačija Kovačnik).",
            )
        ]

    keyword_chunks = _keyword_chunks(question, limit=4)
    base_chunks = search_knowledge(question, top_k=base_top_k)

    combined: list[KnowledgeChunk] = []
    seen = set()
    for chunk in keyword_chunks + base_chunks:
        key = (chunk.url, chunk.paragraph[:80])
        if key in seen:
            continue
        combined.append(chunk)
        seen.add(key)
        if len(combined) >= base_top_k + len(keyword_chunks):
            break
    return combined


def _filter_chunks_by_category(question: str, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    lowered = question.lower()

    # mesnine: bunka / salama / klobasa
    if any(word in lowered for word in ["bunka", "bunko", "salama", "klobasa", "mesni"]):
        filtered = [
            c
            for c in chunks
            if "mesni izdelki" in c.paragraph.lower()
            or "kategorija: mesni" in c.paragraph.lower()
            or "bunka" in c.paragraph.lower()
            or "salama" in c.paragraph.lower()
        ]
        if filtered:
            return filtered[:4]
        fallback = [
            c
            for c in KNOWLEDGE_CHUNKS
            if "mesni izdelki" in c.paragraph.lower()
            or "bunka" in c.paragraph.lower()
            or "salama" in c.paragraph.lower()
        ]
        return fallback[:3]

    # marmelade
    if any(word in lowered for word in ["marmelad", "džem"]):
        filtered = [c for c in chunks if "/marmelada" in c.url.lower()]
        if filtered:
            return filtered
        for chunk in KNOWLEDGE_CHUNKS:
            if "/marmelada" in chunk.url.lower():
                return [chunk]
        return chunks

    # likerji / žganje
    if any(word in lowered for word in ["liker", "žganj", "žganje"]):
        filtered = [
            c
            for c in chunks
            if any(token in c.url.lower() for token in ["liker", "žganje", "tepkovec"])
        ]
        if filtered:
            return filtered
        for chunk in KNOWLEDGE_CHUNKS:
            if any(token in chunk.url.lower() for token in ["liker", "žganje", "tepkovec"]):
                return [chunk]
        return chunks

    return chunks


SYSTEM_PROMPT = """
Ti si pogovorni AI asistent za Domačijo Kovačnik (turistična kmetija na Pohorju). Namenjen si gostom, ki sprašujejo po ponudbi, rezervacijah in turističnih možnostih v okolici.

SLOG IN TON:
- Odgovarjaj toplo, prijazno in naravno, kot človek, ki dobro pozna kmetijo.
- Goste vikaš (vi), stavki naj bodo kratki in razumljivi.
- Pri podobnih vprašanjih NE ponavljaj istega odgovora beseda za besedo – spremeni vsaj uvod ali strukturo (npr. drug začetek stavka, drugačen vrstni red alinej).

RAZMIŠLJANJE IN PODVPRAŠANJA:
- Najprej poskusi razumeti namen vprašanja (vino, marmelade, mesnine, dejavnosti, rezervacije, družinske aktivnosti …).
- Če je vprašanje preveč splošno ali nejasno (npr. "katera rdeča še?", "še kaj?", "kaj pa še?"), naredi ENO od naslednjega:
  - postavi ENO kratko podvprašanje ("Ali iščete rdeče vino, ki je bolj suho ali bolj polsladko?"), ALI
  - na podlagi konteksta sam ponudi nekaj najbolj smiselnjih možnosti (npr. nekaj rdečih vin iz seznama).
- Pri nadaljevanjih, kot so "katera rdeča še?", "še katere marmelade?", "še kaj drugega?", predpostavi, da se gost sklicuje na isto temo, ki jo vidiš v kontekstu (npr. vina, marmelade, mesnine), in tako tudi odgovori.

UPORABA BAZE ZNANJA:
- Odgovarjaj IZKLJUČNO na podlagi posredovanega konteksta (odstavki iz knowledge.jsonl).
- Če v kontekstu najdeš konkretne izdelke, jedilnike, cene ali storitve, jih raje na kratko povzemaj, kot da pošiljaš gosta na spletno stran.
- Če v kontekstu ni nič uporabnega za dano vprašanje, iskreno povej, da v teh podatkih tega nimaš, in ŠELE TAKRAT predlagaj, da pogleda na kovacnik.com ali da kontaktira domačijo.

STRUKTURA ODGOVOROV:
- Odgovor naj bo kratek in pregleden: največ 3–4 kratki odstavki ali 1 odstavek + kratek seznam.
- Pri produktih (marmelade, mesnine, likerji, vina) uporabi tipično strukturo:
  1. Kratek uvod (1–2 stavka), kjer potrdiš, da to ponujate, in dodaš en stavek občutka ("to gostje zelo radi izberejo", "to je naša klasika").
  2. Nato 1–5 alinej z izdelki v obliki: ime – kratek opis – okvirna cena – povezava (če je v kontekstu).
  3. Zaključek z vabilom: npr. "Če mi poveste, ali imate raje sladko ali bolj suho, vam z veseljem še kaj predlagam."
- Pri splošnih vprašanjih (npr. "kaj lahko delamo na kmetiji", "katera vina ponujate", "kaj ponujate za vikend kosila") daj:
  - kratek, jasen povzetek,
  - po želji idejo ali dva (npr. izlet, aktivnost za otroke), če je to podprto s kontekstom.

OMEJITVE IN POŠTENOST:
- Nikoli si ne izmišljuj novih izdelkov, cen ali storitev, ki niso v kontekstu.
- Če ne najdeš nič relevantnega, ne odgovarjaj suhoparno v stilu "V bazi podatkov nimamo podatkov". Raje povej nekaj v smislu:
  - "V teh podatkih tega nimam zapisanega, zato tukaj ne morem odgovoriti čisto natančno."
- Ne dodajaj stavka "Več na www.kovacnik.com" pri vsakem odgovoru. To omeni samo, če res ne najdeš ničesar ali če gost izrecno vpraša za povezavo.
"""


def generate_llm_answer(question: str, top_k: int = 6, history: list[dict[str, str]] | None = None) -> str:
    try:
        paragraphs = _gather_relevant_chunks(question, base_top_k=top_k)
        paragraphs = _filter_chunks_by_category(question, paragraphs)
    except Exception:
        paragraphs = []

    if not paragraphs:
        context_text = (
            "Za to vprašanje v bazi znanja trenutno ni najdenih relevantnih informacij."
        )
    else:
        context_text = _build_context_snippet(question, paragraphs)

    client = get_llm_client()
    convo: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "developer", "content": f"Kontekst iz baze znanja Kovačnik:\n{context_text}"},
    ]
    if history:
        # vzamemo zadnjih nekaj sporočil, da ohranimo kratko zgodovino
        convo.extend(history[-6:])
    convo.append({"role": "user", "content": f"Vprašanje gosta: {question}"})

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=convo,
        max_output_tokens=400,
        temperature=0.7,
        top_p=0.9,
    )

    answer = getattr(response, "output_text", None)
    if not answer:
        outputs = []
        for block in getattr(response, "output", []) or []:
            for content in getattr(block, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    outputs.append(text)
        answer = "\n".join(outputs).strip()

    return answer or (
        "Trenutno v podatkih ne najdem jasnega odgovora. Prosimo, preverite www.kovacnik.com."
    )
