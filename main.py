from pathlib import Path
import sys

from dotenv import load_dotenv

# Nalozi .env pred uvozom modulov, ki berejo environment na import time.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Allow importing the 2026/app2026 package without a new repo.
sys.path.insert(0, str(Path(__file__).resolve().parent / "2026"))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.config import Settings
from app.rag.chroma_service import get_chroma_health
from app.rag.knowledge_base import get_knowledge_base_health
from app2026.chat.router import router as chat_v2_router
from app.services.reservation_router import router as reservation_router
from app.services.admin_router import router as admin_router
from app.services.webhook_router import router as webhook_router
from app.services.imap_poll_service import start_imap_poller

settings = Settings()
app = FastAPI(title=settings.project_name)
BASE_DIR = Path(__file__).resolve().parent

@app.on_event("startup")
def startup_tasks() -> None:
    start_imap_poller()
    kb_health = get_knowledge_base_health()
    print(f"[startup][kb] {kb_health}")

    chroma_health = get_chroma_health()
    print(f"[startup][chroma] {chroma_health}")
    if not chroma_health.get("ready"):
        print(
            "[startup][chroma] Chroma ni pripravljen; uporabljam fallback (knowledge.jsonl + BM25 + embeddings)."
        )

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def chat_ui() -> HTMLResponse:
    """
    Preprost UI za testiranje Kovačnik AI chata.
    Streže datoteko static/chat.html iz root mape projekta.
    """
    html_path = BASE_DIR / "static" / "chat.html"
    if not html_path.exists():
        return HTMLResponse(
            "<h1>Chat UI ni najden.</h1><p>Manjka datoteka static/chat.html.</p>",
            status_code=500,
        )
    html = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html, headers={"X-UI-Source": str(html_path)})

@app.get("/widget", response_class=HTMLResponse)
def widget_ui() -> HTMLResponse:
    """
    Widget verzija chata za embed v WordPress.
    """
    html_path = BASE_DIR / "static" / "widget.html"
    if not html_path.exists():
        return HTMLResponse(
            "<h1>Widget ni najden.</h1>",
            status_code=500,
        )
    html = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html, headers={"X-UI-Source": str(html_path)})


@app.get("/debug/ui-source")
def debug_ui_source() -> dict[str, str]:
    chat = BASE_DIR / "static" / "chat.html"
    widget = BASE_DIR / "static" / "widget.html"
    return {
        "base_dir": str(BASE_DIR),
        "chat_ui": str(chat),
        "chat_ui_exists": str(chat.exists()).lower(),
        "widget_ui": str(widget),
        "widget_ui_exists": str(widget.exists()).lower(),
    }


@app.api_route("/chat", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.api_route("/chat/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.api_route("/chat/stream", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def legacy_chat_disabled(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={
            "detail": "Legacy endpoint '/chat' is intentionally disabled. Use '/v2/chat'.",
            "path": str(request.url.path),
        },
    )

def configure_routes() -> None:
    app.include_router(chat_v2_router)
    app.include_router(reservation_router)
    app.include_router(admin_router)
    app.include_router(webhook_router)

configure_routes()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
