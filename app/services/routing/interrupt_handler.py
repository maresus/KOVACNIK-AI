from __future__ import annotations

from typing import Any, Optional

from app.services.reservation_flow import get_booking_continuation


def handle_interrupt(answer: str, current_step: Optional[str], reservation_state: Optional[dict[str, Any]] = None) -> str:
    continuation = get_booking_continuation(current_step or "", reservation_state or {})
    if continuation:
        return f"{answer}\n\n---\n{continuation}"
    return answer
