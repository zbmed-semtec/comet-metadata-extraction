"""
GitHub implementation of GitPlatformClient.

GitHub's `contents` endpoint already unifies file/directory access (unlike
GitLab's split tree/files endpoints), so `list_directory` and `get_file`
both hit the same endpoint here — mirroring the original Codeberg-style
implementation almost exactly, since Codeberg's API is Gitea's
GitHub-compatible surface.
"""

import base64
import re
from app.layer_3.plugins.shared.types.person import Person
from app.layer_3.plugins.shared.types.organization import Organization
from app.layer_3.plugins.shared.types.online_account import OnlineAccount
from app.layer_3.steps.contracts import ExtractionContext, ExtractionState
from app.layer_3.plugins.shared.git_platform_client import (
    GitPlatformClient,
    RepositoryItem,
    RepositoryFile,
    FileNotFoundOnPlatformError,
)

class GitHubRepositoryItem(RepositoryItem):
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

class GitHubRepositoryFile(GitHubRepositoryItem, RepositoryFile):
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
        return self._raw.get("html_url")

class GitHubClient(GitPlatformClient):
    """Client for interacting with the GitHub API,
    providing cached access to repository metadata, contents, and related resources."""

    def _get_api_base_url(self) -> str:
        """Returns the GitHub API base URL."""
        return "https://api.github.com"

    def _build_headers(self) -> dict:
        """Builds request headers for the GitHub API."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "maSMP-metadata-extraction",
        }
        if self.context.access_token:
            headers["Authorization"] = f"token {self.context.access_token}"
        return headers


    def _extract_repository_info(self, context: ExtractionContext) -> tuple[str, str]:
        """Parses the repository owner and name from the context's repository URL.
        
        Handles various GitHub URL formats, including:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - https://github.com/owner/repo/
        - https://github.com/owner/repo/tree/main
        - https://github.com/owner/repo/blob/main/file.py
        - https://github.com/owner/repo/issues/123
        - https://github.com/owner/repo/pull/456
        - owner/repo (shorthand)
        """
        repository_url = context.repo_url.strip()

        if not repository_url:
            raise ValueError("Repository URL cannot be empty.")

        # Handle SSH-style URLs: git@github.com:owner/repo.git
        ssh_match = re.match(r"^git@[\w.-]+:(.+)$", repository_url)
        if ssh_match:
            repository_url = ssh_match.group(1)

        # Strip protocol and domain if present (https://github.com/, http://, etc.)
        repository_url = re.sub(r"^(https?://)?([\w.-]+\.)?github\.com/", "", repository_url)

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
        """Fetches the repository metadata from the GitHub API."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}"
        return self._caching_get_json(url)

    def get_contributors(self) -> list[Person]:
        """Fetches the contributor list for the repository, enriched with user profile data."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/contributors"
        response = self._caching_get_json(url)

        result: list[Person] = []
        for raw_person in response:
            if raw_person.get('type') == 'Bot':
                continue

            login = raw_person.get('login')
            html_url = raw_person.get('html_url')
            user_url = raw_person.get('url')

            person = Person(
                account=OnlineAccount(
                    accountName=login,
                    accountServiceHomepage="https://github.com",
                    url=html_url,
                ),
                url=html_url,
                atId=user_url,
            )

            if user_url:
                user_data = self._caching_get_json(user_url)

                full_name = user_data.get('name')
                if full_name:
                    # GitHub only gives one free-text "name" field, not given/family split
                    name_parts = full_name.rsplit(" ", 1)
                    if len(name_parts) == 2:
                        person.givenName, person.familyName = name_parts
                    else:
                        person.givenName = full_name

                person.email = user_data.get('email')  # often null unless publicly set

                company = user_data.get('company')
                if company:
                    # GitHub's "company" field is free text (sometimes prefixed with "@")
                    org_name = company.lstrip('@').strip()
                    person.affiliation = Organization(name=org_name)

                person.url = user_data.get('blog') or html_url

            result.append(person)
        return result

    def get_languages(self) -> dict:
        """Fetches the programming languages used in the repository."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/languages"
        return self._caching_get_json(url)

    def get_releases(self) -> list:
        """Fetches the list of releases for the repository."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/releases"
        return self._caching_get_json(url)

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
        return f"https://github.com/{self.get_repository_owner()}/{self.get_repository_name()}/archive/refs/heads/{self.get_default_branch()}.zip"

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
        for tag_descriptor in self.get_tags():
            url = tag_descriptor.get('commit', {}).get('url')
            try:
                tag = self._caching_get_json(url)
                return tag.get('commit', {}).get('author', {}).get('date')
            except:
                pass

    def get_license(self):
        response = self._caching_get(f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/license")
        return response.json().get('license')
        
    def list_directory(self, path: str = "") -> list[RepositoryItem]:
        """Lists the immediate entries at `path` via GitHub's contents API."""
        url = f"{self._get_api_base_url()}/repos/{self.get_repository_owner()}/{self.get_repository_name()}/contents/{path}"
        response = self._caching_get(url)
        if response.status_code == 404:
            raise FileNotFoundOnPlatformError(path)
        raw = response.json()
        if not isinstance(raw, list):
            raise FileNotFoundOnPlatformError(path)
        return [GitHubRepositoryItem(entry) for entry in raw]

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
        return GitHubRepositoryFile(raw)