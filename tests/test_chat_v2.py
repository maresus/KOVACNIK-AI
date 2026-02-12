import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "2026"))

# Avoid optional dependency errors during import (email_service -> resend)
if "resend" not in sys.modules:
    sys.modules["resend"] = ModuleType("resend")

from app2026.chat import router as v2_router  # noqa: E402
from app2026.chat import state as chat_state  # noqa: E402
from app2026.chat.flows import inquiry as inquiry_flow  # noqa: E402
from app2026.chat.flows import reservation as reservation_flow  # noqa: E402


class DummyReservationService:
    def validate_room_rules(self, date, nights):
        return True, ""

    def check_room_availability(self, *args, **kwargs):
        return True, "Sobe (dodelimo ob prihodu)", []

    def available_rooms(self, *args, **kwargs):
        return ["Soba ALJAŽ"]

    def check_table_availability(self, *args, **kwargs):
        return True, "Jedilnica Pri peči", ["Jedilnica Pri peči"]

    def _table_room_occupancy(self):
        return {}

    def _parse_time(self, value):
        return value

    def _parse_date(self, value):
        try:
            return datetime.strptime(value, "%d.%m.%Y")
        except Exception:
            return None

    def validate_table_rules(self, date, time):
        return True, ""

    def create_reservation(self, *args, **kwargs):
        return 1

    def log_conversation(self, *args, **kwargs):
        return None

    def create_inquiry(self, *args, **kwargs):
        return 1


@pytest.fixture()
def client(monkeypatch):
    dummy = DummyReservationService()
    monkeypatch.setattr(reservation_flow, "_reservation_service", dummy)
    monkeypatch.setattr(inquiry_flow, "_reservation_service", dummy)

    app = FastAPI()
    app.include_router(v2_router.router)
    return TestClient(app)


def test_v2_greeting(client):
    res = client.post("/v2/chat", json={"message": "živjo"})
    assert res.status_code == 200
    data = res.json()
    assert "Pozdravljeni" in data["reply"]
    assert data.get("session_id")


def test_v2_info_address(client):
    res = client.post("/v2/chat", json={"message": "Kje ste?"})
    data = res.json()
    assert "Planica" in data["reply"]


def test_v2_reservation_start(client):
    res = client.post("/v2/chat", json={"message": "Rad bi sobo"})
    data = res.json()
    assert "datum" in data["reply"].lower()


def test_v2_inquiry_start(client):
    res = client.post("/v2/chat", json={"message": "Rad bi ponudbo za dogodek"})
    data = res.json()
    assert "do kdaj" in data["reply"].lower()


def test_v2_concurrent_sessions_isolate_state(client):
    session_a = "session-a"
    session_b = "session-b"

    start_a = client.post("/v2/chat", json={"message": "Rad bi rezerviral sobo", "session_id": session_a})
    assert start_a.status_code == 200
    assert "datum" in start_a.json()["reply"].lower()

    greet_b = client.post("/v2/chat", json={"message": "živjo", "session_id": session_b})
    assert greet_b.status_code == 200
    assert "pozdravljeni" in greet_b.json()["reply"].lower()

    continue_a = client.post("/v2/chat", json={"message": "12.12.2099", "session_id": session_a})
    assert continue_a.status_code == 200
    assert "nočit" in continue_a.json()["reply"].lower()


def test_v2_session_timeout_resets_state():
    sid = "timeout-session"
    session = chat_state.get_session(sid)
    session.active_flow = "reservation"
    session.step = "awaiting_email"
    session.data["reservation"] = {"step": "awaiting_email", "type": "room"}
    session.last_activity = datetime.now(timezone.utc) - timedelta(minutes=31)

    refreshed = chat_state.get_session(sid)
    assert refreshed.session_id == sid
    assert refreshed.active_flow is None
    assert refreshed.step is None
    assert refreshed.data == {}


def test_v2_kids_ages_requires_numbers(client):
    sid = "kids-ages-validation"
    client.post("/v2/chat", json={"message": "Rad bi rezerviral sobo", "session_id": sid})
    client.post("/v2/chat", json={"message": "12.12.2099", "session_id": sid})
    client.post("/v2/chat", json={"message": "3", "session_id": sid})
    client.post("/v2/chat", json={"message": "4", "session_id": sid})
    client.post("/v2/chat", json={"message": "2", "session_id": sid})  # kids count -> awaiting_kids_ages

    res = client.post("/v2/chat", json={"message": "imate parking?", "session_id": sid})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "nadaljujmo z rezervacijo" in reply
    assert "koliko so stari" in reply

    session = chat_state.get_session(sid)
    reservation = session.data.get("reservation", {})
    assert reservation.get("step") == "awaiting_kids_ages"


def test_v2_terminal_allows_short_info_then_resumes(client, monkeypatch):
    original_detect = v2_router.intent_mod.detect_intent
    monkeypatch.setattr(
        v2_router.intent_mod,
        "detect_intent",
        lambda m, b: "info" if "parking" in m.lower() else original_detect(m, b),
    )
    monkeypatch.setattr(v2_router.info_flow, "handle", lambda _m, _b: "Imamo parkirišče.")

    sid = "terminal-info-resume"
    client.post("/v2/chat", json={"message": "Rad bi rezerviral sobo", "session_id": sid})
    client.post("/v2/chat", json={"message": "12.12.2099", "session_id": sid})
    client.post("/v2/chat", json={"message": "3", "session_id": sid})
    client.post("/v2/chat", json={"message": "4", "session_id": sid})
    client.post("/v2/chat", json={"message": "2", "session_id": sid})  # awaiting_kids_ages

    res = client.post("/v2/chat", json={"message": "Imate parking?", "session_id": sid})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "nadaljujmo z rezervacijo" in reply
    assert "koliko so stari" in reply


def test_v2_awaiting_email_accepts_email_without_info_detour(client, monkeypatch):
    # Force intent detector towards info to prove terminal guard still treats raw email as input.
    monkeypatch.setattr(v2_router.intent_mod, "detect_intent", lambda _m, _b: "info")

    sid = "awaiting-email-direct-input"
    session = chat_state.get_session(sid)
    session.active_flow = "reservation"
    session.step = "awaiting_email"
    session.data["reservation"] = {
        "step": "awaiting_email",
        "type": "room",
        "name": "Miha Novak",
        "phone": "041123456",
        "terminal_interrupt_count": 0,
        "awaiting_cancel_confirmation": False,
    }

    res = client.post("/v2/chat", json={"message": "satlermarko@gmail.com", "session_id": sid})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "kam naj pošljem" not in reply
    assert "nadaljujmo z rezervacijo" not in reply
    assert "kontakt:" not in reply
    assert ("večerje" in reply) or ("želite še kaj sporočiti" in reply)

    updated = chat_state.get_session(sid).data["reservation"]
    assert updated.get("email") == "satlermarko@gmail.com"
    assert updated.get("step") != "awaiting_email"


def test_v2_awaiting_dinner_da_does_not_detour_to_help(client, monkeypatch):
    # Force a noisy intent to prove terminal guard still consumes valid dinner answer.
    monkeypatch.setattr(v2_router.intent_mod, "detect_intent", lambda _m, _b: "help")

    sid = "awaiting-dinner-direct-input"
    session = chat_state.get_session(sid)
    session.active_flow = "reservation"
    session.step = "awaiting_dinner"
    session.data["reservation"] = {
        "step": "awaiting_dinner",
        "type": "room",
        "date": "12.03.2026",
        "nights": 4,
        "name": "Miha Novak",
        "phone": "041123456",
        "email": "satlermarko@gmail.com",
        "terminal_interrupt_count": 0,
        "awaiting_cancel_confirmation": False,
    }

    res = client.post("/v2/chat", json={"message": "DA", "session_id": sid})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "nadaljujmo z rezervacijo" not in reply
    assert "lahko odgovorim na info vprašanje" not in reply
    assert ("za koliko oseb želite večerje" in reply) or ("večerje ob ponedeljkih in torkih" in reply)

    updated = chat_state.get_session(sid).data["reservation"]
    assert updated.get("step") == "awaiting_dinner_count"


def test_v2_info_returns_structured_6_course_menu(client):
    res = client.post("/v2/chat", json={"message": "Kaj ponujate v 6 hodnem meniju?"})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "6-hodni" in reply
    assert "cena: 53 eur" in reply


def test_v2_info_returns_seasonal_weekend_menu_for_april(client):
    res = client.post("/v2/chat", json={"message": "Kakšna je vikend ponudba za april?"})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "marec–maj" in reply or "marec-maj" in reply
    assert "cena: 36 eur" in reply


def test_v2_info_style_not_uniform_for_repeated_question(client):
    sid = "info-style-rotation"
    first = client.post("/v2/chat", json={"message": "Kakšno vino ponujate?", "session_id": sid})
    second = client.post("/v2/chat", json={"message": "Kakšno vino ponujate?", "session_id": sid})
    assert first.status_code == 200
    assert second.status_code == 200
    reply_1 = first.json()["reply"]
    reply_2 = second.json()["reply"]
    assert "vino" in reply_1.lower() or "vin" in reply_1.lower()
    assert "vino" in reply_2.lower() or "vin" in reply_2.lower()
    assert reply_1 != reply_2


def test_v2_info_weekly_menu_query_does_not_start_inquiry(client):
    res = client.post("/v2/chat", json={"message": "Kaj pa čez teden?"})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "povpraševanje" not in reply
    assert "4-hodni" in reply
    assert "7-hodni" in reply


def test_v2_info_vikend_query_returns_seasonal_menu_without_weekly_line(client):
    res = client.post("/v2/chat", json={"message": "Kaj pa čez vikend?"})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert ("marec" in reply) or ("junij" in reply) or ("september" in reply) or ("december" in reply)
    assert "med tednom (" not in reply


def test_v2_info_traktor_question_does_not_start_inquiry(client):
    res = client.post("/v2/chat", json={"message": "Imate traktor?"})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "povpraševanje" not in reply
    assert ("nimam potrjenega" in reply) or ("kmetij" in reply) or ("preverimo" in reply)


def test_v2_info_gospodar_question_returns_direct_answer(client):
    res = client.post("/v2/chat", json={"message": "Kdo je gospodar kmetije?"})
    assert res.status_code == 200
    reply = res.json()["reply"].lower()
    assert "družina kovačnik" in reply
