import csv
import math
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from app.models.reservation import ReservationRecord


ROOMS = [
    {"id": "ALJAZ", "name": "Soba ALJAŽ - Soba z balkonom (2 + 2)", "capacity": 4},
    {
        "id": "JULIJA",
        "name": "Soba JULIJA - Družinska soba z balkonom (2 odrasla + 2 otroka)",
        "capacity": 4,
    },
    {
        "id": "ANA",
        "name": "Soba ANA - Družinska soba z dvema spalnicama (2 odrasla + 2 otroka)",
        "capacity": 4,
    },
]
ROOM_NAME_MAP = {
    "aljaž": "ALJAZ",
    "aljaz": "ALJAZ",
    "jULIJA".lower(): "JULIJA",
    "julija": "JULIJA",
    "ana": "ANA",
}

DINING_ROOMS = [
    {"id": "PRI_PECI", "name": "Jedilnica Pri peči", "capacity": 15},
    {"id": "PRI_VRTU", "name": "Jedilnica Pri vrtu", "capacity": 35},
]
TOTAL_TABLE_CAPACITY = sum(r["capacity"] for r in DINING_ROOMS)
MAX_NIGHTS = 30

ROOM_CLOSED_DAYS = {0, 1}  # pon, tor
TABLE_OPEN_DAYS = {5, 6}  # sob, ned
LAST_LUNCH_ARRIVAL_HOUR = 15
OPENING_START_HOUR = 12
OPENING_END_HOUR = 20


class ReservationService:
    def __init__(self) -> None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.csv_path = os.path.join(project_root, "reservations.csv")
        self.data_dir = os.path.join(project_root, "data")
        self.backup_dir = os.path.join(project_root, "backups")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "reservations.db")
        self._ensure_db()
        self._import_csv_if_empty()

    # --- DB helpers ------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    nights INTEGER,
                    rooms INTEGER,
                    people INTEGER NOT NULL,
                    reservation_type TEXT NOT NULL,
                    time TEXT,
                    location TEXT,
                    name TEXT,
                    phone TEXT,
                    email TEXT,
                    note TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL
                )
                """
            )
            # dodaj manjkajoče stolpce za stare tabele
            info = conn.execute("PRAGMA table_info(reservations)").fetchall()
            existing_cols = {row[1] for row in info}
            if "rooms" not in existing_cols:
                conn.execute("ALTER TABLE reservations ADD COLUMN rooms INTEGER;")
            if "status" not in existing_cols:
                conn.execute("ALTER TABLE reservations ADD COLUMN status TEXT DEFAULT 'pending';")
            conn.commit()

    def _import_csv_if_empty(self) -> None:
        with self._conn() as conn:
            cursor = conn.execute("SELECT COUNT(1) FROM reservations")
            count = cursor.fetchone()[0]
            if count > 0 or not os.path.exists(self.csv_path):
                return
        # preberi obstoječi csv in ga zapiši v sqlite
        legacy_rows = self._read_legacy_csv()
        if not legacy_rows:
            return
        with self._conn() as conn:
            for row in legacy_rows:
                conn.execute(
                    """
                    INSERT INTO reservations
                    (date, nights, people, reservation_type, time, location, name, phone, email, created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("date", ""),
                        int(row.get("nights") or 0) or None,
                        int(row.get("people") or 0),
                        row.get("reservation_type") or row.get("type") or "room",
                        row.get("time") or None,
                        row.get("location") or None,
                        row.get("name") or None,
                        row.get("phone") or None,
                        row.get("email") or None,
                        row.get("created_at") or datetime.now().isoformat(),
                        row.get("source") or "import",
                    ),
                )
            conn.commit()

    # --- helpers ---------------------------------------------------------
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            return datetime.strptime(date_str.strip(), "%d.%m.%Y")
        except ValueError:
            return None

    def _parse_time(self, time_str: str) -> Optional[str]:
        """Normalize various time inputs to HH:MM."""
        if not time_str:
            return None
        cleaned = time_str.strip().lower()
        cleaned = cleaned.replace("h", ":").replace(".", ":")
        match = re.match(r"^(\d{1,2})(?::(\d{2}))?$", cleaned)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        if hour > 23 or minute > 59:
            return None
        return f"{hour:02d}:{minute:02d}"

    def _room_min_nights(self, arrival: datetime) -> int:
        return 3 if arrival.month in {6, 7, 8} else 2

    def _rooms_needed(self, people: int) -> int:
        return max(1, math.ceil(people / 4))

    def _normalize_room_location(self, location: Optional[str]) -> list[str]:
        if not location:
            return []
        lowered = location.lower()
        selected = []
        for key, rid in ROOM_NAME_MAP.items():
            if key in lowered and rid not in selected:
                selected.append(rid)
        return selected

    def _room_calendar(self) -> dict[str, set[str]]:
        """Vrne slovar room_id -> set datumov (dd.mm.yyyy) ki so zasedeni."""
        calendar: dict[str, set[str]] = {r["id"]: set() for r in ROOMS}
        for reservation in self._fetch_reservations():
            if reservation.reservation_type != "room":
                continue
            if reservation.status == "cancelled":
                continue
            if not reservation.nights:
                continue
            if reservation.nights > MAX_NIGHTS:
                continue
            if reservation.nights > MAX_NIGHTS:
                continue
            arrival = self._parse_date(reservation.date)
            if not arrival:
                continue
            dates = [(arrival + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(reservation.nights)]
            assigned = self._normalize_room_location(reservation.location)
            rooms_to_mark = assigned if assigned else [r["id"] for r in ROOMS]
            rooms_needed = reservation.rooms or self._rooms_needed(reservation.people)
            # če nimamo točne sobe, zapolnimo prve proste
            filled = 0
            for room_id in rooms_to_mark:
                if filled >= rooms_needed:
                    break
                # preveri, ali je soba prosta za vse datume
                if all(date not in calendar[room_id] for date in dates):
                    for d in dates:
                        calendar[room_id].add(d)
                    filled += 1
            # če še vedno kaj manjka, zapolnimo preostale
            if filled < rooms_needed:
                for room_id in [r["id"] for r in ROOMS]:
                    if filled >= rooms_needed:
                        break
                    if all(date not in calendar[room_id] for date in dates):
                        for d in dates:
                            calendar[room_id].add(d)
                        filled += 1
        return calendar

    def available_rooms(self, arrival_str: str, nights: int) -> list[str]:
        arrival = self._parse_date(arrival_str)
        if not arrival:
            return []
        dates = [(arrival + timedelta(days=offset)).strftime("%d.%m.%Y") for offset in range(nights)]
        calendar = self._room_calendar()
        free = []
        for room_id in [r["id"] for r in ROOMS]:
            occupied = calendar.get(room_id, set())
            if all(d not in occupied for d in dates):
                free.append(room_id)
        return free

    def _room_occupancy(self) -> dict[str, int]:
        occupancy: dict[str, int] = defaultdict(int)
        for reservation in self._fetch_reservations():
            if reservation.reservation_type != "room":
                continue
            if reservation.status == "cancelled":
                continue
            if not reservation.nights:
                continue
            arrival = self._parse_date(reservation.date)
            if not arrival:
                continue
            rooms_needed = reservation.rooms or self._rooms_needed(reservation.people)
            for offset in range(reservation.nights):
                day = (arrival + timedelta(days=offset)).strftime("%d.%m.%Y")
                occupancy[day] += rooms_needed
        return occupancy

    def _table_room_occupancy(self) -> dict[tuple[str, str, str], int]:
        occupancy: dict[tuple[str, str, str], int] = defaultdict(int)
        for reservation in self._fetch_reservations():
            if reservation.reservation_type != "table":
                continue
            if reservation.status == "cancelled":
                continue
            if not reservation.time:
                continue
            room_key = reservation.location or "Jedilnica Pri vrtu"
            key = (reservation.date, reservation.time, room_key)
            occupancy[key] += reservation.people
        return occupancy

    # --- availability ----------------------------------------------------
    def validate_room_rules(self, arrival_str: str, nights: int) -> Tuple[bool, str]:
        arrival = self._parse_date(arrival_str)
        if not arrival:
            return False, "Tega datuma ne razumem. Prosimo uporabite obliko DD.MM.YYYY (npr. 12.7.2025)."
        today = datetime.now().date()
        if arrival.date() < today:
            today_str = today.strftime("%d.%m.%Y")
            return False, f"Ta datum je že mimo (danes je {today_str}). Prosimo izberite datum v prihodnosti."
        if arrival.weekday() in ROOM_CLOSED_DAYS:
            return (
                False,
                "Sobe so ob ponedeljkih in torkih zaprte, bivanje je možno od srede do nedelje. Prosimo izberite drug datum prihoda.",
            )
        if nights <= 1:
            return False, "Rezervacija ene nočitve pri nas ni možna. Prosimo izberite več nočitev."
        if nights > MAX_NIGHTS:
            return False, f"Maksimalno število nočitev v eni rezervaciji je {MAX_NIGHTS}. Prosimo izberite manj dni."
        min_nights = self._room_min_nights(arrival)
        if nights < min_nights:
            if arrival.month in {6, 7, 8}:
                return (
                    False,
                    "V juniju, juliju in avgustu je minimalno 3 nočitve. Prosimo izberite vsaj 3 nočitve.",
                )
            return False, "V tem terminu je minimalno 2 nočitvi. Prosimo izberite vsaj 2 nočitvi."
        return True, ""

    def check_room_availability(
        self, arrival_str: str, nights: int, people: int, rooms: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        arrival = self._parse_date(arrival_str)
        if not arrival:
            return False, None
        if people <= 0:
            return False, None
        rooms_needed = rooms or self._rooms_needed(people)
        if rooms_needed > len(ROOMS):
            return False, None

        occupancy = self._room_occupancy()
        for offset in range(nights):
            day = (arrival + timedelta(days=offset)).strftime("%d.%m.%Y")
            used = occupancy.get(day, 0)
            if used + rooms_needed > len(ROOMS):
                alternative = self.suggest_room_alternative(arrival, nights, rooms_needed)
                return False, alternative
        return True, None

    def suggest_room_alternative(
        self, arrival: datetime, nights: int, rooms_needed: int
    ) -> Optional[str]:
        occupancy = self._room_occupancy()
        for delta in range(1, 31):
            candidate = arrival + timedelta(days=delta)
            if candidate.weekday() in ROOM_CLOSED_DAYS:
                continue
            min_nights = self._room_min_nights(candidate)
            if nights < min_nights:
                continue
            fits = True
            for offset in range(nights):
                day = (candidate + timedelta(days=offset)).strftime("%d.%m.%Y")
                if occupancy.get(day, 0) + rooms_needed > len(ROOMS):
                    fits = False
                    break
            if fits:
                return candidate.strftime("%d.%m.%Y")
        return None

    def validate_table_rules(self, date_str: str, time_str: str) -> Tuple[bool, str]:
        dining_day = self._parse_date(date_str)
        if not dining_day:
            return False, "Datum prosimo v obliki DD.MM.YYYY (npr. 15.6.2025)."
        today = datetime.now().date()
        if dining_day.date() < today:
            today_str = today.strftime("%d.%m.%Y")
            return False, f"Ta datum je že mimo (danes je {today_str}). Prosimo izberite datum v prihodnosti."
        if dining_day.weekday() not in TABLE_OPEN_DAYS:
            return False, "Za mize sprejemamo rezervacije ob sobotah in nedeljah med 12:00 in 20:00."
        normalized_time = self._parse_time(time_str)
        if not normalized_time:
            return False, "Uro prosim vpišite v obliki HH:MM (npr. 12:30)."
        hour, minute = map(int, normalized_time.split(":"))
        if hour < OPENING_START_HOUR or hour > OPENING_END_HOUR:
            return False, "Kuhinja obratuje med 12:00 in 20:00. Prosimo izberite uro znotraj tega okna."
        if hour > LAST_LUNCH_ARRIVAL_HOUR or (hour == LAST_LUNCH_ARRIVAL_HOUR and minute > 0):
            return False, "Zadnji prihod na kosilo je ob 15:00. Prosimo izberite zgodnejšo uro."
        return True, ""

    def check_table_availability(
        self, date_str: str, time_str: str, people: int
    ) -> tuple[bool, Optional[str], list[str]]:
        normalized_time = self._parse_time(time_str)
        if not normalized_time:
            return False, None, []
        occupancy = self._table_room_occupancy()
        suggestions: list[str] = []

        # global limit čez oba prostora
        total_used = 0
        for room in DINING_ROOMS:
            total_used += occupancy.get((date_str, normalized_time, room["name"]), 0)
        if total_used + people > TOTAL_TABLE_CAPACITY:
            suggestions = self.suggest_table_slots(date_str, people, limit=3)
            return False, None, suggestions

        for room in DINING_ROOMS:
            key = (date_str, normalized_time, room["name"])
            used = occupancy.get(key, 0)
            if used + people <= room["capacity"]:
                return True, room["name"], suggestions

        suggestions = self.suggest_table_slots(date_str, people, limit=3)
        return False, None, suggestions

    def suggest_table_slots(self, date_str: str, people: int, limit: int = 3) -> list[str]:
        slots: list[str] = []
        occupancy = self._table_room_occupancy()
        start_times = []
        for hour in range(OPENING_START_HOUR, LAST_LUNCH_ARRIVAL_HOUR + 1):
            start_times.append(f"{hour:02d}:00")
            if hour != LAST_LUNCH_ARRIVAL_HOUR:
                start_times.append(f"{hour:02d}:30")

        # 1) isti dan
        for t in start_times:
            for room in DINING_ROOMS:
                used = occupancy.get((date_str, t, room["name"]), 0)
                if used + people <= room["capacity"]:
                    slots.append(f"{date_str} ob {t} ({room['name']})")
                    break
            if len(slots) >= limit:
                return slots

        # 2) najbližji vikend v prihodnjih dveh tednih
        parsed_date = self._parse_date(date_str)
        if not parsed_date:
            return slots
        for delta in range(1, 15):
            candidate = parsed_date + timedelta(days=delta)
            if candidate.weekday() not in TABLE_OPEN_DAYS:
                continue
            candidate_str = candidate.strftime("%d.%m.%Y")
            for t in start_times:
                for room in DINING_ROOMS:
                    used = occupancy.get((candidate_str, t, room["name"]), 0)
                    if used + people <= room["capacity"]:
                        slots.append(f"{candidate_str} ob {t} ({room['name']})")
                        break
                if len(slots) >= limit:
                    return slots
        return slots

    # --- CRUD ------------------------------------------------------------
    def create_reservation(
        self,
        date: str,
        people: int,
        reservation_type: str,
        source: str = "chat",
        nights: Optional[int] = None,
        rooms: Optional[int] = None,
        time: Optional[str] = None,
        location: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        note: Optional[str] = None,
        status: str = "pending",
    ) -> Dict[str, Any]:
        created_at = datetime.now().isoformat()
        # Admin / telefon / API vnosi se avtomatsko potrdijo
        if source in ("admin", "phone", "api"):
            status = "confirmed"
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reservations
                (date, nights, rooms, people, reservation_type, time, location, name, phone, email, note, status, created_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date,
                    nights,
                    rooms,
                    people,
                    reservation_type,
                    time,
                    location,
                    name,
                    phone,
                    email,
                    note,
                    status,
                    created_at,
                    source,
                ),
            )
            new_id = cursor.lastrowid
            conn.commit()

        reservation_data = {
            "id": new_id,
            "date": date,
            "nights": nights if nights is not None else "",
            "rooms": rooms if rooms is not None else "",
            "people": people,
            "reservation_type": reservation_type,
            "time": time or "",
            "location": location or "",
            "name": name or "",
            "phone": phone or "",
            "email": email or "",
            "note": note or "",
            "status": status,
            "created_at": created_at,
            "source": source,
        }
        return reservation_data

    def update_status(self, reservation_id: int, new_status: str) -> bool:
        """Posodobi status rezervacije. Vrne True če uspešno."""
        if new_status not in ("pending", "confirmed", "cancelled"):
            return False
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE reservations SET status = ? WHERE id = ?",
                (new_status, reservation_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def read_reservations(self) -> list[Dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT id, date, nights, rooms, people, reservation_type, time, location,
                       name, phone, email, note, status, created_at, source
                FROM reservations
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def _fetch_reservations(self) -> list[ReservationRecord]:
        records: list[ReservationRecord] = []
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT id, date, nights, rooms, people, reservation_type, time, location,
                       name, phone, email, note, status, created_at, source
                FROM reservations
                """
            )
            for row in cursor.fetchall():
                try:
                    people = int(row["people"])
                except (TypeError, ValueError):
                    people = 0
                try:
                    nights = int(row["nights"]) if row["nights"] is not None else None
                except (TypeError, ValueError):
                    nights = None
                try:
                    rooms = int(row["rooms"]) if row["rooms"] is not None else None
                except (TypeError, ValueError):
                    rooms = None
                records.append(
                    ReservationRecord(
                        id=row["id"],
                        date=row["date"],
                        nights=nights,
                        rooms=rooms,
                        people=people,
                        name=row["name"],
                        phone=row["phone"],
                        email=row["email"],
                        created_at=row["created_at"],
                        source=row["source"],
                        reservation_type=row["reservation_type"],
                        time=row["time"],
                        location=row["location"],
                        note=row["note"],
                        status=row["status"],
                    )
                )
        return records

    def _read_legacy_csv(self) -> list[Dict[str, Any]]:
        if not os.path.exists(self.csv_path):
            return []
        reservations: list[Dict[str, Any]] = []
        expected_fields = [
            "date",
            "nights",
            "people",
            "name",
            "phone",
            "email",
            "created_at",
            "source",
            "reservation_type",
            "time",
            "location",
            "note",
        ]
        with open(self.csv_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                first_value = row[0].strip().lower()
                if first_value == "date":
                    continue
                padded = (row + [""] * len(expected_fields))[: len(expected_fields)]
                reservation = {key: value or "" for key, value in zip(expected_fields, padded)}
                reservations.append(reservation)
        return reservations

    def create_backup_csv(self) -> str:
        """Ustvari CSV backup iz SQLite in vrne pot do datoteke."""
        today_str = datetime.now().strftime("%Y%m%d")
        backup_path = os.path.join(self.backup_dir, f"reservations-{today_str}.csv")
        rows = self.read_reservations()
        with open(backup_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "id",
                    "date",
                    "nights",
                    "rooms",
                    "people",
                    "reservation_type",
                    "time",
                    "location",
                    "name",
                    "phone",
                    "email",
                    "note",
                    "status",
                    "created_at",
                    "source",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row.get("id", ""),
                        row.get("date", ""),
                        row.get("nights", ""),
                        row.get("rooms", ""),
                        row.get("people", ""),
                        row.get("reservation_type", ""),
                        row.get("time", ""),
                        row.get("location", ""),
                        row.get("name", ""),
                        row.get("phone", ""),
                        row.get("email", ""),
                        row.get("note", ""),
                        row.get("status", ""),
                        row.get("created_at", ""),
                        row.get("source", ""),
                    ]
                )
        return backup_path
