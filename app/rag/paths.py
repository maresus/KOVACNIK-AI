from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import Settings

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_PATH = BASE_DIR / "knowledge.jsonl"


def resolve_knowledge_path(raw_path: str | None) -> Path:
    if not raw_path:
        return DEFAULT_KNOWLEDGE_PATH
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


@lru_cache(maxsize=1)
def get_knowledge_path() -> Path:
    settings = Settings()
    return resolve_knowledge_path(settings.knowledge_path)
