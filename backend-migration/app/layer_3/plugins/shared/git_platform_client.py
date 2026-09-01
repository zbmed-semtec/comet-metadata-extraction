"""
Base class for platform-specific Git repository clients (GitHub, GitLab, Codeberg, etc.).

Design principle: this class defines a *normalized* contract for repository
traversal (list a directory, fetch a file) and owns all platform-agnostic
logic built on top of that contract (recursive traversal, README/LICENSE/
CITATION/CHANGELOG discovery, citation parsing). Platform-specific API shapes
(GitHub's dual-purpose "contents" endpoint vs. GitLab's separate "tree"/"files"
endpoints, etc.) are implemented by subclasses behind `list_directory` and
`get_file`, and never leak into this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import yaml

from app.layer_3.plugins.shared.foundation.caching_http_client import CachingHttpClient
from app.layer_3.steps.contracts import ExtractionContext, ExtractionState
from app.layer_3.plugins.url_pattern_matcher_plugin import URLPatternMatcher
from app.layer_3.plugins.shared.bibtex import parse_bibtex
from app.layer_3.plugins.shared.person import Person

class RepositoryItem(ABC):
    """Thin wrapper around a platform's raw JSON representation of a single
    file/directory entry in a repository tree.

    Subclasses interpret the raw payload according to their platform's API
    shape and expose a normalized surface (name/path/is_dir) to the rest of
    the codebase.
    """

    def __init__(self, raw: dict):
        self._raw = raw

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def path(self) -> str:
        pass

    @property
    @abstractmethod
    def is_dir(self) -> bool:
        pass

    @abstractmethod
    def get_html_url(client : "GitPlatformClient") -> str | None:
        ...

class RepositoryFile(RepositoryItem, ABC):
    """Thin wrapper around a platform's raw JSON representation of a single
    fetched file (metadata + content).

    Subclasses know how their platform encodes file content (e.g. base64)
    and decode it in `get_content`.
    """

    @abstractmethod
    def get_content(self) -> str | None:
        """Returns the file's decoded text content, or None if the file is
        binary / not text-decodable."""
        pass

class FileNotFoundOnPlatformError(Exception):
    """Raised when a requested file path does not exist / is not a file on the platform."""
    pass


class GitPlatformClient(CachingHttpClient, ABC):
    """Abstract base class for platform-specific Git repository clients.

    Provides a common interface for interacting with different Git hosting platforms
    (Codeberg, GitHub, GitLab, etc.), handling repository metadata, contents, and resources.
    """

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        """Initializes the client with extraction context/state and sets up request headers.

        Args:
            context: Extraction context containing repository URL and access token
            state: Extraction state for tracking extraction progress
        """
        super().__init__(context, state)
        self._repository_owner: str | None = None
        self._repository_name: str | None = None
        self._parsed_citations: list[dict] | None = None
        self._dois_from_citation: set[str] | None = None
        self._dois_from_readme: set[str] | None = None
        self._parsed_bibtex: list[dict] | None = None
        self._file_cache: dict[tuple[str, str | None], RepositoryFile] = {}
        self.headers = self._build_headers()

    # ------------------------------------------------------------------
    # Platform identity / API basics — must be implemented per platform
    # ------------------------------------------------------------------

    @abstractmethod
    def _get_api_base_url(self) -> str:
        """Returns the base URL for the platform's API."""
        pass

    @abstractmethod
    def _build_headers(self) -> dict:
        """Builds request headers specific to the platform's API requirements."""
        pass

    @abstractmethod
    def _extract_repository_info(self, context: ExtractionContext) -> tuple[str, str]:
        """Parses the repository owner and name from the context's repository URL.

        Returns:
            A tuple of (owner, repository_name)
        """
        pass

    def get_repository_owner(self) -> str:
        """Returns the repository owner, extracting and caching it if not already set."""
        if self._repository_owner is None:
            self._repository_owner, self._repository_name = self._extract_repository_info(self.context)
        return self._repository_owner

    def get_repository_name(self) -> str:
        """Returns the repository name, extracting and caching it if not already set."""
        if self._repository_name is None:
            self._repository_owner, self._repository_name = self._extract_repository_info(self.context)
        return self._repository_name

    # ------------------------------------------------------------------
    # Repository metadata — must be implemented per platform
    # ------------------------------------------------------------------

    @abstractmethod
    def get_repository(self) -> dict:
        """Fetches the repository metadata."""
        pass

    @abstractmethod
    def get_contributors(self) -> list[Person]:
        """Fetches the contributor activity data for the repository."""
        pass

    @abstractmethod
    def get_languages(self) -> dict:
        """Fetches the programming languages used in the repository."""
        pass

    @abstractmethod
    def get_releases(self) -> list:
        """Fetches the list of releases for the repository."""
        pass

    @abstractmethod
    def get_tags(self) -> list:
        """Fetches the list of tags for the repository."""
        pass

    @abstractmethod
    def get_default_branch(self) -> str:
        """Fetches the default branch name for the repository."""
        pass

    @abstractmethod
    def get_html_url(self) -> str | None:
        """Fetches the repositories' clone url using the api"""
        pass

    @abstractmethod
    def get_clone_url(self) -> str | None:
        """Fetches the repositories' clone url using the api"""
        pass

    @abstractmethod
    def get_download_url(self) -> str | None:
        """Fetches the repositories' download url using the api"""
        pass

    @abstractmethod
    def get_date_created(self) -> str | None:
        pass

    @abstractmethod
    def get_date_modified(self) -> str | None:
        pass

    @abstractmethod
    def get_date_published(self) -> str | None:
        pass

    def get_name(self) -> str | None:
        return self.get_repository().get('name')

    # ------------------------------------------------------------------
    # Normalized content contract — must be implemented per platform.
    #
    # These two methods are the *only* place platform-specific content-API
    # shape is allowed to live. Everything below this point is generic
    # traversal/discovery logic built purely on top of these two calls.
    # ------------------------------------------------------------------

    @abstractmethod
    def list_directory(self, path: str = "") -> list[RepositoryItem]:
        """Lists the immediate entries (files & directories) at the given path.

        Args:
            path: Directory path relative to the repo root. "" means repo root.

        Returns:
            A list of RepoEntry describing immediate children of `path`.

        Raises:
            FileNotFoundOnPlatformError: if `path` does not exist or is not a directory.
        """
        pass

    def get_file(self, path: str, ref: str | None = None) -> RepositoryFile:
        """Fetches a single file's metadata and content.

        Args:
            path: File path relative to the repo root.
            ref: Branch, tag, or commit SHA (defaults to the repository's default branch).

        Returns:
            A RepositoryFile wrapping the platform's raw response for `path`.

        Raises:
            FileNotFoundOnPlatformError: if `path` does not exist or is not a file.
        """
        cache_key = (path, ref)
        if cache_key not in self._file_cache:
            self._file_cache[cache_key] = self._fetch_file(path, ref)
        return self._file_cache[cache_key]

    @abstractmethod
    def _fetch_file(self, path: str, ref: str | None = None) -> RepositoryFile:
        """Platform-specific fetch of a single file's metadata + content.

        Subclasses implement this instead of `get_file` directly; `get_file`
        wraps this with an in-memory cache so repeated lookups of the same
        (path, ref) don't re-hit the platform API shape parsing / decoding.

        Raises:
            FileNotFoundOnPlatformError: if `path` does not exist or is not a file.
        """
        pass

    # ------------------------------------------------------------------
    # Generic traversal built on the normalized contract above
    # ------------------------------------------------------------------

    def list_contents(self, path: str = "", depth: int = 2) -> list[RepositoryItem]:
        """Recursively lists repository file/directory entries up to the given depth.

        Args:
            path: Directory path to start from ("" = repo root).
            depth: How many levels of subdirectories to recurse into.
                   depth=1 lists only the immediate contents of `path`.

        Returns:
            A flat list of RepoEntry for all discovered files/directories.
        """
        if depth <= 0:
            return []

        try:
            entries = self.list_directory(path)
        except FileNotFoundOnPlatformError:
            return []

        # Iterate over a stable copy; accumulate into a separate list so we
        # never mutate the collection we're iterating over.
        results: list[RepositoryItem] = list(entries)
        for entry in entries:
            if entry.is_dir:
                results.extend(self.list_contents(entry.path, depth - 1))
        return results

    def _filter_files(self, filter_fn) -> list[RepositoryItem]:
        files = self.list_contents()
        return [f for f in files if not f.is_dir and filter_fn(f)]

    def _discover_files_by_prefix(self, prefix: str) -> list[RepositoryItem]:
        """Helper method to discover files matching a given name prefix (case-insensitive)."""
        return self._filter_files(lambda f: f.name.lower().startswith(prefix))

    def _discover_files_by_postfix(self, postfix: str) -> list[RepositoryItem]:
        """Helper method to discover files matching a given name postfix (case-insensitive)."""
        return self._filter_files(lambda f: f.name.lower().endswith(postfix))

    def discover_readme_candidates(self) -> list[RepositoryItem]:
        """Finds files in the repository whose names suggest they are README files."""
        return self._discover_files_by_prefix("readme")

    def discover_license_candidates(self) -> list[RepositoryItem]:
        """Finds files in the repository whose names suggest they are license files."""
        return self._discover_files_by_prefix("license")

    def discover_citation_candidates(self) -> list[RepositoryItem]:
        """Finds files in the repository whose names suggest they are citation files."""
        return self._discover_files_by_prefix("citation")

    def discover_changelog_candidates(self) -> list[RepositoryItem]:
        """Finds files in the repository whose names suggest they are changelog files."""
        return self._discover_files_by_prefix("changelog")

    def get_multiple_files(self, paths: list[str]) -> list[RepositoryFile]:
        files = []
        for path in paths:
            try:
                file = self.get_file(path)
            except FileNotFoundOnPlatformError:
                continue
            if file.get_content() is not None:
                files.append(file)
        return files

    def get_readme_candidate_files(self) -> list[RepositoryFile]:
        """Fetches the content of all discovered README candidate files."""
        candidates = self.discover_readme_candidates()
        return self.get_multiple_files([c.path for c in candidates])

    def get_license_candidate_files(self) -> list[RepositoryFile]:
        """Fetches the content of all discovered license candidate files."""
        candidates = self.discover_license_candidates()
        return self.get_multiple_files([c.path for c in candidates])

    def get_citation_candidate_files(self) -> list[RepositoryFile]:
        """Fetches the content of all discovered citation candidate files."""
        candidates = self.discover_citation_candidates()
        return self.get_multiple_files([c.path for c in candidates])

    def get_changelog_candidate_files(self) -> list[RepositoryFile]:
        """Fetches the content of all discovered changelog candidate files."""
        candidates = self.discover_changelog_candidates()
        return self.get_multiple_files([c.path for c in candidates])

    def get_bibtex_candidate_files(self) -> list[RepositoryFile]:
            """Fetches the content of all discovered changelog candidate files."""
            candidates = self._discover_files_by_postfix(".bib")
            return self.get_multiple_files([c.path for c in candidates])

    def get_parsed_citations(self) -> list[dict]:
        if self._parsed_citations is None:
            citation_files = self.get_citation_candidate_files()
            parsed = []
            for file in citation_files:
                content = file.get_content()
                if not content:
                    continue
                try:
                    cff_data = yaml.safe_load(content)
                except yaml.YAMLError:
                    continue
                if cff_data is not None and isinstance(cff_data, dict) and cff_data.get("cff-version"):
                    parsed.append(cff_data)
            self._parsed_citations = parsed
        return self._parsed_citations
    
    def get_dois_from_readmes(self) -> set[str]:
        if self._dois_from_readme is None:
            result = set()
            readmes = self.get_readme_candidate_files()
            for readme in readmes:
                content = readme.get_content()
                if content:
                    result.update(URLPatternMatcher.check_zenodo_badge(content))
            self._dois_from_readme = result
        return self._dois_from_readme
    
    def get_dois_from_parsed_citaitons(self) -> set[str]:
        if self._dois_from_citation is None:
            citations = self.get_parsed_citations()
            identifiers = set()
            for cff in citations:
                for cffIdentifier in cff.get("identifiers", []):
                    if cffIdentifier.get("type") == "doi" and cffIdentifier.get("value"):
                        doi_url = f"https://doi.org/{cffIdentifier['value']}"
                        identifiers.add(doi_url)
                doi = cff.get("doi")
                if doi:
                    doi_url = f"https://doi.org/{doi}"
                    identifiers.add(doi_url)
            self._dois_from_citation = identifiers
        return self._dois_from_citation

    def get_parsed_bibtex(self) -> list[dict]:
        if self._parsed_bibtex is None:
            result = []
            filesA = {f.name: f for f in self.get_bibtex_candidate_files()}
            filesB = {f.name: f for f in self.get_readme_candidate_files()}
            filesA.update(filesB)
            files = filesA.values()
            for readme in files:
                for item in parse_bibtex(readme.get_content()):
                    result.append(item)
            self._parsed_bibtex = result
        return self._parsed_bibtex