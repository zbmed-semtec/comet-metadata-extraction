from abc import ABC, abstractmethod
from time import sleep
import requests
from app.layer_3.plugins.shared.foundation.named_stateful_singleton import NamedStatefulSingleton
from app.layer_3.steps.contracts import ExtractionState, ExtractionContext


class FetchError(Exception):
    """Raised when an HTTP GET request fails after all retries are exhausted."""
    pass


def fetchFunction(
    url: str,
    headers: dict = None,
    params: dict = None,
    retries: int = 3,
    timeout: int = 5,
) -> requests.Response:
    """Performs a GET request with up to `retries` attempts on transient failures.

    Raises:
        FetchError: if the request fails on all attempts (timeout, connection
            error, or non-2xx response).
    """
    last_exception: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as exc:
            last_exception = exc
            print(f"[fetchFunction] transient error on attempt {attempt}/{retries} for url: {url} ({exc})")
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            # Retry on server errors (5xx); don't retry on client errors (4xx).
            if status is not None and 500 <= status < 600:
                last_exception = exc
                print(f"[fetchFunction] server error {status} on attempt {attempt}/{retries} for url: {url}")
            else:
                raise

        if attempt < retries:
            sleep(min(2 ** (attempt - 1), 8))  # simple exponential backoff, capped

    raise FetchError(f"Failed to fetch {url} after {retries} attempts") from last_exception


class CachingHttpClient(NamedStatefulSingleton, ABC):
    """Base client providing HTTP request caching functionality."""

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        super().__init__(context, state)
        self.cache: dict[tuple, requests.Response] = {}
        self.headers = {}

    def _caching_get(
        self,
        url: str,
        params: dict = None,
        fetch_function=fetchFunction,
    ) -> requests.Response:
        """Fetches a URL using the given fetch function, caching successful responses for reuse."""
        cache_key = (url, tuple(sorted(params.items()))) if params else (url, ())

        if cache_key not in self.cache:
            response = fetch_function(url, headers=self.headers, params=params)
            self.cache[cache_key] = response

        return self.cache[cache_key]

    @abstractmethod
    def _build_headers(self) -> dict:
        """Builds request headers specific to the platform's API requirements."""
        pass