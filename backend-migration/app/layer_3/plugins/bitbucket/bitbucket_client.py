"""
Bitbucket Cloud implementation of GitPlatformClient.

`/src/{commit}/{path}` is two endpoints in one: a directory is a paginated
JSON page (`values` / `next`, default pagelen 10, `size` often absent), and
a file is raw bytes unless `?format=meta` is set. `links.self` on a tree
entry is the API URL, not the HTML browse URL.
"""

import re
from urllib.parse import quote

import requests

from app.layer_3.plugins.shared.foundation.caching_http_client import fetchFunction
from app.layer_3.plugins.shared.git_platform_client import (
    FileNotFoundOnPlatformError,
    GitPlatformClient,
    RepositoryFile,
    RepositoryItem,
)
from app.layer_3.plugins.shared.types.online_account import OnlineAccount
from app.layer_3.plugins.shared.types.person import Person
from app.layer_3.steps.contracts import ExtractionContext

_AUTHOR_RE = re.compile(r"^(?P<name>.*?)\s*<(?P<email>[^>]+)>\s*$")


class BitbucketRepositoryItem(RepositoryItem):
    @property
    def path(self) -> str:
        return (self._raw.get("path") or "").strip("/")

    @property
    def name(self) -> str:
        path = self.path
        return path.rsplit("/", 1)[-1] if path else ""

    @property
    def is_dir(self) -> bool:
        return self._raw.get("type") == "commit_directory"

    def get_html_url(self, client: "BitbucketClient") -> str | None:
        workspace = client.get_repository_owner()
        repo = client.get_repository_name()
        branch = client.get_default_branch()
        if not (workspace and repo and branch):
            return None
        url = (
            f"https://bitbucket.org/{quote(workspace, safe='')}"
            f"/{quote(repo, safe='')}/src/{quote(branch, safe='')}"
        )
        if self.path:
            url += "/" + quote(self.path, safe="/")
        return url


class BitbucketRepositoryFile(BitbucketRepositoryItem, RepositoryFile):
    def __init__(self, raw: dict, content: str | None):
        super().__init__(raw)
        self._content = content

    def get_content(self) -> str | None:
        return self._content


class BitbucketClient(GitPlatformClient):
    """Cached Bitbucket Cloud API client used by the Bitbucket extractors."""

    name = "bitbucket.client"
    _PAGE_LEN = 100
    _MAX_PAGES = 10

    def _get_api_base_url(self) -> str:
        return "https://api.bitbucket.org/2.0"

    def _build_headers(self) -> dict:
        # API tokens use Bearer. App passwords are a different credential and
        # need Basic auth (email:app_password); do not put those in this header.
        headers = {
            "Accept": "application/json",
            "User-Agent": "maSMP-metadata-extraction",
        }
        if self.context.access_token:
            headers["Authorization"] = f"Bearer {self.context.access_token}"
        return headers

    def _extract_repository_info(self, context: ExtractionContext) -> tuple[str, str]:
        """Parse workspace and repo slug from an HTTP or SSH Bitbucket URL."""
        repository_url = (context.repo_url or "").strip()
        if not repository_url:
            raise ValueError("Repository URL cannot be empty.")

        ssh_match = re.match(r"^git@[\w.-]+:(.+)$", repository_url)
        if ssh_match:
            repository_url = ssh_match.group(1)

        repository_url = re.sub(
            r"^(https?://)?((?:[\w-]+\.)*)bitbucket\.org/",
            "",
            repository_url,
            flags=re.IGNORECASE,
        )
        repository_url = repository_url.split("?", 1)[0].split("#", 1)[0]
        repository_url = repository_url.strip("/")
        repository_url = re.sub(r"\.git$", "", repository_url)

        parts = [part for part in repository_url.split("/") if part]
        if len(parts) < 2:
            raise ValueError(f"Invalid repository URL format: {context.repo_url}")
        return parts[0], parts[1]

    def _repo_url(self, *parts: str) -> str:
        workspace = quote(self.get_repository_owner(), safe="")
        repo = quote(self.get_repository_name(), safe="")
        url = f"{self._get_api_base_url()}/repositories/{workspace}/{repo}"
        if parts:
            url += "/" + "/".join(quote(part, safe="") for part in parts)
        return url

    def _src_url(self, ref: str, path: str = "", *, directory: bool = False) -> str:
        # Quote the ref so a branch like feature/foo is not split into path segments.
        url = f"{self._repo_url('src')}/{quote(ref, safe='')}"
        path = path.strip("/")
        if path:
            url += "/" + quote(path, safe="/")
        # Root listings 404 without a trailing slash once a query string is present:
        # .../src/master?pagelen=100 is not the same resource as .../src/master/
        if directory:
            url += "/"
        return url

    def _get_all_pages(self, url: str, params: dict | None = None) -> list[dict]:
        """Follow Bitbucket's opaque `next` link. Do not stop on a missing `size`."""
        query = dict(params) if params else None
        if query is not None:
            query.setdefault("pagelen", self._PAGE_LEN)

        values: list[dict] = []
        seen: set[str] = set()
        pages = 0
        while url and url not in seen and pages < self._MAX_PAGES:
            seen.add(url)
            pages += 1
            response = self._caching_get(url, params=query)
            try:
                data = response.json()
            except ValueError:
                break
            if not isinstance(data, dict):
                break
            page = data.get("values")
            if isinstance(page, list):
                values.extend(item for item in page if isinstance(item, dict))
            url = data.get("next") or ""
            query = None  # `next` is already a fully qualified URL
        return values

    @staticmethod
    def _raise_not_found(exc: requests.exceptions.HTTPError, path: str) -> None:
        if exc.response is not None and exc.response.status_code == 404:
            raise FileNotFoundOnPlatformError(path) from exc
        raise exc

    @staticmethod
    def _decode_text(response: requests.Response) -> str | None:
        if not response.content:
            return ""
        try:
            return response.content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @staticmethod
    def _fetch_raw(url, headers=None, params=None, retries=3, timeout=5):
        merged = dict(headers or {})
        merged["Accept"] = "*/*"
        return fetchFunction(url, headers=merged, params=params, retries=retries, timeout=timeout)

    def get_repository(self) -> dict:
        raw = self._caching_get_json(self._repo_url())
        if not isinstance(raw, dict):
            return {}
        repo = dict(raw)
        html = ((repo.get("links") or {}).get("html") or {}).get("href")
        if html:
            repo.setdefault("html_url", html)
        # Shared extractors look up GitHub's field names.
        if "is_private" in repo:
            repo.setdefault("private", repo["is_private"])
        size = repo.get("size")
        if isinstance(size, (int, float)):
            repo["size_bytes"] = size
            repo["size"] = size / 1024  # shared storage extractor assumes KB
        return repo

    def get_default_branch(self) -> str:
        mainbranch = self.get_repository().get("mainbranch") or {}
        return mainbranch.get("name") or "main"

    def get_html_url(self) -> str | None:
        return self.get_repository().get("html_url")

    def get_clone_url(self) -> str | None:
        clones = (self.get_repository().get("links") or {}).get("clone") or []
        for link in clones:
            if isinstance(link, dict) and link.get("name") == "https" and link.get("href"):
                return link["href"]
        for link in clones:
            if isinstance(link, dict) and link.get("href"):
                return link["href"]
        workspace = self.get_repository_owner()
        repo = self.get_repository_name()
        if workspace and repo:
            return f"https://bitbucket.org/{workspace}/{repo}.git"
        return None

    def get_download_url(self) -> str | None:
        workspace = self.get_repository_owner()
        repo = self.get_repository_name()
        branch = self.get_default_branch()
        if not (workspace and repo and branch):
            return None
        return (
            f"https://bitbucket.org/{quote(workspace, safe='')}"
            f"/{quote(repo, safe='')}/get/{quote(branch, safe='')}.zip"
        )

    def get_date_created(self) -> str | None:
        return self.get_repository().get("created_on")

    def get_date_modified(self) -> str | None:
        return self.get_repository().get("updated_on")

    def get_date_published(self) -> str | None:
        tags = self.get_tags()
        if not tags:
            return None
        latest = tags[0]
        return latest.get("date") or (latest.get("target") or {}).get("date")

    def get_languages(self) -> dict:
        """Bitbucket has no language-stats endpoint. The repo has one primary language."""
        language = self.get_repository().get("language")
        if not language:
            return {}
        return {language: 1}

    def get_tags(self) -> list:
        tags = self._get_all_pages(self._repo_url("refs", "tags"), {"sort": "-target.date"})

        def timestamp(tag: dict) -> str:
            return tag.get("date") or (tag.get("target") or {}).get("date") or ""

        tags.sort(key=timestamp, reverse=True)
        return tags

    def get_releases(self) -> list:
        """Bitbucket has no releases API. Tags are mapped to the fields the extractors read."""
        releases = []
        for tag in self.get_tags():
            name = tag.get("name")
            if not name:
                continue
            releases.append({
                "name": name,
                "tag_name": name,
                "html_url": ((tag.get("links") or {}).get("html") or {}).get("href"),
                "published_at": tag.get("date") or (tag.get("target") or {}).get("date"),
            })
        return releases

    def get_contributors(self) -> list[Person]:
        """Bitbucket has no contributors endpoint. Unique commit authors stand in for it."""
        commits = self._get_all_pages(self._repo_url("commits"))
        people: list[Person] = []
        seen: set[str] = set()
        for commit in commits:
            author = commit.get("author") or {}
            user = author.get("user") or {}
            key = user.get("uuid") or user.get("account_id") or author.get("raw")
            if not key or key in seen:
                continue
            person = self._person_from_author(author)
            if person is None:
                continue
            seen.add(key)
            people.append(person)
        return people

    @staticmethod
    def _person_from_author(author: dict) -> Person | None:
        user = author.get("user") or {}
        raw = author.get("raw") or ""
        name = user.get("display_name")
        email = None
        match = _AUTHOR_RE.match(raw)
        if match:
            email = match.group("email").strip() or None
            if not name:
                name = match.group("name").strip() or None
        elif raw and not name:
            name = raw.strip() or None

        html = ((user.get("links") or {}).get("html") or {}).get("href")
        api_url = ((user.get("links") or {}).get("self") or {}).get("href")
        nickname = user.get("nickname")
        person = Person(email=email, url=html, atId=api_url)
        if nickname or html:
            person.account = OnlineAccount(
                accountName=nickname,
                accountServiceHomepage="https://bitbucket.org",
                url=html,
            )
        if name:
            parts = name.rsplit(" ", 1)
            if len(parts) == 2:
                person.givenName, person.familyName = parts
            else:
                person.givenName = name
        if not any([person.givenName, person.familyName, person.email, person.url]):
            return None
        return person

    def list_directory(self, path: str = "") -> list[RepositoryItem]:
        ref = self.get_default_branch()
        url = self._src_url(ref, path, directory=True)
        try:
            response = self._caching_get(url, params={"pagelen": self._PAGE_LEN})
        except requests.exceptions.HTTPError as exc:
            self._raise_not_found(exc, path)
        try:
            data = response.json()
        except ValueError as exc:
            raise FileNotFoundOnPlatformError(path) from exc
        if not isinstance(data, dict) or "values" not in data:
            raise FileNotFoundOnPlatformError(path)

        entries = [item for item in data.get("values", []) if isinstance(item, dict)]
        next_url = data.get("next")
        if next_url:
            entries.extend(self._get_all_pages(next_url))
        return [BitbucketRepositoryItem(entry) for entry in entries]

    def _fetch_file(self, path: str, ref: str | None = None) -> RepositoryFile:
        ref = ref or self.get_default_branch()
        url = self._src_url(ref, path)
        try:
            meta_response = self._caching_get(url, params={"format": "meta"})
        except requests.exceptions.HTTPError as exc:
            self._raise_not_found(exc, path)
        try:
            meta = meta_response.json()
        except ValueError as exc:
            raise FileNotFoundOnPlatformError(path) from exc
        if not isinstance(meta, dict) or meta.get("type") != "commit_file":
            raise FileNotFoundOnPlatformError(path)

        try:
            raw_response = self._caching_get(url, fetch_function=self._fetch_raw)
        except requests.exceptions.HTTPError as exc:
            self._raise_not_found(exc, path)
        return BitbucketRepositoryFile(meta, self._decode_text(raw_response))