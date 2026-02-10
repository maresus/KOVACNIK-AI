from __future__ import annotations

from typing import Any, Dict, Optional


def _blank_unified_state() -> Dict[str, Any]:
    return {
        "flow": "idle",  # idle | reservation_table | reservation_room | inquiry
        "step": None,
        "data": {},  # reservation, inquiry, availability
        "last_intent": "",
        "pending_question": "",
        "context": {},
    }


_SESSION_STATES: Dict[str, Dict[str, Any]] = {}


def get_unified_state(session_id: str) -> Dict[str, Any]:
    if session_id not in _SESSION_STATES:
        _SESSION_STATES[session_id] = _blank_unified_state()
    return _SESSION_STATES[session_id]


def reset_unified_state(state_or_session: Any) -> None:
    """Reset unified state by state dict or session id."""
    if isinstance(state_or_session, dict):
        state_or_session.update(_blank_unified_state())
        return
    if isinstance(state_or_session, str):
        state = get_unified_state(state_or_session)
        state.update(_blank_unified_state())
        return
    raise TypeError("reset_unified_state expects dict state or session_id str")


def set_flow(state: Dict[str, Any], flow: str, step: Optional[str] = None) -> None:
    state["flow"] = flow
    state["step"] = step


def ensure_flow_data(state: Dict[str, Any], key: str, default: Any) -> Any:
    if key not in state["data"]:
        state["data"][key] = default
    return state["data"][key]


def set_last_intent(state: Dict[str, Any], intent: str) -> None:
    state["last_intent"] = intent


def set_pending_question(state: Dict[str, Any], question: str) -> None:
    state["pending_question"] = question


class StateManager:
    """Minimal state manager for tests/compatibility."""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def get_state(self) -> Dict[str, Any]:
        return get_unified_state(self.session_id)

    def ensure_context(self) -> Dict[str, Any]:
        state = self.get_state()
        return state.setdefault("context", {})

    def set_context_value(self, key: str, value: Any) -> None:
        ctx = self.ensure_context()
        ctx[key] = value

    def get_context_value(self, key: str, default: Any = None) -> Any:
        return self.ensure_context().get(key, default)
