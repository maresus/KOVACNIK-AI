from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app2026.brand.registry import get_brand
from app2026.chat.flows import info as info_flow
from app2026.chat.flows import inquiry as inquiry_flow
from app2026.chat.flows import reservation as reservation_flow
from app2026.chat import answer as answer_mod
from app2026.chat import intent as intent_mod
from app2026.chat.state import get_session


TERMINAL_STEPS = {
    "awaiting_name",
    "awaiting_phone",
    "awaiting_email",
    "awaiting_confirmation",
}

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
    session.last_activity = datetime.now(timezone.utc)
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
        return info_flow.handle(message, brand)

    # 4) Fallback (LLM)
    return answer_mod.answer(message, session, brand)


def _handle_active_flow(message: str, session, brand) -> str | None:
    # Placeholder: in next steps we will plug reservation/inquiry flows here.
    return None


def _handle_info(message: str, brand) -> str:
    return info_flow.handle(message, brand)
