from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class SessionState:
    session_id: str
    active_flow: str | None = None
    step: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)
    last_activity: datetime | None = None


_SESSIONS: dict[str, SessionState] = {}


def get_session(session_id: str | None) -> SessionState:
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = SessionState(session_id=session_id)
    return _SESSIONS[session_id]


def reset_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
