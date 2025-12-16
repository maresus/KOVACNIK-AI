import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.email_service import (
    send_custom_message,
    send_reservation_confirmed,
    send_reservation_rejected,
)
from app.services.reservation_service import ReservationService

router = APIRouter(tags=["admin"])
service = ReservationService()


class ReservationUpdate(BaseModel):
    status: Optional[str] = None
    date: Optional[str] = None
    people: Optional[int] = None
    nights: Optional[int] = None
    location: Optional[str] = None
    admin_notes: Optional[str] = None


class SendMessageRequest(BaseModel):
    reservation_id: int
    email: str
    subject: str
    body: str
    set_processing: bool = True


@router.get("/admin", response_class=HTMLResponse)
def admin_page() -> HTMLResponse:
    """Postreže statično datoteko admin UI (static/admin.html)."""
    html_path = Path("static/admin.html")
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI manjka (static/admin.html)</h1>", status_code=500)
    html = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@router.get("/api/admin/reservations")
def get_reservations(
    limit: int = 100,
    status: Optional[str] = None,
    type: Optional[str] = None,
    source: Optional[str] = None,
):
    """Vrne seznam rezervacij s filtri ter osnovno statistiko."""
    reservations = service.read_reservations(limit=limit, status=status, reservation_type=type, source=source)

    all_res = service.read_reservations(limit=1000)
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "pending": len([r for r in all_res if r.get("status") == "pending"]),
        "processing": len([r for r in all_res if r.get("status") == "processing"]),
        "confirmed": len([r for r in all_res if r.get("status") == "confirmed"]),
        "today": len([r for r in all_res if str(r.get("created_at", "")).startswith(today_prefix)]),
    }

    return {"reservations": reservations, "stats": stats}


@router.put("/api/admin/reservations/{reservation_id}")
def update_reservation(reservation_id: int, data: ReservationUpdate):
    """Posodobi rezervacijo."""
    ok = service.update_reservation(
        reservation_id,
        status=data.status,
        date=data.date,
        people=data.people,
        nights=data.nights,
        location=data.location,
        admin_notes=data.admin_notes,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Rezervacija ni najdena")
    return {"ok": True}


@router.post("/api/admin/reservations/{reservation_id}/confirm")
def confirm_reservation(reservation_id: int):
    """Potrdi rezervacijo in pošlje email gostu."""
    res = service.get_reservation(reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Rezervacija ni najdena")
    service.update_reservation(
        reservation_id,
        status="confirmed",
        confirmed_at=datetime.now().isoformat(),
        confirmed_by=os.getenv("ADMIN_EMAIL", "info@kovacnik.com"),
    )
    res = service.get_reservation(reservation_id) or res
    send_reservation_confirmed(res)
    return {"ok": True}


@router.post("/api/admin/reservations/{reservation_id}/reject")
def reject_reservation(reservation_id: int):
    """Zavrne rezervacijo in pošlje email gostu."""
    res = service.get_reservation(reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="Rezervacija ni najdena")
    service.update_reservation(reservation_id, status="rejected")
    res = service.get_reservation(reservation_id) or res
    send_reservation_rejected(res)
    return {"ok": True}


@router.post("/api/admin/send-message")
def send_message(data: SendMessageRequest):
    """Pošlje sporočilo gostu in opcijsko status nastavi na 'processing'."""
    if not data.email:
        raise HTTPException(status_code=400, detail="Email manjka")
    send_custom_message(data.email, data.subject, data.body)
    if data.set_processing:
        service.update_reservation(
            data.reservation_id,
            status="processing",
            guest_message=data.body,
        )
    return {"ok": True}

