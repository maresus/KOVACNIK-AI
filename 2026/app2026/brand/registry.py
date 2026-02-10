from __future__ import annotations

import os
from typing import Any

from app2026.brand import kovacnik


_REGISTRY: dict[str, Any] = {
    "kovacnik": kovacnik,
}


def get_brand(brand_id: str | None = None) -> Any:
    brand_key = (brand_id or os.getenv("BRAND", "kovacnik")).strip().lower()
    if brand_key in _REGISTRY:
        return _REGISTRY[brand_key]
    return kovacnik
