from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

INTERPRETER_INTENTS = [
    "BOOKING_ROOM",
    "BOOKING_TABLE",
    "INFO_MENU",
    "INFO_MENU_DETAIL",
    "INFO_LOCATION",
    "INFO_CONTACT",
    "INFO_PRICING",
    "INFO_HOURS",
    "INFO_WINE",
    "INFO_GENERAL",
    "INQUIRY_START",
    "INQUIRY_CONTINUE",
    "CANCEL",
    "CONFIRM",
    "CONTINUE_FLOW",
    "GREETING",
    "SMALLTALK",
    "UNCLEAR",
]

_ALLOWED_INTENTS = set(INTERPRETER_INTENTS)


class Interpretation(BaseModel):
    intent: str = Field(default="UNCLEAR")
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    continue_flow: bool = Field(default=False)

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, value: Any) -> str:
        text = str(value or "UNCLEAR").strip().upper()
        if text not in _ALLOWED_INTENTS:
            return "UNCLEAR"
        return text
