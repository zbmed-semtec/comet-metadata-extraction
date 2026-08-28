import requests
from typing import Any

from app.layer_3.plugins.shared.foundation.caching_http_client import CachingHttpClient
from app.layer_3.steps.contracts import ExtractionState, ExtractionContext

class OpenAlexClient(CachingHttpClient):
    
    name = 'de.zbmed.open.alex.client'

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        super().__init__(context, state)
        self.BASE_URL = "https://api.openalex.org/works"

    def get_work(self, doi : str) -> dict[str, Any] | None:
        clean_doi = doi.replace("https://doi.org/", "").replace("doi:", "")
        url = f"{self.BASE_URL}/doi:{clean_doi}"
        try:
            response = self._caching_get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def get_alternate_title(self, doi : str):
        work = self.get_work(doi)
        if work and work.get('title'):
            return work['title']

    def get_authors(self, doi : str):
        """Normalize authorships from an OpenAlex work payload into Person-shaped dicts."""
        authors: list[dict] = []
        for author_entry in self.get_work(doi).get("authorships", []) or []:
            author = author_entry.get("author", {}) if isinstance(author_entry, dict) else {}
            display_name = author.get("display_name")
            if not display_name:
                continue
            name_parts = display_name.rsplit(" ", 1)
            if len(name_parts) == 2:
                given_name, family_name = name_parts
            else:
                given_name, family_name = display_name, ""
            person = {"@type": "Person", "familyName": family_name, "givenName": given_name}
            if author.get("orcid"):
                person["@id"] = author["orcid"]
            authors.append(person)
        return authors

    def get_keywords(self, doi : str) -> list[str]:
        keywords: list[str] = []
        for keyword in self.get_work(doi).get("keywords", []) or []:
            if isinstance(keyword, dict) and keyword.get("display_name"):
                keywords.append(keyword["display_name"])
            elif isinstance(keyword, str) and keyword:
                keywords.append(keyword)
        return keywords

    def _build_headers(self):
        return {}