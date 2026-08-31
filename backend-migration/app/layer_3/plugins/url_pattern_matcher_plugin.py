import re
from urllib.parse import urlparse
from typing import Optional, Tuple
from app.layer_2.base_plugin import BasePlugin

class URLPatternMatcher(BasePlugin):

    name = "url-pattern-matcher-plugin"

    @staticmethod
    def extract_repo_info(repo_url: str) -> Tuple[Optional[str], Optional[str]]:
        parsed_url = urlparse(repo_url)
        parts = parsed_url.path.strip("/").split("/")
        if len(parts) < 2:
            return None, None
        return parts[-2], parts[-1]

    @staticmethod
    def detect_platform(repo_url: str) -> Optional[str]:
        netloc = urlparse(repo_url).netloc.lower()
        if "github.com" in netloc:
            return "github"
        if "gitlab.com" in netloc:
            return "gitlab"
        return None

    @staticmethod
    def check_zenodo_badge(content: str) -> list[str]:
        """
        Detects actual Zenodo DOI *badges* (badge image + link), not just
        any bare Zenodo/DOI URL mentioned in text.

        Matches patterns like:
          [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1234567.svg)](https://doi.org/10.5281/zenodo.1234567)
          <img src="https://zenodo.org/badge/DOI/10.5281/zenodo.1234567.svg">
        """
        badge_pattern = (
            r"\[!\[[^\]]*\]\("
            r"https://zenodo\.org/badge/DOI/(\d+\.\d+/zenodo\.\d+)\.svg"
            r"\)\]\("
            r"https://doi\.org/\1"
            r"\)"
        )

        html_badge_pattern = (
            r"<img[^>]+src=[\"']https://zenodo\.org/badge/DOI/"
            r"(\d+\.\d+/zenodo\.\d+)\.svg[\"'][^>]*>"
        )

        dois = set()
        dois.update(re.findall(badge_pattern, content))
        dois.update(re.findall(html_badge_pattern, content))

        return [f"https://doi.org/{doi}" for doi in dois]