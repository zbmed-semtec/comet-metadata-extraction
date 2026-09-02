from __future__ import annotations

from typing import Any


def normalize_confidence(value: Any, default: float = 0.0) -> float:
    """Convert a parsed confidence value into a bounded float."""
    try:
        confidence = float(value)
    except Exception:
        confidence = float(default)
    return max(0.0, min(1.0, confidence))
