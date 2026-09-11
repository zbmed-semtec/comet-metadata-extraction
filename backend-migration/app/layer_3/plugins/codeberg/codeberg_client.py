import re
import base64
import requests

from app.layer_3.plugins.shared.types.person import Person
from app.layer_3.plugins.shared.types.online_account import OnlineAccount
from app.layer_3.steps.contracts import ExtractionContext, ExtractionState
from app.layer_3.plugins.shared.git_platform_client import (
    GitPlatformClient,
    RepositoryItem,
    RepositoryFile,
    FileNotFoundOnPlatformError,
)


class CodebergRepositoryItem(RepositoryItem):
    @property
    def name(self) -> str:
        return self._raw["name"]

    @property
    def path(self) -> str:
        return self._raw["path"]

    @property
    def is_dir(self) -> bool:
        return self._raw["type"] == "dir"

    def get_html_url(self, _client) -> str | None:
        return self._raw.get("html_url")

class CodebergRepositoryFile(CodebergRepositoryItem, RepositoryFile):
    def get_content(self) -> str | None:
        raw_content = self._raw.get("content")
        if raw_content is None:
            return None
        if self._raw.get("encoding") == "base64":
            try:
                return base64.b64decode(raw_content).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                return None
        return raw_content

    def get_html_url(self, _client):
        return self._raw.get('html_url')

class CodebergClient(GitPlatformClient):
    """Client for interacting with the Codeberg API and web endpoints,
    providing cached access to repository metadata, contents, and related resources."""

    def _get_api_base_url(self) -> str:
        """Returns the Codeberg API base URL."""
        return "https://codeberg.org/api/v1"

    def _build_headers(self) -> dict:
        """Builds request headers for Codeberg API."""
        return {
            "Accept": "application/vnd.Codeberg.v3+json",
            "User-Agent": "maSMP-metadata-extraction",
            "Authorization": f"token {self.context.access_token}" if self.context.access_token else None
        }

    def _extract_repository_info(self, context: ExtractionContext) -> tuple[str, str]:
        """Parses the repository owner and name from the context's repository URL.

        Handles various Codeberg URL formats, including:
        - https://codeberg.org/owner/repo
        - https://codeberg.org/owner/repo.git
        - git@codeberg.org:owner/repo.git
        - https://codeberg.org/owner/repo/
        - https://codeberg.org/owner/repo/src/branch/main
        - https://codeberg.org/owner/repo/issues/123
        - https://codeberg.org/owner/repo/pulls/456
        - owner/repo (shorthand)
        """
        repository_url = context.repo_url.strip()

        if not repository_url:
            raise ValueError("Repository URL cannot be empty.")

        # Handle SSH-style URLs: git@codeberg.org:owner/repo.git
        ssh_match = re.match(r"^git@[\w.-]+:(.+)$", repository_url)
        if ssh_match:
            repository_url = ssh_match.group(1)

        # Strip protocol and domain if present (https://codeberg.org/, http://, etc.)
        repository_url = re.sub(r"^(https?://)?([\w.-]+\.)?codeberg\.org/", "", repository_url)

        # Strip trailing slashes
        repository_url = repository_url.strip("/")

        # Remove trailing .git extension
        repository_url = re.sub(r"\.git$", "", repository_url)

        parts = repository_url.split("/")

        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repository URL format: {context.repo_url}")

        owner, repo = parts[0], parts[1]

        return owner, repo

    def get_repository(self) -> dict:
        """Fetches the repository metadata from the Codeberg API."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}"
        return self._caching_get_json(url)

    def get_contributors(self) -> list[Person]:
        """Fetches the contributor activity data for the repository."""
        url = f'https://codeberg.org/{self.get_repository_owner()}/{self.get_repository_name()}/activity/contributors/data'
        response = self._caching_get_json(url)

        result: list[Person] = []
        for key, raw_person in response.items():
            if key == "total":
                continue

            name = raw_person.get('name')
            if not name:
                continue

            home_link = raw_person.get('home_link')
            profile_url = f'https://codeberg.org{home_link}' if home_link else None
            username = home_link.lstrip('/') if home_link else None

            result.append(Person(
                name=name,
                account=OnlineAccount(
                    accountName=username,
                    accountServiceHomepage="https://codeberg.org",
                    url=profile_url,
                ) if profile_url else None,
                email=raw_person.get('email') or None,
            ))
        return result

    def get_languages(self) -> dict:
        """Fetches the programming languages used in the repository."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/languages"
        return self._caching_get_json(url)

    def get_releases(self) -> list:
        """Fetches the list of releases for the repository."""
        try:
            url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/releases"
            return self._caching_get_json(url)
        except requests.exceptions.HTTPError:
            return []

    def get_tags(self) -> list:
        """Fetches the list of tags for the repository."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/tags"
        return self._caching_get_json(url)

    def get_default_branch(self) -> str:
        """Fetches the default branch name for the repository."""
        repository = self.get_repository()
        return repository.get("default_branch", "main")

    def get_clone_url(self):
        repository = self.get_repository()
        return repository.get("clone_url")

    def get_download_url(self):
        return f"https://codeberg.org/{self.get_repository_owner()}/{self.get_repository_name()}/archive/{self.get_default_branch()}.zip"

    def get_html_url(self):
        repo = self.get_repository()
        return repo.get('html_url')

    def get_date_modified(self):
        return self.get_repository().get('updated_at')

    def get_date_created(self):
        return self.get_repository().get('created_at')

    def get_date_published(self):
        for release in self.get_releases():
            return release.get('published_at')
        for tag in self.get_tags():
            return tag.get('commit', {}).get('created')

    def list_directory(self, path: str = "") -> list[RepositoryItem]:
        """Lists the immediate entries at `path` via Codeberg's (Gitea-compatible) contents API."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/contents/{path}"
        response = self._caching_get(url)
        if response.status_code == 404:
            raise FileNotFoundOnPlatformError(path)
        raw = response.json()
        if not isinstance(raw, list):
            raise FileNotFoundOnPlatformError(path)
        return [CodebergRepositoryItem(entry) for entry in raw]

    def _fetch_file(self, path: str, ref: str | None = None) -> RepositoryFile:
        """Fetches a single file's metadata and content via GitHub's contents API."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/contents/{path}"
        params = {"ref": ref} if ref else None
        response = self._caching_get(url, params=params)
        if response.status_code == 404:
            raise FileNotFoundOnPlatformError(path)
        raw = response.json()
        if isinstance(raw, list):
            raise FileNotFoundOnPlatformError(path)
        return CodebergRepositoryFile(raw)