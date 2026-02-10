from __future__ import annotations

_current_clinic_id: str | None = None


def set_current_clinic_id(clinic_id: str | None) -> str | None:
    """Set and return previous clinic id (minimal stub for tests)."""
    global _current_clinic_id
    prev = _current_clinic_id
    _current_clinic_id = clinic_id
    return prev


def reset_current_clinic_id(token: str | None = None) -> None:
    """Restore previous clinic id (minimal stub for tests)."""
    global _current_clinic_id
    _current_clinic_id = token
