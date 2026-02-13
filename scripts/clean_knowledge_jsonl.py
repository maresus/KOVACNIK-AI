#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SLO_WORDS = {
    "in", "je", "za", "na", "pri", "od", "do", "ali", "lahko", "smo", "ste",
    "vas", "vam", "kmetija", "domačija", "domacija", "soba", "rezervacija",
    "kosilo", "jedilnik", "ponudba", "otroci", "odrasli", "cena", "kontakt",
    "lokacija", "odpiralni", "čas", "cas", "večerja", "vecerja", "zajtrk",
    "pohorje", "kovačnik", "kovacnik",
}

EN_WORDS = {
    "the", "and", "for", "with", "book", "booking", "room", "rooms", "stay",
    "price", "contact", "location", "hours", "menu", "weekend", "offer",
}

DE_WORDS = {
    "und", "der", "die", "das", "für", "mit", "zimmer", "buchen", "kontakt",
    "lage", "öffnungszeiten", "angebot", "menü", "wochenende", "preise",
}


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZčšžćđČŠŽĆĐ]+", text.lower()))


def detect_lang(record: dict[str, Any]) -> str:
    url = str(record.get("url", "")).lower()
    title = str(record.get("title", ""))
    content = str(record.get("content", ""))
    text = f"{title}\n{content}".lower()
    tokens = tokenize(text)

    # URL hint wins for explicit language paths.
    if any(marker in url for marker in ["/de/", "lang=de", "_de", "-de"]):
        return "de"
    if any(marker in url for marker in ["/en/", "lang=en", "_en", "-en"]):
        return "en"

    sl_score = len(tokens & SLO_WORDS)
    en_score = len(tokens & EN_WORDS)
    de_score = len(tokens & DE_WORDS)

    if sl_score >= 2 and sl_score >= en_score and sl_score >= de_score:
        return "si"
    if de_score >= 2 and de_score > sl_score:
        return "de"
    if en_score >= 2 and en_score > sl_score:
        return "en"

    # Slovenian diacritics are a strong positive signal.
    if any(ch in text for ch in "čšž"):
        return "si"

    return "unknown"


def clean_knowledge(input_path: Path, output_path: Path, keep_unknown: bool) -> Counter:
    stats = Counter()
    kept: list[str] = []

    with input_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stats["total"] += 1
            raw = line.strip()
            if not raw:
                stats["removed_empty"] += 1
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                stats["removed_json_error"] += 1
                continue

            lang = detect_lang(rec)
            stats[f"lang_{lang}"] += 1

            if lang == "si" or (lang == "unknown" and keep_unknown):
                kept.append(json.dumps(rec, ensure_ascii=False))
                stats["kept"] += 1
            elif lang == "de":
                stats["removed_de"] += 1
            elif lang == "en":
                stats["removed_en"] += 1
            else:
                stats["removed_unknown"] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(kept))
        if kept:
            fh.write("\n")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean knowledge.jsonl and keep Slovenian records only.")
    parser.add_argument("--input", default="knowledge.jsonl", help="Input JSONL path")
    parser.add_argument("--output", default="knowledge.cleaned.jsonl", help="Output JSONL path")
    parser.add_argument("--in-place", action="store_true", help="Replace input file in place (creates backup)")
    parser.add_argument("--keep-unknown", action="store_true", help="Keep records with unknown language")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file does not exist: {input_path}")

    if args.in_place:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = input_path.with_suffix(input_path.suffix + f".bak_{stamp}")
        backup_path.write_text(input_path.read_text(encoding="utf-8"), encoding="utf-8")
        output_path = input_path
    else:
        output_path = Path(args.output).resolve()

    stats = clean_knowledge(input_path=input_path, output_path=output_path, keep_unknown=args.keep_unknown)

    print("Knowledge cleanup stats")
    print(f"- input: {input_path}")
    print(f"- output: {output_path}")
    if args.in_place:
        print("- mode: in-place (backup created)")
    print(f"- total: {stats['total']}")
    print(f"- kept: {stats['kept']}")
    print(f"- removed_de: {stats['removed_de']}")
    print(f"- removed_en: {stats['removed_en']}")
    print(f"- removed_unknown: {stats['removed_unknown']}")
    print(f"- removed_empty: {stats['removed_empty']}")
    print(f"- removed_json_error: {stats['removed_json_error']}")
    print(
        f"- detected languages: si={stats['lang_si']}, de={stats['lang_de']}, "
        f"en={stats['lang_en']}, unknown={stats['lang_unknown']}"
    )


if __name__ == "__main__":
    main()
