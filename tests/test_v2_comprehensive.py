"""
30 comprehensive live tests for /v2/chat.

Run:
    pytest tests/test_v2_comprehensive.py -v --base-url=https://kovacnik-ai-production.up.railway.app
"""

from __future__ import annotations

import uuid
import re
from typing import Any

import httpx
import pytest


class V2ChatClient:
    def __init__(self, base_url: str, session_id: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id or str(uuid.uuid4())
        self.history: list[dict[str, str]] = []

    def send(self, message: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/v2/chat",
                json={"message": message, "session_id": self.session_id},
            )
        response.raise_for_status()
        data = response.json()
        self.history.append({"user": message, "bot": str(data.get("reply", ""))})
        return data

    def get_reply(self, message: str) -> str:
        return str(self.send(message).get("reply", ""))


@pytest.fixture()
def base_url(request: pytest.FixtureRequest) -> str:
    return str(request.config.getoption("--base-url"))


@pytest.fixture()
def chat(base_url: str) -> V2ChatClient:
    return V2ChatClient(base_url)


def _has_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(w.lower() in lowered for w in words)


def _drive_room_to_name(chat: V2ChatClient) -> str:
    r = chat.get_reply("Rad bi rezerviral sobo")
    assert _has_any(r, ["datum", "prihod"])
    r = chat.get_reply("25.7.2026")
    assert _has_any(r, ["nočit", "koliko"])
    r = chat.get_reply("3")
    assert _has_any(r, ["oseb", "odras"])
    r = chat.get_reply("2 odrasla")
    if _has_any(r, ["imate otroke", "otroci"]):
        r = chat.get_reply("ne")
    if _has_any(r, ["proste imamo", "katero bi želeli", "izberite med"]):
        r = chat.get_reply("JULIJA")
    return r


def _extract_date(text: str) -> str | None:
    m = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b", text)
    return m.group(1) if m else None


def _drive_table_to_name(chat: V2ChatClient) -> str:
    r = chat.get_reply("Rad bi rezerviral mizo")
    assert _has_any(r, ["datum", "sobota", "nedelja"])
    r = chat.get_reply("26.7.2026")
    assert _has_any(r, ["ura", "uri", "čas"])
    r = chat.get_reply("13:00")
    assert _has_any(r, ["oseb", "koliko"])
    r = chat.get_reply("4 osebe")
    if _has_any(r, ["otroke", "otroci"]):
        r = chat.get_reply("ne")
    if _has_any(r, ["jedilnic", "pri peči", "pri vrtu"]):
        r = chat.get_reply("Pri peči")
    return r


class Test01Greetings:
    def test_01_hello(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Živjo"), ["pozdrav", "pomagam", "živjo"])

    def test_02_good_day(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Dober dan"), ["pozdrav", "pomagam", "dan"])

    def test_03_bye(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Hvala, adijo"), ["hvala", "nasvid", "pozdrav"])


class Test02Info:
    def test_04_location(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Kje se nahajate?"), ["lokacij", "planica", "naslov"])

    def test_05_contact(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Kakšen je vaš telefon?"), ["telefon", "kontakt", "041", "386"])

    def test_06_hours(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Kdaj ste odprti?"), ["sobota", "nedelja", "odprt", "ura"])

    def test_07_room_price(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Koliko stane soba?"), ["cena", "€", "eur", "noč"])

    def test_08_breakfast(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Kdaj je zajtrk?"), ["zajtrk", "8", "9"])

    def test_09_parking(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Imate parking?"), ["parking", "parkiri", "brezplač"])

    def test_10_menu(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Kaj je na jedilniku?"), ["jedilnik", "meni", "kosilo", "hrana"])


class Test03RoomHappyPath:
    def test_11_room_start(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Rad bi rezerviral sobo"), ["datum", "prihod"])

    def test_12_room_date(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        assert _has_any(chat.get_reply("25.7.2026"), ["nočit", "koliko"])

    def test_13_room_nights(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        chat.get_reply("25.7.2026")
        assert _has_any(chat.get_reply("3 noči"), ["oseb", "odras"])

    def test_14_room_people(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        chat.get_reply("25.7.2026")
        chat.get_reply("3")
        r = chat.get_reply("2 odrasla")
        assert _has_any(r, ["otro", "sobo", "proste", "ime", "priimek", "nimamo dovolj", "najbližji prost termin"])

    def test_15_room_full(self, chat: V2ChatClient) -> None:
        r = _drive_room_to_name(chat)
        if _has_any(r, ["nimamo dovolj prostih sob", "najbližji prost termin"]):
            suggested = _extract_date(r)
            if suggested:
                r = chat.get_reply(suggested)
                if _has_any(r, ["nočit", "koliko"]):
                    chat.get_reply("3")
                    r = chat.get_reply("2 odrasla")
                    if _has_any(r, ["imate otroke", "otroci"]):
                        r = chat.get_reply("ne")
                    if _has_any(r, ["proste imamo", "katero bi želeli", "izberite med"]):
                        r = chat.get_reply("JULIJA")
        assert _has_any(r, ["ime", "priimek", "nosilec", "telefon", "številk"])
        assert _has_any(chat.get_reply("Test Testovic"), ["telefon", "številk"])
        assert _has_any(chat.get_reply("041111222"), ["email", "e-pošt"])
        assert _has_any(chat.get_reply("test@example.com"), ["večerj", "opomb", "želite"])
        r = chat.get_reply("ne")
        assert _has_any(r, ["opomb", "sporoč", "prever", "potrdi"])
        if _has_any(r, ["opomb", "sporoč"]):
            r = chat.get_reply("ne")
        assert _has_any(r, ["potrd", "prever", "podatk"])
        r = chat.get_reply("da")
        assert _has_any(r, ["prejeto", "potrdit", "zabelež", "povpraševanje"])


class Test04TableHappyPath:
    def test_16_table_start(self, chat: V2ChatClient) -> None:
        assert _has_any(chat.get_reply("Rad bi rezerviral mizo za kosilo"), ["datum", "sobota", "nedelja"])

    def test_17_table_date_time(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral mizo")
        assert _has_any(chat.get_reply("26.7.2026"), ["ura", "uri", "čas"])

    def test_18_table_full(self, chat: V2ChatClient) -> None:
        r = _drive_table_to_name(chat)
        if _has_any(r, ["ime", "priimek", "nosil"]):
            r = chat.get_reply("Test Testovic")
        assert _has_any(r, ["telefon", "številk"])
        assert _has_any(chat.get_reply("041333444"), ["email", "e-pošt"])
        r = chat.get_reply("test@example.com")
        if _has_any(r, ["opomb", "sporoč"]):
            r = chat.get_reply("ne")
        if _has_any(r, ["potrdi", "prever"]):
            r = chat.get_reply("da")
        assert _has_any(r, ["prejeto", "potrdit", "zabelež", "rezervacij"])


class Test05TerminalGuards:
    def test_19_interrupt_at_name(self, chat: V2ChatClient) -> None:
        _drive_room_to_name(chat)
        r = chat.get_reply("Kje se nahajate?")
        assert not _has_any(r, ["planica", "naslov", "kungota"])
        assert _has_any(r, ["ime", "telefon", "priimek", "datum", "sobo"])

    def test_20_interrupt_at_phone(self, chat: V2ChatClient) -> None:
        _drive_room_to_name(chat)
        chat.get_reply("Test User")
        r = chat.get_reply("Koliko stane soba?")
        assert not _has_any(r, ["€", "eur", "cena", "od 140"])
        assert _has_any(r, ["telefon", "številk", "email", "datum", "sobo"])

    def test_21_interrupt_at_email(self, chat: V2ChatClient) -> None:
        _drive_room_to_name(chat)
        chat.get_reply("Test User")
        chat.get_reply("041555666")
        r = chat.get_reply("Kakšen je vaš email?")
        assert _has_any(r, ["email", "e-pošt", "naslov", "datum", "sobo"])

    def test_22_ne_not_cancel_at_kids(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        chat.get_reply("25.7.2026")
        chat.get_reply("3")
        chat.get_reply("2 odrasla")
        r = chat.get_reply("ne")
        assert "preklical" not in r.lower()
        assert _has_any(r, ["sobo", "proste", "katero"])

    def test_23_ne_not_cancel_at_dinner(self, chat: V2ChatClient) -> None:
        _drive_room_to_name(chat)
        chat.get_reply("Test User")
        chat.get_reply("041777888")
        chat.get_reply("test@test.com")
        r = chat.get_reply("ne")
        assert "preklical" not in r.lower()
        assert _has_any(r, ["opomb", "sporoč", "prever"])


class Test06SessionIsolation:
    def test_24_two_sessions_isolated(self, base_url: str) -> None:
        a = V2ChatClient(base_url, "isolation-A")
        b = V2ChatClient(base_url, "isolation-B")
        a.get_reply("Rad bi rezerviral sobo")
        a.get_reply("25.7.2026")
        rb = b.get_reply("Kakšna vina imate?")
        assert _has_any(rb, ["vina", "lokalna"])
        ra = a.get_reply("3 noči")
        assert _has_any(ra, ["oseb", "koliko", "nimamo dovolj", "najbližji prost termin"])

    def test_25_two_sessions_two_flows(self, base_url: str) -> None:
        room = V2ChatClient(base_url, "room-flow")
        table = V2ChatClient(base_url, "table-flow")
        room.get_reply("Rad bi rezerviral sobo")
        rr = room.get_reply("25.7.2026")
        table.get_reply("Rad bi rezerviral mizo")
        rt = table.get_reply("26.7.2026")
        assert _has_any(rr, ["nočit"])
        assert _has_any(rt, ["ura", "uri", "čas"])

    def test_26_session_id_returned(self, chat: V2ChatClient) -> None:
        data = chat.send("Živjo")
        assert data["session_id"] == chat.session_id


class Test07EdgeCases:
    def test_27_past_date_rejected(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        r = chat.get_reply("15.1.2020")
        if not _has_any(r, ["pretekl", "mimo", "prihodnost", "drug"]):
            r = chat.get_reply("2")
        assert _has_any(r, ["pretekl", "mimo", "prihodnost", "drug", "datum je že mimo"])

    def test_28_closed_day_signal(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        r = chat.get_reply("20.7.2026")
        # depending on validator, this can appear now or after nights input
        if not _has_any(r, ["pon", "tor", "zaprto", "drug datum"]):
            r = chat.get_reply("2")
        assert _has_any(r, ["pon", "tor", "zaprto", "drug datum", "drug"])

    def test_29_explicit_cancel(self, chat: V2ChatClient) -> None:
        chat.get_reply("Rad bi rezerviral sobo")
        chat.get_reply("25.7.2026")
        r = chat.get_reply("prekini")
        assert _has_any(r, ["preklical", "prekin", "kako vam"])

    def test_30_empty_message(self, chat: V2ChatClient) -> None:
        r = chat.get_reply("")
        assert isinstance(r, str)
