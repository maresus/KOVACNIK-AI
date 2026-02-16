#!/usr/bin/env python3
"""Live interaktivni chat za Kovačnik AI V3.

Zagon:
    PYTHONPATH=. python scripts/chat_live.py
    PYTHONPATH=. python scripts/chat_live.py --debug
    PYTHONPATH=. python scripts/chat_live.py --session abc123   (nadaljuj sejo)

Izhod: Ctrl+C ali vtipkaj 'exit' / 'quit'
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "2026"))

from dotenv import load_dotenv
load_dotenv()

from app2026.brand.registry import get_brand
from app2026.chat_v3.router import handle_message


# ── ANSI barve ────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
RED    = "\033[91m"


def _header(session_id: str) -> None:
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   Kovačnik AI  —  V3  live chat              ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════╝{RESET}")
    print(f"{DIM}  Seja: {session_id}{RESET}")
    print(f"{DIM}  Izhod: Ctrl+C ali 'exit'{RESET}\n")


async def _send(message: str, session_id: str, brand, debug: bool) -> str:
    result = await handle_message(message, session_id, brand)
    if debug:
        # Pokaži interne podatke (intent, confidence) če so na voljo
        intent = result.get("intent", "")
        conf   = result.get("confidence", "")
        if intent or conf:
            print(f"  {DIM}[intent={intent}  conf={conf}]{RESET}")
    return result.get("reply", ""), result.get("session_id", session_id)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Kovačnik AI V3 live chat")
    parser.add_argument("--debug",   action="store_true", help="Pokaži intent/confidence")
    parser.add_argument("--session", default="",          help="ID obstoječe seje")
    args = parser.parse_args()

    session_id = args.session.strip() or str(uuid.uuid4())[:8]
    brand = get_brand()

    _header(session_id)

    while True:
        # Vhod
        try:
            raw = input(f"{BOLD}{GREEN}Ti:{RESET}  ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Nasvidenje!{RESET}\n")
            break

        if not raw:
            continue
        if raw.lower() in {"exit", "quit", "izhod", "konec"}:
            print(f"\n{DIM}Nasvidenje!{RESET}\n")
            break

        # Pošlji
        try:
            reply, session_id = await _send(raw, session_id, brand, args.debug)
        except Exception as exc:
            print(f"  {RED}[NAPAKA] {exc}{RESET}\n")
            continue

        # Odgovor
        print(f"\n{BOLD}{CYAN}Bot:{RESET} {reply}\n")


if __name__ == "__main__":
    asyncio.run(main())
