from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.config import Settings
from app.core.chat_service import get_reply
from app.core.db import init_db, get_sessions, get_messages, get_stats

load_dotenv()

settings = Settings()
app = FastAPI(title=settings.project_name)

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def chat_ui() -> HTMLResponse:
    html_path = Path("static/chat.html")
    if not html_path.exists():
        return HTMLResponse("<h1>chat.html ni najden</h1>", status_code=500)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/widget", response_class=HTMLResponse)
def widget_ui() -> HTMLResponse:
    html_path = Path("static/widget.html")
    if not html_path.exists():
        return HTMLResponse("<h1>widget.html ni najden</h1>", status_code=500)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/chat/", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    reply = get_reply(req.session_id, req.message)
    return ChatResponse(reply=reply)


@app.get("/admin", response_class=HTMLResponse)
def admin_ui() -> HTMLResponse:
    html_path = Path("static/admin.html")
    if not html_path.exists():
        return HTMLResponse("<h1>admin.html ni najden</h1>", status_code=500)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/admin/stats")
def admin_stats() -> dict:
    return get_stats()


@app.get("/admin/sessions")
def admin_sessions() -> list:
    return get_sessions()


@app.get("/admin/sessions/{session_id}")
def admin_session_detail(session_id: str) -> list:
    return get_messages(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
