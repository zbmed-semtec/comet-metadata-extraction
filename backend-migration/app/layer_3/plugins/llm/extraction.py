from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Any

from app.config.settings import settings
from app.layer_3.plugins.llm.confidence import normalize_confidence
from app.layer_3.plugins.llm.heuristics import (
    extract_contributors_from_text,
    extract_license_from_readme,
    extract_links_from_text,
)
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


def extract_property(property_name: str, readme_text: str, provider: str, model: str, base_url: str, top_k: int = 5) -> dict:
    """Extract one metadata property from README text using rules or an LLM."""
    if not settings.llm_enabled:
        return {"value": None, "evidence": None, "confidence": 0.0, "retrieved_chunks": []}

    if property_name == "license":
        license_value, evidence = extract_license_from_readme(readme_text)
        if license_value:
            return {"value": license_value, "evidence": evidence, "confidence": 0.98, "retrieved_chunks": []}

    if property_name == "contributors":
        contributors = extract_contributors_from_text(readme_text)
        if contributors:
            return {
                "value": contributors,
                "evidence": "Found GitHub handles/links in README.",
                "confidence": 0.95,
                "retrieved_chunks": [],
            }

    if property_name == "links":
        raw_links = extract_links_from_text(readme_text, check_health=False)
        useful_rels = {"paper", "docs", "repo", "tutorial"}
        noise_domain_parts = ("shields.io", "travis-ci", "circleci", "codecov", "twitter.com", "x.com", "linkedin.com", "discord.gg")
        noise_path_parts = ("/issues", "/pull", "/actions", "/commit/", "/releases/tag", "/workflows")
        image_exts = (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")

        def _canon(url: str) -> str:
            """Normalize a candidate link before deduplication and filtering."""
            normalized = (url or "").strip().rstrip(").,;")
            normalized = normalized.split("#", 1)[0]
            normalized = re.sub(r"([?&])utm_[^&]*", "", normalized, flags=re.IGNORECASE)
            normalized = normalized.replace("?&", "?")
            normalized = re.sub(r"[?&]+$", "", normalized)
            return normalized

        filtered = []
        seen = set()
        for item in raw_links or []:
            url = _canon(str(item.get("url") or ""))
            if not url or url in seen:
                continue
            lower_url = url.lower()
            if any(domain in lower_url for domain in noise_domain_parts):
                continue
            if any(path in lower_url for path in noise_path_parts):
                continue
            if lower_url.endswith(image_exts):
                continue
            relevance = str(item.get("relevance") or "other").lower()
            if relevance not in useful_rels:
                continue
            seen.add(url)
            cleaned = dict(item)
            cleaned["url"] = url
            filtered.append(cleaned)

        priority = {"paper": 0, "docs": 1, "repo": 2, "tutorial": 3}
        filtered.sort(key=lambda item: priority.get(str(item.get("relevance") or "other").lower(), 99))

        max_links = 10
        filtered = filtered[:max_links]

        if filtered:
            return {
                "value": filtered,
                "evidence": "Filtered high-signal links (paper/docs/repo/tutorial) from README text.",
                "confidence": 0.92,
                "retrieved_chunks": [],
            }

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


@dataclass
class RepoRef:
    """Identify a repository by provider, owner, and repository name."""

    provider: str
    owner: str
    repo: str


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
            confidence = normalize_confidence(result.get("confidence", 0.8), default=0.8)
            state.metadata_collector.collect("LLM README", "https://schema.org/name", value, confidence)

        return state
