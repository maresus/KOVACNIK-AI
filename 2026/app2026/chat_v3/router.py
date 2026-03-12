from __future__ import annotations

import copy
import json
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import Settings
from app2026.brand.kovacnik_data import AMBIGUOUS_ENTITIES, resolve_entity
from app2026.brand.registry import get_brand
from app2026.chat import intent as v2_intent
from app2026.chat.state import get_session
from app2026.chat_v3 import config as v3_config
from app2026.chat_v3 import guards, interpreter, state_machine
from app2026.chat_v3 import ood_policy
from app2026.chat_v3.handlers import booking as booking_handler
from app2026.chat_v3.handlers import fallback as fallback_handler
from app2026.chat_v3.handlers import info as info_handler
from app2026.chat_v3.schemas import InterpretResult

router = APIRouter(prefix="/v3/chat", tags=["chat-v3"])
_settings = Settings()
_SHADOW_LOG_PATH = Path("data/shadow_intents.jsonl")
_DISAMBIG_LOG_PATH = Path("data/shadow_disambiguation.jsonl")

# Keyword sets for resolving pending disambiguation on the follow-up turn.
_PERSON_HINTS = frozenset({
    "druzin", "familij", "oseba", "sin", "hci", "hči", "gospod", "babi",
    "angelc", "danilo", "barbara", "kmetiji", "kmetija",
    "partner", "partnerica", "moz", "zena", "dekle", "fant",
})
# Month names — never treat as person/room names in disambiguation
# Include genitive forms (julija, avgusta, etc.) used in dates like "22. julija"
_MONTH_NAMES = frozenset({
    "januar", "januarja", "februar", "februarja", "marec", "marca",
    "april", "aprila", "maj", "maja", "junij", "junija",
    "julij", "julija",  # julija = genitive, also room/person name
    "avgust", "avgusta", "september", "septembra",
    "oktober", "oktobra", "november", "novembra", "december", "decembra",
})
_BOOKING_KEYWORDS = frozenset({"rezerv", "book", "sobo", "nočit", "nocit", "room"})
_ROOM_HINTS = frozenset({
    "sob",       # soba / sobo / sobi / sobah
    "nastanit", "nocit", "nocitev", "rezerv", "prenoc", "spalnic",
})


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None


def _preview(text: str, limit: int = 100) -> str:
    value = (text or "").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def _mask_message(message: str) -> str:
    # Minimal PII masking for shadow logs.
    text = message or ""
    text = text.replace("@", "[at]")
    return text


def _normalize_name(value: str) -> str:
    lowered = (value or "").lower()
    # Minimal normalization for Slovene diacritics in this routing guard.
    return (
        lowered.replace("ž", "z")
        .replace("š", "s")
        .replace("č", "c")
        .strip()
    )


def _detect_ambiguous_name_from_message(message: str) -> str | None:
    normalized = _normalize_name(message)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    token_set = set(tokens)
    for name in AMBIGUOUS_ENTITIES:
        if _normalize_name(name) in token_set:
            return name
    return None


def _log_disambiguation_event(session_id: str, message: str, name: str, question: str) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event": "router_disambiguation",
        "name": name,
        "message": _mask_message(message),
        "question": question,
    }
    try:
        _DISAMBIG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DISAMBIG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def _pre_dispatch_trap(message: str) -> str | None:
    """Deterministic keyword traps to override LLM misclassification.

    Returns a reply string if the message should be intercepted, else None.
    Only call this when the user is NOT mid-booking (guards handle those).
    """
    msg_l = (message or "").lower()

    # Jahanje / riding (J05 "lahk jaha", J10 "jahanje rezerviral")
    if re.search(r"\bjaha", msg_l) or any(kw in msg_l for kw in ("lahk jaha", "lahko jaha", "jahamo", "jahanj")):
        return (
            "Jahanje s ponijem je mogoče!\n"
            "Na kmetiji imata Malajka in Marsi rada najmlajše goste.\n"
            "Cena: 5 € na krog. Ob prihodu povejte, da bi radi jahali."
        )

    # Kajin paket (S12 "kaj je v kajnem paketu")
    if any(kw in msg_l for kw in ("kajnem paketu", "kajin paket", "kajin pak", "kajinem paketu")):
        return (
            "Kajin paket (sirup, čaj, marmelada) — 17,50 €\n"
            "🛒 https://kovacnik.com/kovacnikova-spletna-trgovina/"
        )

    # Bunka slang — "bunk za domov" (S07)
    if "bunk" in msg_l:
        return (
            "Mesni izdelki Kovačnik:\n"
            "  • Pohorska bunka, 500 g — 18–21 €\n"
            "  • Suha salama, 650 g — 16 €\n"
            "  • Hišna suha klobasa, 180 g — 7 €\n"
            "🛒 https://kovacnik.com/kovacnikova-spletna-trgovina/"
        )

    # Božanje živali — petting farm animals (NOT bringing pets)
    # Must fire BEFORE pet policy so "božamo mačke" doesn't trigger pet rejection
    if any(kw in msg_l for kw in ("bož", "pobož", "božam", "božamo", "boham", "bohamo")):
        if any(kw in msg_l for kw in ("mačk", "muck", "muce", "zajc", "poni", "konj", "krav", "žival", "mucek", "macke", "macek")):
            return (
                "Seveda! Naše živali lahko pobožate ob obisku.\n"
                "Julija z veseljem pokaže živali otrokom in odraslim."
            )

    # Hišni ljubljenčki / psi (RS14 "Ali sprejmete pse") — razširjen za typo
    if (any(kw in msg_l for kw in ("psa", "pse", " pes", "psičko", "psicko")) or re.search(r"\bpes\b", msg_l)):
        if any(kw in msg_l for kw in ("dovol", "prepo", "sme", "lahko", "lahk", "prinest", "pripelj", "prpel", "sprejmete", "sprejma", "imam", "vzam", "pelem", "peljem")):
            return (
                "Žal hišnih ljubljenčkov pri nas ne sprejemamo.\n"
                "Če vas zanimajo živali na naši kmetiji, jih ob obisku z veseljem pokažemo! "
                "Pokličite Barbaro za dogovor: 031 330 113"
            )

    # Alergije / posebna prehrana (RS15 "alergijo na gluten")
    if any(kw in msg_l for kw in ("alergij", "alergijo", "brezglutensko", "brezgluten", "celiakij", "laktozni")):
        return (
            "Za posebne prehranske zahteve (alergije, vegetarijansko, brezglutensko) "
            "nas pokličite vnaprej — Barbara bo poskrbela za vaše potrebe.\n"
            "Pokličite: 031 330 113 ali pišite: info@kovacnik.si"
        )

    # Danilo kontakt (O03 "Danilova tel stevilka")
    if "danilo" in msg_l and any(kw in msg_l for kw in ("tel", "stevilka", "kontakt", "poklic", "stik")):
        return (
            "Za stik z Danilom in kmetijo pokličite Barbaro: 031 330 113\n"
            "ali pišite: info@kovacnik.si"
        )

    # WiFi / internet
    if any(kw in msg_l for kw in ("wifi", "wi-fi", "internet", "brezžičn", "omrež")):
        return (
            "Wifi je na voljo v celotni hiši — brezplačno in odprto.\n"
            "Gesla ne potrebujete, samo povežite se na omrežje 'Kovacnik'."
        )

    # Parking / parkiranje
    if any(kw in msg_l for kw in ("parking", "parkir", "avto postav", "kam z avtom", "parkirišč")):
        return (
            "Parkiranje je brezplačno neposredno pri kmetiji.\n"
            "Prostora je dovolj za vse goste."
        )

    # Zajtrk (breakfast)
    if any(kw in msg_l for kw in ("zajtrk", "zjutraj jem", "zjutraj jest", "jutranjo")):
        return (
            "Zajtrk je vključen v ceno nočitve.\n"
            "  • Postrežemo vsak dan od 8:00 do 9:00\n"
            "  • Domač pohorski zajtrk s svežimi izdelki z naše kmetije"
        )

    # Večerja (dinner)
    if any(kw in msg_l for kw in ("večerj", "vacerj", "večer jem", "večer jest", "polpenzion", "penzion")):
        if any(kw in msg_l for kw in ("cen", "stane", "koliko", "eur", "€")):
            return (
                "Penzionska večerja: 25 € po odrasli osebi\n"
                "  • Juha, glavna jed in sladica\n"
                "  • Postrežemo ob 18:00\n"
                "  • POZOR: Ob ponedeljkih in torkih večerij ne pripravljamo"
            )
        return (
            "Večerjo ponujamo ob 18:00 vsak dan razen ponedeljka in torka.\n"
            "  • Penzionska večerja (juha, glavna jed, sladica): 25 € / oseba\n"
            "  • Naročite jo lahko ob prijavi ali med bivanjem"
        )

    # Check-in / check-out / prijava / odjava
    if any(kw in msg_l for kw in ("check", "prijav", "odjav", "nastanit", "prihod ura", "kdaj pridem", "kdaj lahko pridem")):
        _has_in = any(kw in msg_l for kw in ("check-in", "checkin", "prijav", "pride", "prihod", "nastanit"))
        _has_out = any(kw in msg_l for kw in ("check-out", "checkout", "odjav", "oditi", "odide", "zapust"))
        # BOTH asked together
        if _has_in and _has_out:
            return (
                "Ure prihoda in odhoda:\n"
                "  • Check-in (prihod): od 14:00 naprej\n"
                "  • Check-out (odhod): do 10:00\n"
                "Če potrebujete zgodnejši prihod ali kasnejši odhod, nas pokličite vnaprej: 031 330 113"
            )
        if _has_out:
            return "Odjava iz sobe (check-out) je do 10:00."
        if _has_in:
            return "Prijava v sobo (check-in) je od 14:00 naprej."
        return (
            "Časi prijave in odjave:\n"
            "  • Prijava (check-in): od 14:00\n"
            "  • Odjava (check-out): do 10:00"
        )

    # Klimatizacija / klima
    if any(kw in msg_l for kw in ("klim", "hlajenje", "vroč", "mraz soba")):
        return "Vse sobe so klimatizirane — za prijetno temperaturo je poskrbljeno."

    # Min nočitve
    if any(kw in msg_l for kw in ("minim", "najmanj", "najkraj", "ena noč", "eno noc", "1 noč", "1 noc")):
        return (
            "Minimalno število nočitev:\n"
            "  • Junij, julij, avgust: 3 nočitve\n"
            "  • Ostali meseci: 2 nočitvi\n\n"
            "Rezervacija ene nočitve žal ni možna."
        )

    # Zima / smučišče (KDZ05, KDZ07)
    if any(kw in msg_l for kw in ("pozim", "zimsk", "pozimi", "zima ", "sneg", "sneži", "snezi", "smuc", "smuč", "smučišč", "areh")) or re.search(r"\bzima\b", msg_l):
        return (
            "Najbližji smučišči sta Mariborsko Pohorje in Areh — od nas je do obeh nekje 25–35 minut vožnje.\n"
            "Odlična izbira za poldnevni ali celodnevni izlet med bivanjem pri nas.\n"
            "Če potrebujete nasvet o pristopu ali kje je manj gneče, vam z veseljem povemo."
        )

    # Dež / slabo vreme (KDZ04 "slabo vreme kaj naredimo")
    if any(kw in msg_l for kw in ("dežj", "deže", "deževn", "slabo vreme", "dežuje", "dezuje", "dezeva")) or re.search(r"\bdez\b", msg_l):
        return (
            "Ob dežju je kmetija prav tako prijetna!\n"
            "  • Ogled živali v hlevu — Julija jih rada pokaže otrokom\n"
            "  • Degustacija domačih likerjev, sirupov in marmelad\n"
            "  • Degustacijski meni (po dogovoru)\n"
            "  • Degustacija vin v prijetnem domačem vzdušju"
        )

    return None


async def _dispatch(result: InterpretResult, message: str, session, brand) -> dict[str, str]:
    if result.intent.startswith("INFO_"):
        return await info_handler.execute(result, message, session, brand)
    if result.intent in {"BOOKING_ROOM", "BOOKING_TABLE", "CONTINUE_FLOW", "CANCEL", "CONFIRM"}:
        return await booking_handler.execute(result, message, session, brand)
    return await fallback_handler.execute(result, message, session, brand)


async def handle_message(message: str, session_id: str, brand: Any) -> dict[str, Any]:
    session = get_session(session_id)
    guard_result = guards.check(message, session)
    if guard_result:
        if guard_result["action"] in {"continue_flow", "menu_detail"}:
            reply = await booking_handler.execute(
                InterpretResult(intent="CONTINUE_FLOW", entities=guard_result, confidence=1.0, continue_flow=True),
                message,
                session,
                brand,
            )
            return {"reply": reply["reply"], "session_id": session.session_id}

    # ── OOD Policy Guard ────────────────────────────────────────────────────
    # Check for out-of-domain messages BEFORE disambiguation and pre-dispatch traps.
    # This ensures OOD messages are handled early and consistently.
    _ood_result = ood_policy.check_ood(
        message,
        rag_similarity=None,  # Will be set after RAG call if needed
        session_data=session.data,
    )
    if _ood_result.is_ood and _ood_result.response:
        # Handle mixed input if present
        if _ood_result.in_domain_parts and ood_policy.OOD_MIXED_SPLIT_ENABLED:
            # Process in-domain part and combine with OOD acknowledgment
            in_domain_msg = " ".join(_ood_result.in_domain_parts)
            # Let the rest of the pipeline handle the in-domain part
            # by continuing with modified message
            pass  # Fall through - will be handled by normal flow
        else:
            return {"reply": _ood_result.response, "session_id": session.session_id}

    # Resolve pending disambiguation from the previous turn (e.g. user replied
    # "iz družine" or "soba" after we asked them to clarify Aljaž/Julija/Ana).
    _pending = session.data.get("_pending_disambiguation")
    if _pending:
        # Normalize diacritics so "iz družine" matches hint "druzin" etc.
        msg_normalized = _normalize_name(message)
        is_person = any(h in msg_normalized for h in _PERSON_HINTS)
        is_room = any(h in msg_normalized for h in _ROOM_HINTS)
        if is_person and not is_room:
            session.data.pop("_pending_disambiguation", None)
            reply = await info_handler.execute(
                InterpretResult(
                    intent="INFO_PERSON",
                    entities={"name": _pending, "_resolved": "person"},
                    confidence=1.0,
                ),
                _pending,
                session,
                brand,
            )
            return {"reply": reply["reply"], "session_id": session.session_id}
        if is_room and not is_person:
            session.data.pop("_pending_disambiguation", None)
            reply = await info_handler.execute(
                InterpretResult(
                    intent="INFO_ROOM",
                    entities={"name": _pending, "_resolved": "room"},
                    confidence=1.0,
                ),
                _pending,
                session,
                brand,
            )
            return {"reply": reply["reply"], "session_id": session.session_id}
        # Still ambiguous — fall through to normal flow (interpreter will try)

    # Deterministic disambiguation must run before interpreter/handlers
    # and must not depend on LLM output or intent class.
    # Skip disambiguation entirely when user is mid-booking — month names like
    # "julija" (the month) would otherwise trigger room/person disambiguation.
    _in_booking = session.active_flow == "reservation"

    # Pre-dispatch keyword traps — fire before disambiguation AND LLM to ensure
    # deterministic responses for specific topics regardless of LLM classification
    # or confidence. Only fires when user is NOT mid-booking.
    if not _in_booking:
        _trap_reply = _pre_dispatch_trap(message)
        if _trap_reply is not None:
            return {"reply": _trap_reply, "session_id": session.session_id}

    # Also skip when the message contains clear booking intent + month name
    # (e.g. "Ok rad bi rezerviral. Prihod 20. julija..." should not trigger Julija disambiguation)
    # Also skip when there's booking intent + room context — they want to BOOK the room,
    # not get info about it. Let the interpreter handle it as BOOKING_ROOM.
    _msg_low = message.lower()
    _has_booking_intent = any(kw in _msg_low for kw in ("rezerv", "book", "zarezrv", "rad bi", "bi rad", "bi želel", "bi zelel"))
    _has_room_ctx = any(kw in _msg_low for kw in ("sobo", "soba", "sobi", "mizo", "miza"))
    _has_month = any(m in _msg_low for m in _MONTH_NAMES)
    _has_nights = any(kw in _msg_low for kw in ("noči", "noci", "nočitv", "nocitv"))
    # Skip disambiguation if: booking flow OR (booking intent + month/nights) OR (room context + month)
    _skip_disambig = _in_booking or (_has_booking_intent and (_has_month or _has_nights)) or (_has_room_ctx and _has_month)
    ambiguous_name = None if _skip_disambig else _detect_ambiguous_name_from_message(message)
    if ambiguous_name:
        resolved = resolve_entity(ambiguous_name)
        if isinstance(resolved, dict) and resolved.get("action") == "clarify":
            # If the message itself already provides context, resolve directly
            # without asking — e.g. "Kakšna je soba Aljaž?" already says "soba".
            _msg_ctx = _normalize_name(message)
            if any(h in _msg_ctx for h in _ROOM_HINTS) and not any(h in _msg_ctx for h in _PERSON_HINTS):
                reply = await info_handler.execute(
                    InterpretResult(
                        intent="INFO_ROOM",
                        entities={"name": ambiguous_name, "_resolved": "room"},
                        confidence=1.0,
                    ),
                    ambiguous_name, session, brand,
                )
                return {"reply": reply["reply"], "session_id": session.session_id}
            if any(h in _msg_ctx for h in _PERSON_HINTS) and not any(h in _msg_ctx for h in _ROOM_HINTS):
                reply = await info_handler.execute(
                    InterpretResult(
                        intent="INFO_PERSON",
                        entities={"name": ambiguous_name, "_resolved": "person"},
                        confidence=1.0,
                    ),
                    ambiguous_name, session, brand,
                )
                return {"reply": reply["reply"], "session_id": session.session_id}
            # No clear context — ask the user
            question = str(resolved.get("question") or "").strip()
            if question:
                session.data["_pending_disambiguation"] = ambiguous_name
                _log_disambiguation_event(
                    session_id=session.session_id,
                    message=message,
                    name=ambiguous_name,
                    question=question,
                )
                return {"reply": question, "session_id": session.session_id}

    history = session.history[-5:]

    # Pre-interpretation override: "soba za X oseb" is clearly a booking, not info request
    _msg_low = message.lower()
    _has_room_for = re.search(r"sob[oai]\s+(za\s+)?\d+", _msg_low) or any(kw in _msg_low for kw in ("soba za", "sobo za"))
    _has_people = any(kw in _msg_low for kw in ("odrasl", "oseb", "osebe", "otroc", "otrok"))
    if _has_room_for and _has_people:
        # Force BOOKING_ROOM intent - this is clearly a booking request
        result = InterpretResult(intent="BOOKING_ROOM", entities={}, confidence=0.95)
    else:
        result = interpreter.interpret(message, history, session.data)

    threshold = v3_config.get_confidence_threshold(result.intent)
    if result.confidence < threshold:
        reply = await fallback_handler.execute(result, message, session, brand)
        return {"reply": reply["reply"], "session_id": session.session_id}

    if result.needs_clarification and result.clarification_question:
        # Suppress false disambiguation: month names in booking context are dates, not person names.
        # Also suppress when message has clear person context (e.g. "partnerica") without room context —
        # let info_handler resolve the right person via token scoring.
        _msg_low = message.lower()
        _msg_norm = _normalize_name(_msg_low)
        _has_month = any(m in _msg_low for m in _MONTH_NAMES)
        _has_booking = any(b in _msg_low for b in _BOOKING_KEYWORDS)
        _has_clear_person = (
            any(h in _msg_norm for h in _PERSON_HINTS)
            and not any(h in _msg_norm for h in _ROOM_HINTS)
        )
        if not (_has_month and _has_booking) and not _has_clear_person:
            return {"reply": result.clarification_question, "session_id": session.session_id}

    # Remember whether we were mid-booking BEFORE the transition.
    _pre_flow = session.active_flow
    _pre_step = session.step

    session.active_flow = state_machine.transition(session.active_flow, result)
    reply = await _dispatch(result, message, session, brand)
    reply_text = reply["reply"]

    # If user switched topic mid-booking, gently offer to continue after answering.
    _booking_intents = {"BOOKING_ROOM", "BOOKING_TABLE", "CONTINUE_FLOW", "CANCEL", "CONFIRM"}
    if (
        _pre_flow == "reservation"
        and _pre_step
        and result.intent not in _booking_intents
        and session.active_flow == "reservation"  # booking still active (not cancelled/completed)
    ):
        from app2026.chat.flows.booking_flow import get_booking_continuation
        _continuation = get_booking_continuation(_pre_step, {})
        reply_text = reply_text + f"\n\n—\nNadaljujemo z rezervacijo? {_continuation}"

    return {"reply": reply_text, "session_id": session.session_id}


async def build_shadow_record(message: str, session, brand: Any, v2_reply: str) -> dict[str, Any]:
    start = time.perf_counter()
    old_intent = v2_intent.detect_intent(message, brand)
    result = interpreter.interpret(message, session.history[-5:], session.data)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    # Predict v3 response in a deep-copied session snapshot.
    snapshot = copy.deepcopy(session)
    would = await _dispatch(result, message, snapshot, brand)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session.session_id,
        "message": _mask_message(message),
        "v2_intent": old_intent,
        "v3_intent": result.intent,
        "v3_confidence": result.confidence,
        "v3_entities": result.entities,
        "v3_needs_clarification": result.needs_clarification,
        "latency_ms": latency_ms,
        "v2_response_preview": _preview(v2_reply),
        "v3_would_respond": _preview(would.get("reply", "")),
        "final_handler": result.intent.lower(),
    }


def log_shadow_record(record: dict[str, Any]) -> None:
    try:
        _SHADOW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _SHADOW_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def build_shadow_record_sync(message: str, session, brand: Any, v2_reply: str) -> dict[str, Any]:
    return asyncio.run(build_shadow_record(message, session, brand, v2_reply))


@router.post("", response_model=ChatResponse)
async def chat_v3_endpoint(payload: ChatRequest) -> ChatResponse:
    # Disabled by default.
    if not _settings.v3_enabled or _settings.chat_engine != "v3":
        return ChatResponse(reply="V3 endpoint je izklopljen. Uporabite /v2/chat.", session_id=payload.session_id)
    brand = get_brand()
    result = await handle_message(payload.message, payload.session_id or "", brand)

    # Log conversation to database for daily reports
    try:
        from app.services.reservation_service import ReservationService
        service = ReservationService()
        service.log_conversation(
            session_id=str(result["session_id"]),
            user_message=payload.message,
            bot_response=str(result["reply"]),
            intent=None,  # V3 doesn't expose intent directly
            needs_followup=False,
            followup_email=None,
        )
    except Exception as e:
        # Don't fail the chat if logging fails
        print(f"[V3 CHAT] Napaka pri logganju pogovora: {e}")

    return ChatResponse(reply=str(result["reply"]), session_id=str(result["session_id"]))
