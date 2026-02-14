#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REQUIRED = ("url", "title", "content")


def normalize_name(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def load_records(path: Path) -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    stats = Counter()
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            raw = line.strip()
            if not raw:
                stats["empty_line"] += 1
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                stats["json_error"] += 1
                continue
            rec["_line"] = line_no
            rows.append(rec)
            stats["loaded"] += 1
    return rows, stats


def validate(rows: list[dict[str, Any]]) -> tuple[Counter, list[str]]:
    stats = Counter()
    issues: list[str] = []

    by_url_title: dict[tuple[str, str], set[str]] = defaultdict(set)
    names_by_type: dict[str, set[str]] = defaultdict(set)
    types_by_name: dict[str, set[str]] = defaultdict(set)

    for rec in rows:
        line = rec.get("_line")
        for key in REQUIRED:
            if not str(rec.get(key, "")).strip():
                stats["missing_required"] += 1
                issues.append(f"line {line}: missing required field '{key}'")

        url = str(rec.get("url", "")).strip()
        title = str(rec.get("title", "")).strip()
        content = str(rec.get("content", "")).strip()
        lang = str(rec.get("lang", "unknown")).strip().lower()
        entity_type = str(rec.get("entity_type", "unknown")).strip().lower()
        entity_name = normalize_name(str(rec.get("entity_name", "")))

        if lang in {"de", "en"}:
            stats["non_sl"] += 1
            issues.append(f"line {line}: non-sl language '{lang}' in {url}")

        if len(content) < 40:
            stats["too_short"] += 1
            issues.append(f"line {line}: content too short")

        by_url_title[(url, title)].add(content)

        if entity_name:
            names_by_type[entity_type].add(entity_name)
            types_by_name[entity_name].add(entity_type)

    for (url, title), variants in by_url_title.items():
        if len(variants) > 1:
            stats["conflict_url_title"] += 1
            issues.append(f"conflict: same url+title with different content -> {url} | {title}")

    # ambiguous names across multiple entity types (e.g. "aljaz" person+room)
    for name, type_set in types_by_name.items():
        if len(type_set) > 1:
            stats["ambiguous_entity_name"] += 1
            issues.append(f"ambiguous entity_name '{name}' used by types: {sorted(type_set)}")

    stats["unique_entity_names"] = len(types_by_name)
    stats["unique_url_title"] = len(by_url_title)
    return stats, issues


def main() -> None:
    p = argparse.ArgumentParser(description="Validate chatbot knowledge JSONL quality.")
    p.add_argument("--input", default="knowledge.cleaned.jsonl")
    p.add_argument("--strict", action="store_true", help="Exit non-zero on any issue")
    p.add_argument("--max-issues", type=int, default=30)
    args = p.parse_args()

    path = Path(args.input).resolve()
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")

    rows, load_stats = load_records(path)
    val_stats, issues = validate(rows)

    print("Validation summary")
    print(f"- file: {path}")
    for k in sorted(load_stats):
        print(f"- {k}: {load_stats[k]}")
    for k in sorted(val_stats):
        print(f"- {k}: {val_stats[k]}")

    if issues:
        print("\nTop issues:")
        for msg in issues[: args.max_issues]:
            print(f"- {msg}")

    if args.strict and issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
