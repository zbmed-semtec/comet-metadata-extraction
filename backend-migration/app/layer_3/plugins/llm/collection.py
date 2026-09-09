"""Public LLM extractor plugins.

Platform modules (GitHub / GitLab / Codeberg) subclass these extractors.
Implementation details live in sibling modules (``extraction``, ``prompt``, …).
"""

from __future__ import annotations

from app.layer_3.plugins.llm.extraction import (
    LlmAlternateNameExtractor,
    LlmApplicationCategoryExtractor,
    LlmBuildInstructionsExtractor,
    LlmContactExtractor,
    LlmDescriptionExtractor,
    LlmInstallationExtractor,
    LlmIntendedUseExtractor,
    LlmNameExtractor,
    LlmReadmePropertyExtractor,
)

__all__ = [
    "LlmAlternateNameExtractor",
    "LlmApplicationCategoryExtractor",
    "LlmBuildInstructionsExtractor",
    "LlmContactExtractor",
    "LlmDescriptionExtractor",
    "LlmInstallationExtractor",
    "LlmIntendedUseExtractor",
    "LlmNameExtractor",
    "LlmReadmePropertyExtractor",
]
