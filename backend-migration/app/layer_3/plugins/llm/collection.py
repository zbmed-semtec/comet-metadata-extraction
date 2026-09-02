from __future__ import annotations

from app.layer_3.plugins.llm.config import (
    LICENSE_PATTERNS,
    PROPERTY_QUERIES,
    PROPERTY_PROMPTS,
    PROPERTY_RULES,
    PROPERTY_SCHEMA_HINTS,
    PROMPT_ENGINEERING_CONFIG,
    PROMPT_ENGINEERING_CONFIG_PATH,
    RETRIEVAL_CONFIG,
    SYSTEM_PROMPTS,
    load_prompt_engineering_config,
)
from app.layer_3.plugins.llm.confidence import normalize_confidence
from app.layer_3.plugins.llm.extraction import LlmNameExtractor, RepoRef, extract_json, extract_property
from app.layer_3.plugins.llm.heuristics import (
    check_url_health,
    extract_contributors_from_text,
    extract_license_from_readme,
    extract_links_from_text,
)
from app.layer_3.plugins.llm.prompt import build_prompt
from app.layer_3.plugins.llm.provider import check_provider_ready, resolve_model_config, run_llm
from app.layer_3.plugins.llm.retrieval import (
    build_retrieval_index,
    hybrid_chunking,
    keyword_score,
    prepare_chunk_records,
    retrieve_top_chunks,
    split_with_metadata,
)

__all__ = [
    "LICENSE_PATTERNS",
    "PROPERTY_QUERIES",
    "PROPERTY_PROMPTS",
    "PROPERTY_RULES",
    "PROPERTY_SCHEMA_HINTS",
    "PROMPT_ENGINEERING_CONFIG",
    "PROMPT_ENGINEERING_CONFIG_PATH",
    "RETRIEVAL_CONFIG",
    "SYSTEM_PROMPTS",
    "LlmNameExtractor",
    "RepoRef",
    "build_prompt",
    "build_retrieval_index",
    "check_provider_ready",
    "check_url_health",
    "extract_contributors_from_text",
    "extract_json",
    "extract_license_from_readme",
    "extract_links_from_text",
    "extract_property",
    "hybrid_chunking",
    "keyword_score",
    "load_prompt_engineering_config",
    "normalize_confidence",
    "prepare_chunk_records",
    "resolve_model_config",
    "retrieve_top_chunks",
    "run_llm",
    "split_with_metadata",
]
