import requests
from typing import Any

from app.layer_3.plugins.shared.foundation.caching_http_client import CachingHttpClient
from app.layer_3.steps.contracts import ExtractionState, ExtractionContext
from app.layer_3.plugins.shared.types.person import Person
from app.layer_3.plugins.shared.types.organization import Organization
from app.layer_3.plugins.shared.types.online_account import OnlineAccount

class OpenAlexClient(CachingHttpClient):

    name = 'de.zbmed.open.alex.client'

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        super().__init__(context, state)
        self.BASE_URL = "https://api.openalex.org/works"

    def get_work(self, doi: str) -> dict[str, Any] | None:
        clean_doi = doi.replace("https://doi.org/", "").replace("doi:", "")
        url = f"{self.BASE_URL}/doi:{clean_doi}"
        try:
            response = self._caching_get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

    def get_alternate_title(self, doi: str):
        work = self.get_work(doi)
        if work and work.get('title'):
            return work['title']

    def get_authors(self, doi: str) -> list[Person]:
        """Normalize authorships from an OpenAlex work payload."""
        authors: list[Person] = []
        work = self.get_work(doi)
        if not work:
            return authors

        for author_entry in work.get("authorships", []) or []:
            author = author_entry.get("author", {}) if isinstance(author_entry, dict) else {}
            display_name = author.get("display_name")
            if not display_name:
                continue

            name_parts = display_name.rsplit(" ", 1)
            if len(name_parts) == 2:
                given_name, family_name = name_parts
            else:
                given_name, family_name = display_name, None

            institutions = author_entry.get("institutions", []) or []
            affiliation = None
            if institutions:
                institution = institutions[0]
                affiliation = Organization(
                    name=institution.get("display_name"),
                    url=institution.get("homepage_url"),
                    sameAs=institution.get("id") or institution.get("ror"),
                )

            orcid = author.get("orcid")
            openalex_id = author.get("id")

            person = Person(
                givenName=given_name,
                familyName=family_name,
                atId=orcid or openalex_id,
                sameAs=openalex_id if orcid else None,
                affiliation=affiliation,
            )
            authors.append(person)

        return authors

    def get_keywords(self, doi: str) -> list[str]:
        keywords: list[str] = []
        work = self.get_work(doi)
        if not work:
            return keywords
        for keyword in work.get("keywords", []) or []:
            if isinstance(keyword, dict) and keyword.get("display_name"):
                keywords.append(keyword["display_name"])
            elif isinstance(keyword, str) and keyword:
                keywords.append(keyword)
        return keywords

    def _build_headers(self):
        return {}