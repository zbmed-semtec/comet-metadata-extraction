from __future__ import annotations

from typing import Any


def normalize_confidence(value: Any, default: float = 0.0) -> float:
    """Convert model confidence to a float bounded by LLM source reliability."""
    try:
        confidence = float(value)
    except Exception:
        confidence = float(default)
    return max(0.0, min(0.7, confidence))