from __future__ import annotations

import re

import requests

from app.layer_3.plugins.llm.config import LICENSE_PATTERNS


def extract_links_from_text(text: str, check_health: bool = False, health_timeout: int = 3) -> list[dict]:
    """Extract, filter, classify, and rank high-signal links in text."""
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
        """Normalize a URL by removing fragments, tracking parameters, and trailing punctuation."""
        normalized = url.strip().rstrip(").,;")
        if not normalized:
            return ""
        normalized = normalized.split("#", 1)[0]
        normalized = re.sub(r"([?&])utm_[^&]*", "", normalized, flags=re.IGNORECASE)
        normalized = normalized.replace("?&", "?")
        normalized = re.sub(r"[?&]+$", "", normalized)
        return normalized

    def _is_noise(url: str, title: str | None = None) -> bool:
        """Determine whether a link is a badge, social, CI, image, or repository-noise URL."""
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
        """Classify a link as paper, documentation, repository, tutorial, or other."""
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
        """Assign a ranking score to a classified link."""
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


def extract_contributors_from_text(text: str) -> list[dict]:
    """Extract distinct GitHub-linked contributors and @handles from text."""
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
    """Check whether a URL responds successfully, falling back from HEAD to GET."""
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
