from fastapi import APIRouter
from pydantic import BaseModel
import re

from app2026.brand.registry import get_brand
from app2026.chat.flows import info as info_flow
from app2026.chat.flows import inquiry as inquiry_flow
from app2026.chat.flows import reservation as reservation_flow
from app2026.chat.flows.booking_flow import get_booking_continuation
from app2026.chat import answer as answer_mod
from app2026.chat import intent as intent_mod
from app2026.chat.state import get_session


TERMINAL_STEPS = {
    "awaiting_people",
    "awaiting_kids_info",
    "awaiting_kids_ages",
    "awaiting_room_location",
    "awaiting_table_location",
    "awaiting_name",
    "awaiting_phone",
    "awaiting_email",
    "awaiting_dinner",
    "awaiting_note",
    "awaiting_confirmation",
}
MAX_TERMINAL_INTERRUPTS = 3

router = APIRouter(prefix="/v2/chat", tags=["chat-v2"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None


@router.post("", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    session = get_session(payload.session_id)
    session.touch()
    session.history.append({"role": "user", "content": payload.message})
    if len(session.history) > 20:
        session.history = session.history[-20:]

    brand = get_brand()
    reply = _decision_pipeline(payload.message, session, brand)

    session.history.append({"role": "assistant", "content": reply})
    if len(session.history) > 20:
        session.history = session.history[-20:]

    return ChatResponse(reply=reply, session_id=session.session_id)


def _decision_pipeline(message: str, session, brand) -> str:
    reservation_state = session.data.get("reservation")
    if isinstance(reservation_state, dict):
        current_step = reservation_state.get("step")
    else:
        current_step = None

    # Terminal guard: never switch flows during critical booking steps.
    if current_step in TERMINAL_STEPS:
        if isinstance(reservation_state, dict) and reservation_state.get("awaiting_cancel_confirmation"):
            lowered = message.strip().lower()
            if reservation_flow.is_affirmative(lowered):
                reservation_flow.reset_reservation_state(reservation_state)
                session.active_flow = None
                session.step = None
                return "V redu, rezervacijo smo prekinili. Kako vam lahko še pomagam?"
            if lowered in {"ne", "ne hvala", "nadaljuj", "nadaljujmo", "ostani"}:
                reservation_state["awaiting_cancel_confirmation"] = False
                reservation_state["terminal_interrupt_count"] = 0
                return (
                    "Super, nadaljujmo z rezervacijo.\n\n"
                    f"{get_booking_continuation(current_step, reservation_state)}"
                )
            return "Prosim odgovorite z 'da' (prekini) ali 'ne' (nadaljuj rezervacijo)."

        intent = intent_mod.detect_intent(message, brand)
        text = (message or "").strip().lower()
        question_like = (
            "?" in text
            or text.startswith(("kaj", "kje", "kako", "ali", "imate", "je ", "pa "))
        )

        def looks_like_location_choice() -> bool:
            if current_step != "awaiting_room_location" or not isinstance(reservation_state, dict):
                return False
            options = reservation_state.get("available_locations") or []
            if not isinstance(options, list):
                return False
            lowered = text
            for opt in options:
                if isinstance(opt, str) and opt.lower() in lowered:
                    return True
            return False

        if (
            isinstance(reservation_state, dict)
            and not looks_like_location_choice()
            and not (current_step == "awaiting_kids_ages" and re.search(r"\d", text))
            and (intent in {"info", "help", "greeting"} or question_like)
        ):
            interrupt_count = int(reservation_state.get("terminal_interrupt_count") or 0) + 1
            reservation_state["terminal_interrupt_count"] = interrupt_count
            if intent == "info":
                side_reply = info_flow.handle(message, brand)
            elif intent == "help":
                side_reply = "Lahko odgovorim na info vprašanje in nato nadaljujeva rezervacijo."
            else:
                side_reply = "Pozdravljeni."
            if side_reply.strip() == "Za to nimam podatka.":
                side_reply = answer_mod.answer(message, session, brand)

            if interrupt_count >= MAX_TERMINAL_INTERRUPTS:
                reservation_state["awaiting_cancel_confirmation"] = True
                return (
                    f"{side_reply}\n\n"
                    "Vidim, da imate več dodatnih vprašanj. Želite prekiniti trenutno rezervacijo? (da/ne)"
                )

            return (
                f"{side_reply}\n\n"
                "Nadaljujmo z rezervacijo:\n"
                f"{get_booking_continuation(current_step, reservation_state)}"
            )

        if isinstance(reservation_state, dict):
            reservation_state["terminal_interrupt_count"] = 0
            reservation_state["awaiting_cancel_confirmation"] = False
        session.active_flow = "reservation"
        return reservation_flow.handle(session, message, brand)

    # 1) Active flow takes priority
    if session.active_flow:
        if session.active_flow == "reservation":
            return reservation_flow.handle(session, message, brand)
        if session.active_flow == "inquiry":
            inquiry_reply = inquiry_flow.handle(session, message)
            if inquiry_reply:
                return inquiry_reply
        flow_reply = _handle_active_flow(message, session, brand)
        if flow_reply:
            return flow_reply

    # 2) Intent detection
    intent = intent_mod.detect_intent(message, brand)

    # 3) Route to handlers
    if intent == "reservation":
        return reservation_flow.start(session, message, brand)
    if intent == "inquiry":
        return inquiry_flow.start(session, message)
    if intent == "greeting":
        return "Pozdravljeni! Kako vam lahko pomagam?"
    if intent == "help":
        return (
            "Pomagam lahko z rezervacijami, jedilnikom, informacijami o lokaciji in urniku ter izdelki."
        )
    if intent == "info":
        info_reply = info_flow.handle(message, brand)
        if info_reply.strip().lower() == "za to nimam podatka.":
            return answer_mod.answer(message, session, brand)
        return info_reply

    # 4) Fallback (LLM)
    return answer_mod.answer(message, session, brand)


def _handle_active_flow(message: str, session, brand) -> str | None:
    # Placeholder: in next steps we will plug reservation/inquiry flows here.
    return None


def _handle_info(message: str, brand) -> str:
    return info_flow.handle(message, brand)
