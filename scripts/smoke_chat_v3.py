#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "2026"))

from app.core.config import Settings
from app2026.chat_v3 import guards, interpreter


@dataclass
class FakeSession:
    active_flow: str | None = None
    step: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)


def _ok(value: bool) -> str:
    return "PASS" if value else "FAIL"


def run() -> int:
    load_dotenv()
    failures = 0
    skipped = 0
    llm_enabled = bool(Settings().openai_api_key)

    # 1) Kdo je Aljaž?
    if llm_enabled:
        r1 = interpreter.interpret("Kdo je Aljaž?", [], {})
        t1 = (r1.intent == "INFO_PERSON") or bool(r1.needs_clarification)
        print(f"[1] {_ok(t1)} intent={r1.intent} clarify={r1.needs_clarification}")
        failures += int(not t1)
    else:
        print("[1] SKIP no OPENAI_API_KEY")
        skipped += 1

    # 2) Kakšna je soba Aljaž?
    if llm_enabled:
        r2 = interpreter.interpret("Kakšna je soba Aljaž?", [], {})
        t2 = r2.intent == "INFO_ROOM"
        print(f"[2] {_ok(t2)} intent={r2.intent}")
        failures += int(not t2)
    else:
        print("[2] SKIP no OPENAI_API_KEY")
        skipped += 1

    # 3) Weekly menu follow-up "6"
    s3 = FakeSession(
        history=[
            {"role": "user", "content": "kaj ponujate čez teden"},
            {
                "role": "assistant",
                "content": "Med tednom ponujamo 4-hodni, 5-hodni, 6-hodni, 7-hodni meni.",
            },
        ]
    )
    g3 = guards.check("6", s3)
    t3 = isinstance(g3, dict) and g3.get("action") == "menu_detail" and g3.get("value") == 6
    print(f"[3] {_ok(t3)} guard={g3}")
    failures += int(not t3)

    # 4) Email guard
    s4 = FakeSession(active_flow="reservation", step="awaiting_email")
    g4 = guards.check("marko@test.com", s4)
    t4 = isinstance(g4, dict) and g4.get("field") == "email"
    print(f"[4] {_ok(t4)} guard={g4}")
    failures += int(not t4)

    # 5) Phone guard
    s5 = FakeSession(active_flow="reservation", step="awaiting_phone")
    g5 = guards.check("041123456", s5)
    t5 = isinstance(g5, dict) and g5.get("field") == "phone"
    print(f"[5] {_ok(t5)} guard={g5}")
    failures += int(not t5)

    # 6) Confirm guard
    s6 = FakeSession(active_flow="reservation", step="awaiting_confirmation")
    g6 = guards.check("da", s6)
    t6 = isinstance(g6, dict) and g6.get("field") == "confirm" and g6.get("value") is True
    print(f"[6] {_ok(t6)} guard={g6}")
    failures += int(not t6)

    # 7) Cancel intent
    if llm_enabled:
        r7 = interpreter.interpret("ne, prekliči", [], {})
        t7 = r7.intent == "CANCEL"
        print(f"[7] {_ok(t7)} intent={r7.intent}")
        failures += int(not t7)
    else:
        print("[7] SKIP no OPENAI_API_KEY")
        skipped += 1

    # 8) INFO_ANIMAL intent
    if llm_enabled:
        r8 = interpreter.interpret("Kakšne živali imate?", [], {})
        t8 = r8.intent == "INFO_ANIMAL"
        print(f"[8] {_ok(t8)} intent={r8.intent}")
        failures += int(not t8)
    else:
        print("[8] SKIP no OPENAI_API_KEY")
        skipped += 1

    # 9) GREETING intent
    if llm_enabled:
        r9 = interpreter.interpret("Živjo", [], {})
        t9 = r9.intent == "GREETING"
        print(f"[9] {_ok(t9)} intent={r9.intent}")
        failures += int(not t9)
    else:
        print("[9] SKIP no OPENAI_API_KEY")
        skipped += 1

    # 10) BOOKING_TABLE intent
    if llm_enabled:
        r10 = interpreter.interpret("Rad bi rezerviral mizo", [], {})
        t10 = r10.intent == "BOOKING_TABLE"
        print(f"[10] {_ok(t10)} intent={r10.intent}")
        failures += int(not t10)
    else:
        print("[10] SKIP no OPENAI_API_KEY")
        skipped += 1

    executed = 10 - skipped
    print(f"\nSummary: {executed - failures}/{executed} passed, {skipped} skipped")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mini smoke tests for chat_v3 interpreter/guards.")
    _ = parser.parse_args()
    raise SystemExit(run())
