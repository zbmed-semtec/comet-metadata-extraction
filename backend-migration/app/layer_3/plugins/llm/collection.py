from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import requests
import yaml

from app.config.settings import settings
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None


PROMPT_ENGINEERING_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "prompt_engineering.yaml"


def load_prompt_engineering_config() -> dict:
    """Load optional prompt-engineering settings from YAML.

    Args:
        None.

    Returns:
        Parsed configuration dictionary, or an empty dictionary when absent.
    """
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


@dataclass
class RepoRef:
    """Identify a repository by provider, owner, and repository name."""
    provider: str
    owner: str
    repo: str


def split_with_metadata(md_text: str) -> list[dict]:
    """Split Markdown into sections while retaining heading metadata.

    Args:
        md_text: Markdown source text.

    Returns:
        Section dictionaries containing heading, level, and content lines.
    """
    lines = md_text.split("\n")
    chunks = []
    current = {"heading": None, "level": None, "content": []}

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if current["content"]:
                chunks.append(current)
            current = {"heading": m.group(2), "level": len(m.group(1)), "content": []}
            i += 1
            continue

        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.match(r"^=+$", next_line):
                if current["content"]:
                    chunks.append(current)
                current = {"heading": line, "level": 1, "content": []}
                i += 2
                continue
            if re.match(r"^-+$", next_line):
                if current["content"]:
                    chunks.append(current)
                current = {"heading": line, "level": 2, "content": []}
                i += 2
                continue

        current["content"].append(lines[i])
        i += 1

    if current["content"]:
        chunks.append(current)

    return chunks


def hybrid_chunking(section: dict, max_chars: int = 1200, overlap: int = 200) -> list[dict]:
    """Break a Markdown section into overlapping, size-limited chunks.

    Args:
        section: Section dictionary produced by ``split_with_metadata``.
        max_chars: Maximum characters per chunk.
        overlap: Characters shared by consecutive chunks.

    Returns:
        Chunk dictionaries with the original heading and chunk content.
    """
    text = "\n".join(section["content"]).strip()
    if len(text) <= max_chars:
        return [{"heading": section["heading"], "content": text}]

    out = []
    start = 0
    while start < len(text):
        end = start + max_chars
        out.append({"heading": section["heading"], "content": text[start:end]})
        start += max_chars - overlap
    return out


def prepare_chunk_records(chunks: list[dict]) -> list[dict]:
    """Normalize chunks into records ready for keyword or vector retrieval.

    Args:
        chunks: Chunk dictionaries containing headings and content.

    Returns:
        Non-empty records with IDs, normalized text, and combined full text.
    """
    records = []
    for i, chunk in enumerate(chunks):
        heading = "" if chunk.get("heading") is None else str(chunk.get("heading")).strip()
        content = "" if chunk.get("content") is None else str(chunk.get("content")).strip()
        if not content:
            continue
        records.append(
            {
                "chunk_id": i,
                "heading": heading,
                "content": content,
                "full_text": f"Heading: {heading}\n\n{content}" if heading else content,
            }
        )
    return records


def build_retrieval_index(records: list[dict], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> dict:
    """Build a retrieval index, adding embeddings when available.

    Args:
        records: Normalized README chunk records.
        model_name: SentenceTransformer model used to create embeddings.

    Returns:
        Index containing records and, when successful, model embeddings.
    """
    index = {
        "records": records,
        "embeddings": None,
        "model": None,
        "embedding_enabled": False,
    }

    if SentenceTransformer is None:
        return index

    try:
        model = SentenceTransformer(model_name)
        vec = model.encode([record["full_text"] for record in records], normalize_embeddings=True)
        index["embeddings"] = np.asarray(vec, dtype=np.float32)
        index["model"] = model
        index["embedding_enabled"] = True
    except Exception:
        pass

    return index


def keyword_score(record: dict, query_terms: list[str]) -> float:
    """Score one record by occurrences of property-related query terms.

    Args:
        record: A normalized chunk record.
        query_terms: Terms used to find relevant content.

    Returns:
        Weighted keyword-match score, with heading matches weighted higher.
    """
    heading = record["heading"].lower()
    content = record["content"].lower()
    score = 0.0
    for term in query_terms:
        normalized = term.lower()
        if normalized in heading:
            score += 2.0
        if normalized in content:
            score += 1.0
    return score


def retrieve_top_chunks(index: dict, property_name: str, top_k: int = 5, alpha: float = 0.75) -> list[dict]:
    """Rank and return README chunks most relevant to a metadata property.

    Args:
        index: Retrieval index from ``build_retrieval_index``.
        property_name: Metadata property to retrieve context for.
        top_k: Maximum number of chunks to return.
        alpha: Weight of semantic similarity versus keyword relevance.

    Returns:
        Highest-ranked chunk records annotated with score and rank.
    """
    terms = PROPERTY_QUERIES.get(property_name, [property_name])
    records = index["records"]

    kw = np.array([keyword_score(record, terms) for record in records], dtype=np.float32)
    if kw.size and kw.max() > 0:
        kw = kw / kw.max()

    if index["embedding_enabled"] and records:
        query_text = " ".join(terms)
        query_vector = index["model"].encode([query_text], normalize_embeddings=True)[0]
        sem = index["embeddings"] @ np.asarray(query_vector, dtype=np.float32)
        sem = (sem + 1.0) / 2.0
        scores = alpha * sem + (1 - alpha) * kw
    else:
        scores = kw

    order = np.argsort(-scores)[:top_k]
    out = []
    for rank, idx in enumerate(order, start=1):
        record = dict(records[int(idx)])
        record["score"] = float(scores[int(idx)])
        record["rank"] = rank
        out.append(record)
    return out


def extract_links_from_text(text: str, check_health: bool = False, health_timeout: int = 3) -> list[dict]:
    """Extract, filter, classify, and rank high-signal links in text.

    Args:
        text: README or other source text to scan.
        check_health: Whether to issue HTTP HEAD requests for extracted links.
        health_timeout: Per-link timeout in seconds when checking health.

    Returns:
        Deduplicated useful links, with relevance and optional health status.
    """
    found = []
    seen = set()

    noise_domain_parts = (
        "shields.io",
        "img.shields.io",
        "badge.fury.io",
        "travis-ci",
        "appveyor",
        "circleci",
        "codecov",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "discord.gg",
        "slack.com",
        "gitter.im",
    )
    noise_path_parts = (
        "/actions",
        "/workflows",
        "/issues",
        "/pull",
        "/pulls",
        "/compare",
        "/commit/",
        "/commits/",
        "/releases/tag",
        "/graphs/",
        "/network/",
    )
    image_exts = (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")

    def _canonicalize_url(url: str) -> str:
        """Normalize a URL by removing fragments, tracking parameters, and trailing punctuation.

        Args:
            url: Raw URL text.

        Returns:
            Canonical URL string, or an empty string for blank input.
        """
        normalized = url.strip().rstrip(").,;")
        if not normalized:
            return ""
        normalized = normalized.split("#", 1)[0]
        normalized = re.sub(r"([?&])utm_[^&]*", "", normalized, flags=re.IGNORECASE)
        normalized = normalized.replace("?&", "?")
        normalized = re.sub(r"[?&]+$", "", normalized)
        return normalized

    def _is_noise(url: str, title: str | None = None) -> bool:
        """Determine whether a link is a badge, social, CI, image, or repository-noise URL.

        Args:
            url: Canonical URL to evaluate.
            title: Optional Markdown link title.

        Returns:
            ``True`` when the link should be excluded.
        """
        lower_url = url.lower()
        lower_title = (title or "").lower()
        if any(domain in lower_url for domain in noise_domain_parts):
            return True
        if any(path in lower_url for path in noise_path_parts):
            return True
        if lower_url.endswith(image_exts):
            return True
        if any(keyword in lower_title for keyword in ["badge", "build status", "coverage", "ci"]):
            return True
        return False

    def _classify_relevance(url: str, title: str | None = None) -> str:
        """Classify a link as paper, documentation, repository, tutorial, or other.

        Args:
            url: Canonical URL to classify.
            title: Optional Markdown link title.

        Returns:
            Relevance category string.
        """
        lower_url = url.lower()
        lower_title = (title or "").lower()
        if any(keyword in lower_url or keyword in lower_title for keyword in ["arxiv", "doi.org", "paper", "publication", "proceedings", ".pdf"]):
            return "paper"
        if any(keyword in lower_url or keyword in lower_title for keyword in ["docs", "documentation", "readthedocs", "gitbook", "wiki", "guide"]):
            return "docs"
        if any(keyword in lower_url or keyword in lower_title for keyword in ["github", "gitlab", "bitbucket"]):
            return "repo"
        if any(keyword in lower_url or keyword in lower_title for keyword in ["example", "demo", "tutorial", "howto"]):
            return "tutorial"
        return "other"

    def _score(item: dict) -> float:
        """Assign a ranking score to a classified link.

        Args:
            item: Link dictionary containing URL, title, and relevance.

        Returns:
            Score used to prioritize useful links.
        """
        base = {"paper": 4.0, "docs": 3.0, "repo": 2.0, "tutorial": 1.5, "other": 0.2}.get(item.get("relevance", "other"), 0.2)
        lower_url = (item.get("url") or "").lower()
        lower_title = (item.get("title") or "").lower()
        bonus = 0.0
        if any(keyword in lower_url or keyword in lower_title for keyword in ["official", "documentation", "readme", "citation"]):
            bonus += 0.5
        if "github.com" in lower_url and any(keyword in lower_url for keyword in ["/issues", "/pull", "/actions"]):
            bonus -= 1.0
        return base + bonus

    for title, url in re.findall(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", text, flags=re.IGNORECASE):
        canonical = _canonicalize_url(url)
        if not canonical or canonical in seen or _is_noise(canonical, title):
            continue
        seen.add(canonical)
        found.append({"title": title.strip(), "url": canonical})

    for url in re.findall(r"https?://[^\s<>()\]\[\"'`]+", text, flags=re.IGNORECASE):
        canonical = _canonicalize_url(url)
        if not canonical or canonical in seen or _is_noise(canonical, None):
            continue
        seen.add(canonical)
        found.append({"title": None, "url": canonical})

    for item in found:
        item["relevance"] = _classify_relevance(item["url"], item.get("title"))
        if check_health:
            try:
                response = requests.head(item["url"], timeout=health_timeout, allow_redirects=True)
                item["status_code"] = int(response.status_code)
                item["is_working"] = 200 <= response.status_code < 400
            except Exception:
                item["status_code"] = None
                item["is_working"] = False
        else:
            item["status_code"] = None
            item["is_working"] = None

    useful = [item for item in found if item.get("relevance") in {"paper", "docs", "repo", "tutorial"}]
    useful.sort(key=_score, reverse=True)

    caps = {"paper": 2, "docs": 4, "repo": 2, "tutorial": 2}
    kept = []
    counts = {key: 0 for key in caps}
    for item in useful:
        relevance = item["relevance"]
        if counts[relevance] >= caps[relevance]:
            continue
        kept.append(item)
        counts[relevance] += 1

    return kept


def extract_license_from_readme(readme_text: str) -> tuple[str | None, str | None]:
    """Find a configured SPDX license pattern and its nearby README evidence.

    Args:
        readme_text: README content to inspect.

    Returns:
        SPDX identifier and evidence snippet, or ``(None, None)`` if not found.
    """
    low = readme_text.lower()
    for pattern, spdx in LICENSE_PATTERNS:
        match = re.search(pattern, low, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 80)
            end = min(len(readme_text), match.end() + 80)
            evidence = readme_text[start:end].replace("\n", " ").strip()
            return spdx, evidence
    return None, None


def extract_contributors_from_text(text: str) -> list[dict]:
    """Extract distinct GitHub-linked contributors and @handles from text.

    Args:
        text: README or other source text to scan.

    Returns:
        Contributor dictionaries with display name and GitHub URL.
    """
    found = []
    seen = set()

    for name, url in re.findall(r"\[([^\]]+)\]\((https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)\)", text, flags=re.IGNORECASE):
        canonical = url.strip()
        if canonical and canonical not in seen:
            seen.add(canonical)
            found.append({"name": name.strip(), "github_url": canonical})

    for url in re.findall(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?", text, flags=re.IGNORECASE):
        canonical = url.strip().rstrip(").,;")
        if canonical and canonical not in seen:
            seen.add(canonical)
            found.append({"name": canonical.rstrip("/").split("/")[-1], "github_url": canonical})

    for handle in re.findall(r"(?<![\w/])@([A-Za-z0-9-]{1,39})\b", text):
        github_url = f"https://github.com/{handle}"
        if github_url not in seen:
            seen.add(github_url)
            found.append({"name": handle, "github_url": github_url})

    return found


def check_url_health(url: str, timeout: int = 5) -> tuple[bool, int | None]:
    """Check whether a URL responds successfully, falling back from HEAD to GET.

    Args:
        url: URL to request.
        timeout: Request timeout in seconds.

    Returns:
        Working-status boolean and HTTP status code, if available.
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        is_working = 200 <= response.status_code < 400
        return is_working, response.status_code
    except Exception:
        try:
            response = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
            response.close()
            is_working = 200 <= response.status_code < 400
            return is_working, response.status_code
        except Exception:
            return False, None


def extract_json(text: str) -> dict:
    """Parse an LLM response into an extraction-result dictionary.

    Args:
        text: Raw model output, optionally wrapped in a Markdown JSON fence.

    Returns:
        Parsed result dictionary, or an empty standard result on parse failure.
    """
    text = (text or "").strip()
    if not text:
        return {"value": None, "evidence": None, "confidence": 0.0}

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s*```$", "", text).strip()

    def _normalize(parsed: Any) -> dict:
        """Convert parsed JSON into the first usable result dictionary.

        Args:
            parsed: JSON-decoded object.

        Returns:
            Parsed dictionary or the standard empty result dictionary.
        """
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


def build_prompt(property_name: str, context: str) -> str:
    """Create the JSON-only extraction prompt for a metadata property.

    Args:
        property_name: Metadata property requested from the model.
        context: Retrieved README chunks supplied as evidence.

    Returns:
        Prompt instructing the model to return value, evidence, and confidence.
    """
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


def check_provider_ready(provider: str, model: str, base_url: str, timeout: int = 10) -> tuple[bool, str]:
    """Verify that a supported local provider is reachable and hosts a model.

    Args:
        provider: LLM provider name (``ollama`` or ``vllm``).
        model: Required model identifier.
        base_url: Provider server base URL.
        timeout: HTTP request timeout in seconds.

    Returns:
        Readiness boolean and a human-readable diagnostic message.
    """
    provider = provider.lower().strip()

    if provider == "ollama":
        endpoint = base_url.rstrip("/") + "/api/tags"
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()
            names = [item.get("name", "") for item in response.json().get("models", [])]
            if model in names:
                return True, f"Ollama ready. Model {model} found."
            return False, f"Model {model} not found. Available: {names}"
        except Exception as exc:
            return False, f"Cannot reach Ollama: {exc}"

    if provider == "vllm":
        endpoint = base_url.rstrip("/") + "/v1/models"
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()
            names = [item.get("id", "") for item in response.json().get("data", [])]
            if model in names:
                return True, f"vLLM ready. Model {model} found."
            return False, f"Model {model} not found. Available: {names}"
        except Exception as exc:
            return False, f"Cannot reach vLLM: {exc}"

    return False, f"Unsupported provider: {provider}"


def run_llm(prompt: str, provider: str, model: str, base_url: str, timeout: int = 420) -> str:
    """Submit an extraction prompt to Ollama or vLLM.

    Args:
        prompt: User prompt requesting structured metadata extraction.
        provider: LLM provider name (``ollama`` or ``vllm``).
        model: Model identifier to invoke.
        base_url: Provider server base URL.
        timeout: HTTP request timeout in seconds.

    Returns:
        Raw text returned by the selected model.

    Raises:
        RuntimeError: If the provider is unsupported.
        requests.RequestException: If the provider request fails.
    """
    provider = provider.lower().strip()

    if provider == "ollama":
        endpoint = base_url.rstrip("/") + "/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "top_p": 0.7, "num_predict": 700},
        }
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", "")

    if provider == "vllm":
        endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": str(SYSTEM_PROMPTS.get("json_only", "Return valid JSON only.")).strip()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "top_p": 0.7,
            "max_tokens": 2000,
        }
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    raise RuntimeError(f"Unsupported provider: {provider}")


def resolve_model_config() -> tuple[str, str, str, str]:
    """Read the active LLM provider, model, and endpoint from settings.

    Args:
        None.

    Returns:
        Active model label, provider, model name, and provider base URL.
    """
    active_model = str(getattr(settings, "llm_provider", "ollama")).strip().lower()
    provider = str(getattr(settings, "llm_provider", "ollama")).strip().lower()
    model_name = str(getattr(settings, "llm_model", "phi4-mini")).strip()
    base_url = str(getattr(settings, "llm_base_url", "http://localhost:11434")).strip()
    description = f"{provider}:{model_name}" if model_name else provider
    return active_model, provider, model_name, base_url or description


def extract_property(property_name: str, readme_text: str, provider: str, model: str, base_url: str, top_k: int = 5) -> dict:
    """Extract one metadata property from README text using rules or an LLM.

    Args:
        property_name: Metadata property to extract.
        readme_text: Complete README text.
        provider: LLM provider name.
        model: Model identifier.
        base_url: Provider server base URL.
        top_k: Number of retrieved chunks supplied to the model.

    Returns:
        Result dictionary containing value, evidence, confidence, and chunk data.
    """
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
            """Normalize a candidate link before deduplication and filtering.

            Args:
                url: Raw URL string.

            Returns:
                Canonicalized URL string.
            """
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
    data.setdefault("confidence", 0.0)
    data["retrieved_chunks"] = chunk_info
    return data


class LlmNameExtractor(GitPlatformBaseExtractor):
    """Extract a repository's ``schema:name`` from README content using an LLM."""

    extracts = {"https://schema.org/name"}

    def extract(self, context, state):
        """Collect an LLM-inferred repository name into the extraction state.

        Args:
            context: Extraction context used to obtain the platform client.
            state: Mutable extraction state and metadata collector.

        Returns:
            The input state, optionally updated with a ``schema:name`` value.
        """
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
            confidence = float(result.get("confidence", 0.8) or 0.8)
            state.metadata_collector.collect("LLM README", "https://schema.org/name", value, confidence)

        return state
