#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 20
DEFAULT_SLEEP = 0.25
USER_AGENT = "KovacnikAIBot/2.0 (+https://kovacnik.com)"

SLO_WORDS = {
    "kmetija", "domacija", "doma", "soba", "sobe", "rezervacija", "kosilo", "jedilnik",
    "ponudba", "otroci", "odrasli", "cena", "kontakt", "lokacija", "odpiralni", "cas",
    "vecerja", "zajtrk", "pohorje", "kovacnik", "zivali", "vin", "kmetiji",
}
EN_WORDS = {"the", "and", "for", "with", "book", "booking", "room", "rooms", "price", "contact", "location", "hours", "menu"}
DE_WORDS = {"und", "der", "die", "das", "fur", "mit", "zimmer", "buchen", "kontakt", "lage", "offnungszeiten", "angebot", "menu"}


@dataclass
class Record:
    url: str
    title: str
    content: str
    lang: str
    topic: str
    entity_type: str
    entity_name: str
    priority: int
    fetched_at: str

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "lang": self.lang,
            "topic": self.topic,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "priority": self.priority,
            "fetched_at": self.fetched_at,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-zCScszZz0-9]+", text.lower()))


def detect_lang(url: str, title: str, content: str) -> str:
    lu = url.lower()
    if any(m in lu for m in ("/de/", "lang=de", "_de", "-de")):
        return "de"
    if any(m in lu for m in ("/en/", "lang=en", "_en", "-en")):
        return "en"

    text = f"{title} {content}".lower()
    tokens = _tokenize(text)
    sl = len(tokens & SLO_WORDS)
    en = len(tokens & EN_WORDS)
    de = len(tokens & DE_WORDS)

    if sl >= 2 and sl >= en and sl >= de:
        return "sl"
    if de >= 2 and de > sl:
        return "de"
    if en >= 2 and en > sl:
        return "en"
    if any(ch in text for ch in "csz"):
        return "sl"
    return "unknown"


def classify(url: str, title: str, content: str) -> tuple[str, str, str, int]:
    u = url.lower()
    t = title.lower()
    txt = f"{t} {content[:600].lower()}"

    if "kontakt" in u or "kontakt" in t:
        return ("contact", "contact", "kontakt", 100)
    if "odpiralni" in u or "urnik" in u:
        return ("hours", "policy", "odpiralni_cas", 95)
    if "soba" in u or "namestitev" in u:
        m = re.search(r"soba\s+([a-z0-9]+)", t)
        name = m.group(1).upper() if m else "sobe"
        return ("rooms", "room", name, 90)
    if "zival" in u or "otroci" in u or "poni" in txt:
        return ("animals", "farm", "zivali", 90)
    if "jedil" in u or "meni" in txt or "kosilo" in txt:
        return ("menu", "menu", "ponudba", 85)
    if "vino" in txt or "penin" in txt:
        return ("wine", "wine", "vina", 85)
    if "zgodovin" in u or "zgodovin" in t:
        return ("history", "history", "zgodovina", 70)
    if "kmetij" in u:
        return ("farm", "farm", "kmetija", 75)
    return ("general", "general", "splosno", 60)


def extract_main_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "form", "iframe"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = _normalize_ws(title_tag.get_text(" ")) if title_tag else ""

    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "p", "li"]):
        line = _normalize_ws(el.get_text(" "))
        if len(line) < 20:
            continue
        if line.lower().startswith(("cookies", "piškot", "copyright")):
            continue
        lines.append(line)

    # dedupe nearby duplicates
    deduped: list[str] = []
    seen = set()
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)

    return title, "\n".join(deduped)


def content_chunks(text: str, max_chars: int = 1200) -> str:
    parts = [p.strip() for p in text.split("\n") if p.strip()]
    out: list[str] = []
    buf = ""
    for p in parts:
        cand = p if not buf else f"{buf} {p}"
        if len(cand) > max_chars:
            if buf:
                out.append(buf)
            buf = p
        else:
            buf = cand
    if buf:
        out.append(buf)
    return "\n".join(out)


def load_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.urls:
        urls.extend(args.urls)
    if args.urls_file:
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    # unique preserve order
    seen = set()
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def fetch(session: requests.Session, url: str, timeout: int) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def build(
    urls: Iterable[str],
    only_sl: bool,
    timeout: int,
    sleep_s: float,
    min_chars: int,
) -> tuple[list[Record], Counter]:
    stats = Counter()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    rows: list[Record] = []
    fp_seen = set()

    for idx, url in enumerate(urls, start=1):
        stats["total_urls"] += 1
        try:
            html = fetch(session, url, timeout)
            title, text = extract_main_text(html)
            text = content_chunks(text)
            if not text:
                stats["empty_text"] += 1
                continue
            if len(text) < min_chars:
                stats["skip_short"] += 1
                continue
            lang = detect_lang(url, title, text)
            if only_sl and lang != "sl":
                stats[f"skip_lang_{lang}"] += 1
                continue

            topic, entity_type, entity_name, priority = classify(url, title, text)
            rec = Record(
                url=url,
                title=title or urlparse(url).path.strip("/") or url,
                content=text,
                lang=lang,
                topic=topic,
                entity_type=entity_type,
                entity_name=entity_name,
                priority=priority,
                fetched_at=_now_iso(),
            )
            fp = hashlib.sha1(f"{rec.url}|{rec.title}|{rec.content}".encode("utf-8")).hexdigest()
            if fp in fp_seen:
                stats["deduped"] += 1
                continue
            fp_seen.add(fp)
            rows.append(rec)
            stats["kept"] += 1
            print(f"[{idx}] OK {url} ({topic}/{lang})")
        except Exception as exc:
            stats["errors"] += 1
            print(f"[{idx}] ERR {url}: {exc}")
        time.sleep(sleep_s)

    return rows, stats


def write_jsonl(path: Path, rows: list[Record]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Scrape URLs and build chatbot-ready knowledge JSONL.")
    p.add_argument("--urls", nargs="*", help="Inline URLs")
    p.add_argument("--urls-file", help="Text file with one URL per line")
    p.add_argument("--output", default="knowledge.cleaned.jsonl")
    p.add_argument("--only-sl", action="store_true", help="Keep only Slovenian records")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    p.add_argument("--min-chars", type=int, default=60, help="Skip records with content shorter than this")
    args = p.parse_args()

    urls = load_urls(args)
    if not urls:
        raise SystemExit("No URLs provided. Use --urls or --urls-file.")

    rows, stats = build(
        urls,
        only_sl=args.only_sl,
        timeout=args.timeout,
        sleep_s=args.sleep,
        min_chars=args.min_chars,
    )
    out = Path(args.output).resolve()
    write_jsonl(out, rows)

    print("\nBuild summary")
    print(f"- output: {out}")
    for k in sorted(stats):
        print(f"- {k}: {stats[k]}")


if __name__ == "__main__":
    main()
