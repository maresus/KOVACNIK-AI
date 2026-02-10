from __future__ import annotations

import os
import re
from typing import Any, Optional

from app.services.email_service import send_custom_message
from app.services.reservation_service import ReservationService


INQUIRY_RECIPIENT = os.getenv("INQUIRY_RECIPIENT", "info@kovacnik.com")
_reservation_service = ReservationService()


def _blank_inquiry_state() -> dict[str, Optional[str]]:
    return {
        "step": None,
        "details": "",
        "deadline": "",
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "contact_raw": "",
    }


def start(session: Any, message: str) -> str:
    session.active_flow = "inquiry"
    state = session.data.get("inquiry")
    if not isinstance(state, dict):
        state = _blank_inquiry_state()
        session.data["inquiry"] = state
    state["details"] = message.strip()
    state["step"] = "awaiting_deadline"
    return "Super, zabeležim povpraševanje. Do kdaj bi to potrebovali? (datum/rok ali 'ni pomembno')"


def handle(session: Any, message: str) -> Optional[str]:
    state = session.data.get("inquiry")
    if not isinstance(state, dict) or not state.get("step"):
        return None
    reply = handle_inquiry_flow(message, state, session.session_id)
    if state.get("step") is None:
        session.active_flow = None
        session.step = None
    return reply


def handle_inquiry_flow(message: str, state: dict[str, Optional[str]], session_id: str) -> Optional[str]:
    text = message.strip()
    lowered = text.lower()
    step = state.get("step")

    if step == "awaiting_consent":
        if lowered in {"da", "ja", "seveda", "lahko", "ok"}:
            state["step"] = "awaiting_details"
            return "Odlično. Prosim opišite, kaj točno želite (količina, izdelek, storitev)."
        if lowered in {"ne", "ne hvala", "ni treba"}:
            reset_inquiry_state(state)
            return "V redu. Če želite, lahko vprašate še kaj drugega."
        return "Želite, da zabeležim povpraševanje? Odgovorite z 'da' ali 'ne'."

    if step == "awaiting_details":
        if text:
            state["details"] = (state.get("details") or "")
            state["details"] = f"{state['details']}\n{text}".strip()
        state["step"] = "awaiting_deadline"
        return "Hvala! Do kdaj bi to potrebovali? (datum/rok ali 'ni pomembno')"

    if step == "awaiting_deadline":
        if any(word in lowered for word in ["ni", "ne vem", "kadar koli", "vseeno", "ni pomembno"]):
            state["deadline"] = ""
        else:
            state["deadline"] = text
        state["step"] = "awaiting_contact"
        return "Super. Prosim še kontakt (ime, telefon, email)."

    if step == "awaiting_contact":
        state["contact_raw"] = text
        email = extract_email(text)
        phone = extract_phone(text)
        state["contact_email"] = email or state.get("contact_email") or ""
        state["contact_phone"] = phone or state.get("contact_phone") or ""
        if not state["contact_email"]:
            return "Za povratni kontakt prosim dodajte email."

        details = state.get("details") or text
        deadline = state.get("deadline") or ""
        contact_summary = state.get("contact_raw") or ""
        summary = "\n".join(
            [
                "Novo povpraševanje:",
                f"- Podrobnosti: {details}",
                f"- Rok: {deadline or 'ni naveden'}",
                f"- Kontakt: {contact_summary}",
                f"- Session: {session_id}",
            ]
        )
        _reservation_service.create_inquiry(
            session_id=session_id,
            details=details,
            deadline=deadline,
            contact_name=state.get("contact_name") or "",
            contact_email=state.get("contact_email") or "",
            contact_phone=state.get("contact_phone") or "",
            contact_raw=contact_summary,
            source="chat",
            status="new",
        )
        send_custom_message(
            INQUIRY_RECIPIENT,
            "Novo povpraševanje – Kovačnik",
            summary,
        )
        reset_inquiry_state(state)
        return "Hvala! Povpraševanje sem zabeležil in ga posredoval. Odgovorimo vam v najkrajšem možnem času."

    return None


def start_inquiry_consent(state: dict[str, Optional[str]]) -> str:
    state["step"] = "awaiting_consent"
    return (
        "Žal nimam dovolj informacij. "
        "Lahko zabeležim povpraševanje in ga posredujem ekipi. "
        "Želite to? (da/ne)"
    )


def reset_inquiry_state(state: dict[str, Optional[str]]) -> None:
    state.clear()
    state.update(_blank_inquiry_state())


def extract_email(text: str) -> str:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    digits = re.sub(r"\D", "", text)
    return digits if len(digits) >= 7 else ""
