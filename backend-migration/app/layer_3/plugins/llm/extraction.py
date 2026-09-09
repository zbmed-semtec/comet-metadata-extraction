from __future__ import annotations

import json
import re
from typing import Any

from app.config.settings import settings
from app.layer_3.plugins.llm.confidence import normalize_confidence
from app.layer_3.plugins.llm.heuristics import extract_license_from_readme
from app.layer_3.plugins.llm.prompt import build_prompt
from app.layer_3.plugins.llm.provider import resolve_model_config, run_llm
from app.layer_3.plugins.llm.retrieval import (
    build_retrieval_index,
    hybrid_chunking,
    prepare_chunk_records,
    retrieve_top_chunks,
    split_with_metadata,
)
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor


def extract_json(text: str) -> dict:
    """Parse an LLM response into an extraction-result dictionary."""
    text = (text or "").strip()
    if not text:
        return {"value": None, "evidence": None, "confidence": 0.0}

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s*```$", "", text).strip()

    def _normalize(parsed: Any) -> dict:
        """Convert parsed JSON into the first usable result dictionary."""
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    return item
        return {"value": None, "evidence": None, "confidence": 0.0}

    try:
        return _normalize(json.loads(text))
    except Exception:
        pass

    try:
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(text)
        return _normalize(parsed)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*?\}", text)
    if match:
        try:
            return _normalize(json.loads(match.group(0)))
        except Exception:
            pass

    return {"value": None, "evidence": None, "confidence": 0.0}


def try_license_heuristic(readme_text: str) -> dict | None:
    """Return a license result from README SPDX patterns, or ``None`` to fall through to the LLM."""
    license_value, evidence = extract_license_from_readme(readme_text)
    if not license_value:
        return None
    return {
        "value": license_value,
        "evidence": evidence,
        "confidence": 0.98,
        "retrieved_chunks": [],
    }


def extract_property(property_name: str, readme_text: str, provider: str, model: str, base_url: str, top_k: int = 5) -> dict:
    """Extract one metadata property from README text using rules or an LLM."""
    if not settings.llm_enabled:
        return {"value": None, "evidence": None, "confidence": 0.0, "retrieved_chunks": []}

    # License is isolated: pattern match first, LLM only if no SPDX hit.
    if property_name == "license":
        heuristic = try_license_heuristic(readme_text)
        if heuristic is not None:
            return heuristic

    sections = split_with_metadata(readme_text)
    chunks = []
    for section in sections:
        chunks.extend(hybrid_chunking(section))
    records = prepare_chunk_records(chunks)
    index = build_retrieval_index(records)
    top_chunks = retrieve_top_chunks(index, property_name, top_k=top_k)

    chunk_info = []
    for chunk in top_chunks:
        chunk_info.append({"rank": chunk["rank"], "score": chunk["score"], "heading": chunk["heading"]})

    context = "\n\n".join([f"[Rank {chunk['rank']}, score={chunk['score']:.3f}] {chunk['full_text']}" for chunk in top_chunks])
    prompt = build_prompt(property_name, context)
    raw = run_llm(prompt, provider=provider, model=model, base_url=base_url)
    data = extract_json(raw)
    data.setdefault("value", None)
    data.setdefault("evidence", None)
    data["confidence"] = normalize_confidence(data.get("confidence", 0.0))
    data["retrieved_chunks"] = chunk_info
    return data


class LlmNameExtractor(GitPlatformBaseExtractor):
    """Extract a repository's ``schema:name`` from README content using an LLM."""

    extracts = {"https://schema.org/name"}

    def extract(self, context, state):
        """Collect an LLM-inferred repository name into the extraction state."""
        if not settings.llm_enabled:
            return state

        client = self.get_client(context, state)
        readme_text = "\n\n------\n\n".join(
            str(readme_file.get_content())
            for readme_file in client.get_readme_candidate_files()
        ).strip()

        if not readme_text:
            return state

        _, provider, model_name, base_url = resolve_model_config()
        result = extract_property(
            property_name="name",
            readme_text=readme_text,
            provider=provider,
            model=model_name,
            base_url=base_url,
            top_k=5,
        )

        value = result.get("value")
        if value:
            confidence = normalize_confidence(result.get("confidence", 0.7), default=0.7)
            state.metadata_collector.collect("LLM README", "https://schema.org/name", value, confidence)

        return state


# README properties that can be supplied by the prompt configuration and also
# mapped to an actual LinkML slot in one or more supported output schemas.
# `prompt_property` intentionally need not be the same as the schema slot:
# the existing configuration calls the maSMP installation prompt
# ``installation``, while its output slot is ``installInstructions``.
_URL_PATTERN = re.compile(r"https?://[^\s<>\]\[\"')]+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def normalize_readme_property(value: Any, value_type: str) -> Any:
    """Apply small, schema-oriented guards to LLM README values.

    These are deliberately validation heuristics, not a second extractor: the
    README evidence remains the source of truth and the LLM still performs the
    semantic extraction.
    """
    if value_type == "text":
        return value.strip() if isinstance(value, str) and value.strip() else None

    if value_type == "url":
        if not isinstance(value, str):
            return None
        match = _URL_PATTERN.search(value)
        return match.group(0).rstrip(".,;)") if match else None

    if value_type == "string_list":
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                normalized.append(cleaned)
        return normalized or None

    if value_type == "contact":
        if not isinstance(value, str):
            return None
        email = _EMAIL_PATTERN.search(value)
        if email:
            return email.group(0)
        url = _URL_PATTERN.search(value)
        return url.group(0).rstrip(".,;)") if url else None

    return None


class LlmReadmePropertyExtractor(GitPlatformBaseExtractor):
    """Shared README LLM extraction for one configured schema property.

    Subclasses mirror ``LlmNameExtractor``: one plugin per prompt property.
    These run after deterministic plugins and only call the LLM when the field
    still has no candidate.
    """

    prompt_property: str = ""
    value_type: str = "text"
    extracts: set[str] = set()
    priority_level = 10

    def extract(self, context, state):
        """Collect one LLM-inferred README property into the extraction state."""
        if not settings.llm_enabled:
            return state

        schema_uris = {
            context.schema.get_uri(property_name)
            for property_name in context.schema.get_property_list()
        }
        target_uris = self.extracts & schema_uris
        if not target_uris:
            return state

        # A deterministic plugin has already supplied this field.
        if any(state.metadata_collector.get_most_confident(uri) for uri in self.extracts):
            return state

        client = self.get_client(context, state)
        readme_text = "\n\n------\n\n".join(
            str(readme_file.get_content())
            for readme_file in client.get_readme_candidate_files()
            if readme_file.get_content()
        ).strip()
        if not readme_text:
            return state

        _, provider, model_name, base_url = resolve_model_config()
        result = extract_property(
            property_name=self.prompt_property,
            readme_text=readme_text,
            provider=provider,
            model=model_name,
            base_url=base_url,
            top_k=5,
        )
        value = normalize_readme_property(result.get("value"), self.value_type)
        if not value:
            return state

        confidence = normalize_confidence(result.get("confidence", 0.0))
        for uri in target_uris:
            state.metadata_collector.collect("LLM README", uri, value, confidence)

        return state


class LlmDescriptionExtractor(LlmReadmePropertyExtractor):
    """Extract a repository's ``schema:description`` from README content using an LLM."""

    prompt_property = "description"
    value_type = "text"
    extracts = {"https://schema.org/description"}


class LlmBuildInstructionsExtractor(LlmReadmePropertyExtractor):
    """Extract build-instruction URLs from README content using an LLM."""

    prompt_property = "buildInstructions"
    value_type = "url"
    extracts = {
        "https://discovery.biothings.io/ns/maSMP/buildInstructions",
        "https://codemeta.github.io/terms/buildInstructions",
        "codemeta:buildInstructions",
    }


class LlmInstallationExtractor(LlmReadmePropertyExtractor):
    """Extract installation-instruction URLs from README content using an LLM."""

    prompt_property = "installation"
    value_type = "url"
    extracts = {"https://discovery.biothings.io/ns/maSMP/installInstructions"}


class LlmAlternateNameExtractor(LlmReadmePropertyExtractor):
    """Extract a repository's ``schema:alternateName`` from README content using an LLM."""

    prompt_property = "alternateNames"
    value_type = "string_list"
    extracts = {"https://schema.org/alternateName"}


class LlmApplicationCategoryExtractor(LlmReadmePropertyExtractor):
    """Extract a repository's ``schema:applicationCategory`` from README content using an LLM."""

    prompt_property = "applicationCategory"
    value_type = "string_list"
    extracts = {"https://schema.org/applicationCategory"}


class LlmIntendedUseExtractor(LlmReadmePropertyExtractor):
    """Extract the software's intended use from README content using an LLM."""

    prompt_property = "intendedUse"
    value_type = "text"
    extracts = {
        "https://discovery.biothings.io/ns/maSMP/intendedUse",
        "https://schema.org/intendedUse",
    }


class LlmContactExtractor(LlmReadmePropertyExtractor):
    """Extract a repository's ``schema:contactPoint`` from README content using an LLM."""

    prompt_property = "contact"
    value_type = "contact"
    extracts = {"https://schema.org/contactPoint"}
