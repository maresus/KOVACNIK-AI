import sys
from datetime import datetime
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
