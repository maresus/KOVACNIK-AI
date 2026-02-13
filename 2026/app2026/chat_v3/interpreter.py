from __future__ import annotations

import json
from typing import Any

from app.core.config import Settings
from app.core.llm_client import get_llm_client
from app2026.chat_v3.schemas import INTERPRETER_INTENTS, Interpretation

_settings = Settings()

SYSTEM_PROMPT = f"""
Si parser namere za Domačijo Kovačnik.
Vrni samo JSON objekt s ključi:
- intent: ena izmed {", ".join(INTERPRETER_INTENTS)}
- entities: objekt z izluščenimi podatki
- confidence: število 0..1
- continue_flow: true/false

Pravila:
- Upoštevaj kontekst pogovora in trenutno stanje.
- Če je uporabnik nejasen, vrni intent "UNCLEAR".
- Ne dodajaj dodatnih polj.
""".strip()


def _extract_text_from_response(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    outputs: list[str] = []
    for block in getattr(response, "output", []) or []:
        for content in getattr(block, "content", []) or []:
            chunk = getattr(content, "text", None)
            if chunk:
                outputs.append(chunk)
    return "\n".join(outputs).strip()


def parse_intent(message: str, history: list[dict[str, str]], state: dict[str, Any]) -> Interpretation:
    context = history[-5:] if isinstance(history, list) else []
    state_snapshot = state if isinstance(state, dict) else {}

    user_payload = {
        "message": message,
        "history": context,
        "state": state_snapshot,
    }

    try:
        client = get_llm_client()
        response = client.responses.create(
            model=_settings.v3_intent_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            max_output_tokens=220,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = _extract_text_from_response(response)
        if not raw:
            return Interpretation()
        data = json.loads(raw)
        if not isinstance(data, dict):
            return Interpretation()
        return Interpretation(**data)
    except Exception:
        return Interpretation()
