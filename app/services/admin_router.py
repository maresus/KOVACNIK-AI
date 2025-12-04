from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/admin", tags=["admin"])
service = ReservationService()


class StatusUpdate(BaseModel):
    status: str


class AvailabilityCheck(BaseModel):
    reservation_type: str
    date: str
    nights: Optional[int] = None
    people: int
    rooms: Optional[int] = None
    time: Optional[str] = None


@router.get("", response_class=HTMLResponse)
def admin_page() -> HTMLResponse:
    """
    Postreže statično datoteko admin UI (static/admin.html).
    """
    html_path = Path("static/admin.html")
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI manjka (static/admin.html)</h1>", status_code=500)
    html = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@router.post("/backup")
def trigger_backup() -> dict:
    """
    Ročno sproži CSV backup iz SQLite.
    """
    path = service.create_backup_csv()
    return {"message": "Backup created", "path": str(path)}


@router.patch("/reservations/{reservation_id}/status")
def update_reservation_status(reservation_id: int, update: StatusUpdate) -> dict:
    """Posodobi status rezervacije."""
    if update.status not in ("pending", "confirmed", "cancelled"):
        return {"error": "Invalid status. Use: pending, confirmed, cancelled"}

    success = service.update_status(reservation_id, update.status)
    if success:
        return {"message": "Status updated", "id": reservation_id, "status": update.status}
    return {"error": "Reservation not found"}


@router.post("/check-availability")
def check_availability(check: AvailabilityCheck) -> dict:
    """Preveri razpoložljivost pred dodajanjem rezervacije."""
    if check.reservation_type == "room":
        ok, msg = service.validate_room_rules(check.date, check.nights or 2)
        if not ok:
            return {"available": False, "message": msg}

        rooms_needed = check.rooms or service._rooms_needed(check.people)
        available, alternative = service.check_room_availability(
            check.date, check.nights or 2, check.people, rooms_needed
        )
        if not available:
            msg = "Ni prostih sob za ta termin."
            if alternative:
                msg += f" Najbližji prosti termin: {alternative}"
            return {"available": False, "message": msg, "alternative": alternative}

        free_rooms = service.available_rooms(check.date, check.nights or 2)
        return {"available": True, "free_rooms": free_rooms}

    if check.reservation_type == "table":
        ok, msg = service.validate_table_rules(check.date, check.time or "12:00")
        if not ok:
            return {"available": False, "message": msg}

        available, location, suggestions = service.check_table_availability(
            check.date, check.time or "12:00", check.people
        )
        if not available:
            msg = "Ni prostih miz za ta termin."
            if suggestions:
                msg += f" Predlogi: {', '.join(suggestions[:3])}"
            return {"available": False, "message": msg, "suggestions": suggestions}

        return {"available": True, "suggested_location": location}

    return {"available": False, "message": "Neveljaven tip rezervacije"}
