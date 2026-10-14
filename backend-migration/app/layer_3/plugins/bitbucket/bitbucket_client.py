"""
Bitbucket implementation of GitPlatformClient.

Bitbucket's API differs significantly from GitHub/GitLab/Codeberg: it uses
the `src` endpoint for both directory listing and file content, but returns
raw file content directly (no base64 wrapping) and paginates directory
listings. Contributor data isn't natively exposed, so it's derived from
commit authors. Metadata such as license and languages also require
different endpoints or heuristics, since Bitbucket doesn't expose a
languages breakdown or license detection API like GitHub does.
"""

import re
from collections import Counter
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

class BitbucketRepositoryItem(RepositoryItem):
    @property
    def name(self) -> str:
        return self._raw["path"].rsplit("/", 1)[-1]

    @property
    def path(self) -> str:
        return self._raw["path"]

    @property
    def is_dir(self) -> bool:
        return self._raw["type"] == "commit_directory"

    def get_html_url(self, client) -> str | None:
        links = self._raw.get("links", {})
        self_link = links.get("self", {}).get("href")
        if not self_link:
            return None
        # Convert API src link into a web UI link
        return (
            f"https://bitbucket.org/{client.get_repository_owner()}/"
            f"{client.get_repository_name()}/src/{client.get_default_branch()}/{self.path}"
        )

class BitbucketRepositoryFile(BitbucketRepositoryItem, RepositoryFile):
    def get_content(self) -> str | None:
        # Content is fetched separately as raw text and stashed on the instance
        # by the client (Bitbucket's `src` metadata endpoint doesn't embed content
        # the way GitHub/Gitea does for files fetched via directory listing).
        return self._raw.get("_content")

    def get_html_url(self, client):
        return super().get_html_url(client)

class BitbucketClient(GitPlatformClient):
    """Client for interacting with the Bitbucket API,
    providing cached access to repository metadata, contents, and related resources."""

    def _get_api_base_url(self) -> str:
        """Returns the Bitbucket API base URL."""
        return "https://api.bitbucket.org/2.0"

    def _build_headers(self) -> dict:
        """Builds request headers for the Bitbucket API."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "maSMP-metadata-extraction",
        }
        if self.context.access_token:
            headers["Authorization"] = f"Bearer {self.context.access_token}"
        return headers

    def _extract_repository_info(self, context: ExtractionContext) -> tuple[str, str]:
        """Parses the workspace and repo slug from the context's repository URL.

        Handles various Bitbucket URL formats, including:
        - https://bitbucket.org/workspace/repo
        - https://bitbucket.org/workspace/repo.git
        - git@bitbucket.org:workspace/repo.git
        - https://bitbucket.org/workspace/repo/
        - https://bitbucket.org/workspace/repo/src/main
        - https://bitbucket.org/workspace/repo/src/main/file.py
        - https://bitbucket.org/workspace/repo/issues/123
        - https://bitbucket.org/workspace/repo/pull-requests/456
        - workspace/repo (shorthand)
        """
        repository_url = context.repo_url.strip()

        if not repository_url:
            raise ValueError("Repository URL cannot be empty.")

        # Handle SSH-style URLs: git@bitbucket.org:workspace/repo.git
        ssh_match = re.match(r"^git@[\w.-]+:(.+)$", repository_url)
        if ssh_match:
            repository_url = ssh_match.group(1)

        # Strip protocol and domain if present (https://bitbucket.org/, http://, etc.)
        repository_url = re.sub(r"^(https?://)?([\w.-]+\.)?bitbucket\.org/", "", repository_url)

        # Strip trailing slashes
        repository_url = repository_url.strip("/")

        # Remove trailing .git extension
        repository_url = re.sub(r"\.git$", "", repository_url)

        parts = repository_url.split("/")

        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repository URL format: {context.repo_url}")

        workspace, repo_slug = parts[0], parts[1]

        return workspace, repo_slug

    def get_repository(self) -> dict:
        """Fetches the repository metadata from the Bitbucket API."""
        url = f"{self._get_api_base_url()}/repositories/{self.get_repository_owner()}/{self.get_repository_name()}"
        return self._caching_get_json(url)

    def _get_all_pages(self, url: str, params: dict | None = None) -> list:
        """Follows Bitbucket's `next` pagination links, collecting all `values`."""
        results = []
        next_url = url
        next_params = params
        while next_url:
            response = self._caching_get_json(next_url, params=next_params)
            results.extend(response.get("values", []))
            next_url = response.get("next")
            next_params = None  # `next` already contains query params
        return results

    def get_contributors(self) -> list[Person]:
        """Derives a contributor list from commit authors, since Bitbucket has
        no dedicated contributors endpoint. Deduplicates by account UUID/nickname."""
        url = f"{self._get_api_base_url()}/repositories/{self.get_repository_owner()}/{self.get_repository_name()}/commits"
        commits = self._get_all_pages(url)

        seen = set()
        result: list[Person] = []
        for commit in commits:
            author = commit.get("author", {})
            user = author.get("user")

            if user is None:
                # Unassociated author (raw name/email only) — skip, no account to link.
                continue

            if user.get("type") == "team":
                continue

            account_id = user.get("uuid") or user.get("nickname")
            if account_id is None or account_id in seen:
                continue
            seen.add(account_id)

            nickname = user.get("nickname")
            html_url = user.get("links", {}).get("html", {}).get("href")
            self_url = user.get("links", {}).get("self", {}).get("href")

            person = Person(
                account=OnlineAccount(
                    accountName=nickname,
                    accountServiceHomepage="https://bitbucket.org",
                    url=html_url,
                ),
                url=html_url,
                atId=self_url,
            )

            full_name = user.get("display_name")
            if full_name:
                # Bitbucket only gives one free-text "display_name" field
                name_parts = full_name.rsplit(" ", 1)
                if len(name_parts) == 2:
                    person.givenName, person.familyName = name_parts
                else:
                    person.givenName = full_name

            result.append(person)
        return result

    def get_languages(self) -> dict:
        """Returns the repository's single declared language, since Bitbucket's
        API (unlike GitHub's) does not provide a byte-count breakdown by language."""
        repository = self.get_repository()
        language = repository.get("language")
        return {language: 1} if language else {}

    def get_releases(self) -> list:
        """Fetches the list of releases (tags with associated annotations) for the
        repository. Bitbucket has no first-class "releases" concept like GitHub,
        so tags are used as a substitute."""
        return self.get_tags()

    def get_tags(self) -> list:
        """Fetches the list of tags for the repository."""
        url = f"{self._get_api_base_url()}/repositories/{self.get_repository_owner()}/{self.get_repository_name()}/refs/tags"
        return self._get_all_pages(url)

    def get_default_branch(self) -> str:
        """Fetches the default branch name for the repository."""
        repository = self.get_repository()
        return repository.get("mainbranch", {}).get("name", "main")

    def get_clone_url(self):
        repository = self.get_repository()
        clone_links = repository.get("links", {}).get("clone", [])
        for link in clone_links:
            if link.get("name") == "https":
                return link.get("href")
        return None

    def get_download_url(self):
        return (
            f"https://bitbucket.org/{self.get_repository_owner()}/"
            f"{self.get_repository_name()}/get/{self.get_default_branch()}.zip"
        )

    def get_html_url(self):
        repo = self.get_repository()
        return repo.get("links", {}).get("html", {}).get("href")

    def get_date_modified(self):
        return self.get_repository().get("updated_on")

    def get_date_created(self):
        return self.get_repository().get("created_on")

    def get_date_published(self):
        for tag in self.get_tags():
            target = tag.get("target", {})
            date = target.get("date")
            if date:
                return date

    def get_license(self):
        """Bitbucket exposes no license-detection API; this returns None
        unless a future heuristic (e.g. parsing a LICENSE file) is added."""
        return None

    def list_directory(self, path: str = "") -> list[RepositoryItem]:
        """Lists the immediate entries at `path` via Bitbucket's `src` API."""
        url = (
            f"{self._get_api_base_url()}/repositories/{self.get_repository_owner()}/"
            f"{self.get_repository_name()}/src/{self.get_default_branch()}/{path}"
        )
        response = self._caching_get(url)
        if response.status_code == 404:
            raise FileNotFoundOnPlatformError(path)
        raw = response.json()
        values = raw.get("values")
        if values is None:
            raise FileNotFoundOnPlatformError(path)
        return [BitbucketRepositoryItem(entry) for entry in values]

    def _fetch_file(self, path: str, ref: str | None = None) -> RepositoryFile:
        """Fetches a single file's metadata and raw content via Bitbucket's `src` API.

        Bitbucket returns raw file bytes directly at the `src` endpoint for a
        specific file (rather than a JSON envelope with base64 content like
        GitHub/Gitea), so we issue two requests: one for the raw content and
        one for the surrounding directory listing entry that yields metadata
        (path/type), synthesizing a minimal envelope compatible with
        `BitbucketRepositoryFile`.
        """
        commit_ref = ref or self.get_default_branch()
        url = (
            f"{self._get_api_base_url()}/repositories/{self.get_repository_owner()}/"
            f"{self.get_repository_name()}/src/{commit_ref}/{path}"
        )
        response = self._caching_get(url)
        if response.status_code == 404:
            raise FileNotFoundOnPlatformError(path)

        content_type = response.headers.get("Content-Type", "")
        if content_type.startswith("application/json"):
            # Bitbucket returns a directory listing JSON if `path` is actually a directory.
            raise FileNotFoundOnPlatformError(path)

        raw = {
            "path": path,
            "type": "commit_file",
            "_content": response.text,
            "links": {"self": {"href": url}},
        }
        return BitbucketRepositoryFile(raw)