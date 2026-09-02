from __future__ import annotations

from app.layer_3.plugins.llm.config import PROPERTY_RULES, PROPERTY_SCHEMA_HINTS


def build_prompt(property_name: str, context: str) -> str:
    """Create the JSON-only extraction prompt for a metadata property."""
    schema_hint = PROPERTY_SCHEMA_HINTS.get(property_name, "null if unknown")
    rule_hint = PROPERTY_RULES.get(property_name, PROPERTY_RULES["default"])
    return (
        f"You are extracting '{property_name}' from repository README chunks.\n"
        f"Rules: {rule_hint}\n"
        f"Expected value shape: {schema_hint}\n\n"
        "No guessing. Return JSON only with keys: value, evidence, confidence.\n"
        "- value: extracted value or null\n"
        "- evidence: exact short quote from context or null\n"
        "- confidence: number from 0 to 1\n\n"
        f"Context:\n{context}"
    )
