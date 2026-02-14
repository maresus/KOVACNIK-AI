from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app2026.chat_v3.intents import ALL_INTENTS

_ALLOWED_INTENTS = set(ALL_INTENTS)


class InterpretResult(BaseModel):
    intent: str = Field(default="UNCLEAR")
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    continue_flow: bool = Field(default=False)
    needs_clarification: bool = Field(default=False)
    clarification_question: str | None = Field(default=None)

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, value: Any) -> str:
        text = str(value or "UNCLEAR").strip().upper()
        if text not in _ALLOWED_INTENTS:
            return "UNCLEAR"
        return text

    @field_validator("entities", mode="before")
    @classmethod
    def normalize_entities(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @field_validator("clarification_question", mode="before")
    @classmethod
    def normalize_clarification_question(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
