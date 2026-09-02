from __future__ import annotations

from pathlib import Path

import yaml


PROMPT_ENGINEERING_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "prompt_engineering.yaml"


def load_prompt_engineering_config() -> dict:
    """Load optional prompt-engineering settings from YAML."""
    if not PROMPT_ENGINEERING_CONFIG_PATH.exists():
        return {}

    with PROMPT_ENGINEERING_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


PROMPT_ENGINEERING_CONFIG = load_prompt_engineering_config()
RETRIEVAL_CONFIG = PROMPT_ENGINEERING_CONFIG.get("retrieval", {})
PROPERTY_PROMPTS = PROMPT_ENGINEERING_CONFIG.get("property_prompts", {})
SYSTEM_PROMPTS = PROMPT_ENGINEERING_CONFIG.get("system_prompts", {})

PROPERTY_QUERIES = {
    "name": ["name", "project", "repository", "software", "readme", "title"],
    **{
        key: value
        for key, value in RETRIEVAL_CONFIG.get("property_queries", {}).items()
        if isinstance(value, list)
    },
}

PROPERTY_SCHEMA_HINTS = {
    name: str(
        details.get(
            "expected_value_shape",
            PROPERTY_PROMPTS.get("default", {}).get("expected_value_shape", "null if unknown"),
        )
    )
    for name, details in PROPERTY_PROMPTS.items()
    if isinstance(details, dict)
}
PROPERTY_RULES = {
    name: str(
        details.get(
            "rules",
            PROPERTY_PROMPTS.get("default", {}).get("rules", "Return concise value and evidence quote if available."),
        )
    )
    for name, details in PROPERTY_PROMPTS.items()
    if isinstance(details, dict)
}
PROPERTY_SCHEMA_HINTS.setdefault(
    "default",
    str(PROPERTY_PROMPTS.get("default", {}).get("expected_value_shape", "null if unknown")),
)
PROPERTY_RULES.setdefault(
    "default",
    str(PROPERTY_PROMPTS.get("default", {}).get("rules", "Return concise value and evidence quote if available.")),
)

LICENSE_PATTERNS = [
    (item.get("pattern", ""), item.get("value", ""))
    for item in RETRIEVAL_CONFIG.get("license_patterns", [])
    if isinstance(item, dict)
]

LICENSE_PATTERNS = [
    (pattern, value)
    for pattern, value in LICENSE_PATTERNS
    if pattern and value
]
