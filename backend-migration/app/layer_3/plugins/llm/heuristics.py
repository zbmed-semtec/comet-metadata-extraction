from __future__ import annotations

import re

from app.layer_3.plugins.llm.config import LICENSE_PATTERNS


def extract_license_from_readme(readme_text: str) -> tuple[str | None, str | None]:
    """Find a configured SPDX license pattern and its nearby README evidence."""
    low = readme_text.lower()
    for pattern, spdx in LICENSE_PATTERNS:
        match = re.search(pattern, low, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 80)
            end = min(len(readme_text), match.end() + 80)
            evidence = readme_text[start:end].replace("\n", " ").strip()
            return spdx, evidence
    return None, None
