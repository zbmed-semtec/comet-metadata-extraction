"""
Platform-agnostic extraction plugins for Git-hosted repositories.

Each class extracts one schema.org/codemeta/maSMP property. These classes are abstract on their own (no client) -- each platform's collection.py mixes one of these with its concrete *BaseExtractor (e.g. GitHubBaseExtractor) to produce a runnable plugin.

Where a property has multiple sources (API, CITATION.cff, BibTeX, README, OpenAlex), each is collected independently with its own confidence score;
conflict resolution across sources happens later in merge_* steps.
"""

import re
import datetime
from app.layer_3.plugins.shared.types.person import Person
from app.layer_3.plugins.shared.types.online_account import OnlineAccount
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor
from app.layer_3.plugins.url_pattern_matcher_plugin import URLPatternMatcher
from app.layer_3.plugins.shared.utils import match_license_text, dependency_files, iso_dt_to_str
from app.layer_3.plugins.shared.external_services.wayback_client import WaybackClient
from app.layer_3.plugins.shared.external_services.software_heritage_client import SoftwareHeritageClient
from app.layer_3.plugins.shared.external_services.open_alex_client import OpenAlexClient
from app.layer_3.plugins.shared.utils import parse_contributor_names


class GitPlatformNameExtractor(GitPlatformBaseExtractor):
    """schema:name"""

    extracts = {'https://schema.org/name'}

    def extract(self, context, state):
        
        # getting the name from the API
        client = self.get_client(context, state)
        name = client.get_name()
        if name:
            state.metadata_collector.collect("Platform API", "https://schema.org/name", name, 0.95)
        
        # getting the name from the CFF
        cffs = client.get_parsed_citations()
        for cff in cffs:
            if 'title' in cff:
                state.metadata_collector.collect("CFF File", "https://schema.org/name", cff['title'], 0.90)

        entries = client.get_parsed_bibtex()
        for entry in entries:
            fields = entry.get('fields', {})
            if 'title' in fields:
                state.metadata_collector.collect("BibTeX", "https://schema.org/name", fields['title'], 0.85)
        return state

class GitPlatformDescriptionExtractor(GitPlatformBaseExtractor):
    """schema:description"""

    extracts = {'https://schema.org/description'}

    def extract(self, context, state):
        # getting the description from the GitLab API
        result = self.get_client(context, state).get_repository()
        if result.get("description"):
            state.metadata_collector.collect("Platform API", "https://schema.org/description", result['description'], 0.95)

        # getting the description from the CFF
        client = self.get_client(context, state)
        cffs = client.get_parsed_citations()
        for cff in cffs:
            # non standard but seen 'in the wild'
            if 'abstract' in cff:
                state.metadata_collector.collect("CFF File", "https://schema.org/description", cff['abstract'], 0.90)
            # non standard but seen 'in the wild'
            if 'description' in cff:
                state.metadata_collector.collect("CFF File", "https://schema.org/description", cff['description'], 0.90)
        return state

class GitPlatformUrlExtractor(GitPlatformBaseExtractor):
    """schema:url"""

    extracts = {'https://schema.org/url'}

    def extract(self, context, state):
        # getting the URL from the Platform API
        result = self.get_client(context, state).get_html_url()
        if result:
            state.metadata_collector.collect("Platform API", "https://schema.org/url", result, 0.95)

        # getting the URL from CITATION.cff
        client = self.get_client(context, state)
        cffs = client.get_parsed_citations()
        for cff in cffs:
            if 'url' in cff:
                state.metadata_collector.collect("CFF File", 'https://schema.org/url', cff['url'], 0.90)
        return state

class GitPlatformCodeRepositoryExtractor(GitPlatformBaseExtractor):
    """schema:codeRepository"""

    extracts = {'https://schema.org/codeRepository', 'https://codemeta.github.io/terms/codeRepository'}

    def extract(self, context, state):
        clone_url = self.get_client(context, state).get_clone_url()
        if clone_url:
            state.metadata_collector.collect("Platform API", "https://schema.org/codeRepository", clone_url, 0.95)
            state.metadata_collector.collect("Platform API", 'https://codemeta.github.io/terms/codeRepository', clone_url, 0.95)
        return state

class GitPlatformProgrammingLanguageExtractor(GitPlatformBaseExtractor):
    """schema:programmingLanguage"""

    extracts = {'https://schema.org/programmingLanguage'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_languages()
        if result and len(result) > 0:
            languages = list(result.keys())
            state.metadata_collector.collect("Platform API", "https://schema.org/programmingLanguage", languages, 0.95)
        return state

class GitPlatformAuthorExtractor(GitPlatformBaseExtractor):
    """schema:author"""

    extracts = {'https://schema.org/author'}

    CFF_CONFIDENCE = 0.90
    OPENALEX_CONFIDENCE = 0.95
    BIBTEX_CONFIDENCE = 0.85

    def extract(self, context, state):
        client = self.get_client(context, state)

        self._extract_cff(client, state)
        self._extract_openalex(context, client, state)
        self._extract_bibtex(client, state)

        return state

    def _collect(self, state, source, persons, confidence):
        if persons:
            state.metadata_collector.collect(source, "https://schema.org/author", persons, confidence)

    def _extract_cff(self, client, state):
        for cff in client.get_parsed_citations():
            authors = []
            for cff_author in cff.get("authors", []):
                orcid = cff_author.get("orcid")
                person = Person(
                    familyName=cff_author.get("family-names"),
                    givenName=cff_author.get("given-names"),
                    identifier=self._normalize_orcid(orcid) if orcid else None,
                    name=cff_author.get("name"),
                )
                if any([person.name, person.givenName, person.familyName]):
                    authors.append(person.to_jsonld_dict())
            self._collect(state, "CFF File", authors, self.CFF_CONFIDENCE)

    @staticmethod
    def _normalize_orcid(orcid: str) -> str:
        return orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"

    def _extract_openalex(self, context, client, state):
        dois = client.get_dois_from_parsed_citations().union(client.get_dois_from_readmes())
        for doi in dois:
            authors = OpenAlexClient.get_or_create(context, state).get_authors(doi)
            authors = [author.to_jsonld_dict() for author in authors]
            self._collect(state, "OpenAlex", authors, self.OPENALEX_CONFIDENCE)

    def _extract_bibtex(self, client, state):
        for bibtex in client.get_parsed_bibtex():
            author_field = bibtex.get('fields', {}).get('author')
            if not author_field:
                continue

            persons = []
            for entry in author_field.split(" and "):
                entry = entry.strip()
                if not entry:
                    continue

                if "," in entry:
                    last, given = (part.strip() for part in entry.split(",", 1))
                    person = Person(familyName=last or None, givenName=given or None)
                else:
                    person = Person(name=entry)

                if any([person.name, person.givenName, person.familyName]):
                    persons.append(person.to_jsonld_dict())

            self._collect(state, "BibTex", persons, self.BIBTEX_CONFIDENCE)

class GitPlatformLicenseExtractor(GitPlatformBaseExtractor):
    """schema:license"""

    extracts = {'https://schema.org/license'}

    def extract(self, context, state):
        # from License File
        client = self.get_client(context, state)
        license_candidates = client.get_license_candidate_files()
        for license_candidate in license_candidates:
            text = license_candidate.get_content()
            result = match_license_text(text)
            spdx_id = result["detected_license_expression_spdx"]
            conf    = result["percentage_of_license_text"] * 0.95 / 100.0
            license_object = {
                '@type': 'CreativeWork',
                '@context': 'https://schema.org',
                'name': spdx_id,
                'url' : f'https://spdx.org/licenses/{spdx_id}.html'
            }
            state.metadata_collector.collect("License File", 'https://schema.org/license', license_object, conf)
        # From CFF File
        citations = client.get_parsed_citations()
        for citation in citations:
            if 'license' in citation:
                license_value = citation.get('license')
                if license_value:
                    result = match_license_text(license_value)
                    spdx_id = result["detected_license_expression_spdx"]
                    conf    = result["percentage_of_license_text"] * 0.85 / 100.0
                    if spdx_id:
                        license_object = {
                            '@type': 'CreativeWork',
                            '@context': 'https://schema.org',
                            'name': spdx_id,
                            'url' : f'https://spdx.org/licenses/{spdx_id}.html'
                        }
                    else:
                        # Fall back to using the raw citation value as the name
                        # if no SPDX match could be determined.
                        license_object = {
                            '@type': 'CreativeWork',
                            '@context': 'https://schema.org',
                            'name': license_value
                        }
                    state.metadata_collector.collect(
                        "CFF File", 'https://schema.org/license', license_object, conf
                    )
            if 'license-url' in citation:
                license_url = citation.get('license-url')
                if license_url:
                    license_object = {
                        '@type': 'CreativeWork',
                        '@context': 'https://schema.org',
                        'url': license_url
                    }
                    # license-url is an explicit, author-provided value, so we treat
                    # it with high confidence, similar to other direct metadata fields.
                    conf = 0.9
                    state.metadata_collector.collect(
                        "CITATION.cff", 'https://schema.org/license', license_object, conf
                    )
        return state

class GitPlatformIdentifierExtractor(GitPlatformBaseExtractor):
    """schema:identifier"""

    extracts = {'https://schema.org/identifier'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        
        # from CFF
        identifiers = list(client.get_dois_from_parsed_citations())
        if len(identifiers) > 0:
            state.metadata_collector.collect("CFF File", "https://schema.org/identifier", identifiers, 0.9)

        # from README
        identifiers = list(client.get_dois_from_readmes())
        if len(identifiers) > 0:
            state.metadata_collector.collect("README", "https://schema.org/identifier", identifiers, 0.75)

        identifiers = []
        for entry in client.get_parsed_bibtex():
            fields = entry.get("fields", {})
            if 'doi' in fields:
                identifiers.append(fields['doi'])
        if len(identifiers) > 0:
            state.metadata_collector.collect("BibTeX", "https://schema.org/identifier", identifiers, 0.85)

        return state

class GitPlatformCitationExtractor(GitPlatformBaseExtractor):
    """schema:citation"""

    extracts = {'https://schema.org/citation', "https://schema.org/alternateName", "https://codemeta.github.io/terms/referencePublication"}

    def _build_citation_entry(self, ref: dict) -> dict:
        """Build a citation entry (@type Article/Software/etc) from a CFF reference-like dict."""
        ref_type = ref.get("type")
        type_map = {
            "article": "Article",
            "software": "SoftwareApplication",
            "book": "Book",
            "conference-paper": "Article",
            "dataset": "Dataset",
        }
        citation_entry = {"@type": type_map.get(ref_type, "CreativeWork")}

        doi_value = ref.get("doi")
        if doi_value:
            citation_entry["@id"] = f"https://doi.org/{str(doi_value)}"

        title = ref.get("title")
        if title:
            citation_entry["title"] = str(title)

        authors_field = ref.get("authors") or []
        author_list: list[dict] = []
        for author in authors_field:
            if not isinstance(author, dict):
                continue
            given = author.get("given-names")
            family = author.get("family-names")
            if not given and not family and not author.get("orcid"):
                continue
            person: dict[str, str] = {"@type": "Person"}
            if given:
                person["givenName"] = given
            if family:
                person["familyName"] = family
            if author.get("orcid"):
                person["@id"] = author["orcid"]
            author_list.append(person)
        if author_list:
            citation_entry["author"] = author_list

        return citation_entry

    def extract(self, context, state):
        client = self.get_client(context, state)
        # from cff
        citations = client.get_parsed_citations()
        for cff in citations:
            preferred_citation = cff.get("preferred-citation")
            if preferred_citation and isinstance(preferred_citation, dict):
                citation_entry = {"@type": "Article"}
                doi_value = preferred_citation.get("doi")
                if doi_value:
                    doi_url = f"https://doi.org/{str(doi_value)}"
                    citation_entry["@id"] = doi_url
                title = preferred_citation.get("title")
                if title:
                    citation_entry["title"] = str(title)
                    state.metadata_collector.collect("CFF File", "https://schema.org/alternateName", str(title), 0.90)
                authors_field = preferred_citation.get("authors") or []
                author_list: list[dict] = []
                for author in authors_field:
                    if not isinstance(author, dict):
                        continue
                    given = author.get("given-names")
                    family = author.get("family-names")
                    if not given and not family and not author.get("orcid"):
                        continue
                    person: dict[str, str] = {"@type": "Person"}
                    if given:
                        person["givenName"] = given
                    if family:
                        person["familyName"] = family
                    if author.get("orcid"):
                        person["@id"] = author["orcid"]
                    author_list.append(person)
                if author_list:
                    citation_entry["author"] = author_list
                state.metadata_collector.collect("CFF File", "https://codemeta.github.io/terms/referencePublication", citation_entry, 0.90)
            else:
                # If no preferred-citation, we can still try to extract a DOI from the CFF file
                doi_value = cff.get("doi")
                if doi_value:
                    doi_url = f"https://doi.org/{str(doi_value)}"
                    citation_entry = {"@type": "Software", "@id": doi_url}
                    state.metadata_collector.collect("CFF File", "https://schema.org/citation", citation_entry, 0.90)

            # Extract 'references' field from CFF (list of related works/citations)
            references_field = cff.get("references") or []
            for ref in references_field:
                if not isinstance(ref, dict):
                    continue
                ref_citation_entry = self._build_citation_entry(ref)
                state.metadata_collector.collect("CFF File", "https://schema.org/citation", ref_citation_entry, 0.90)

        # from bibtex
        for entry in client.get_parsed_bibtex():
            fields = entry.get("fields", {})
            if len(fields.keys()) > 0:
                state.metadata_collector.collect("BibTeX", "https://schema.org/citation", fields, 0.85)

        return state

class GitPlatformKeywordsExtractor(GitPlatformBaseExtractor):
    """schema:keywords"""

    extracts = {'https://schema.org/keywords'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_repository()
        if "topics" in result and result["topics"]:
            state.metadata_collector.collect("Platform API", "https://schema.org/keywords", result['topics'], 0.95)
        client = self.get_client(context, state)
        citations = client.get_parsed_citations()
        keywords = []
        for cff in citations:
            keywords.extend(cff.get('keywords', []))
        if len(keywords) > 0:
            state.metadata_collector.collect("CFF File", "https://schema.org/keywords", keywords, 0.90)
        
        # Query OpenAlex
        for doi in client.get_dois_from_parsed_citations().union(client.get_dois_from_readmes()):
            keywords = OpenAlexClient.get_or_create(context, state).get_keywords(doi)
            if len(keywords) > 0:
                state.metadata_collector.collect("OpenAlex", "https://schema.org/keywords", keywords, 0.95)
        return state

class GitPlatformReadmeExtractor(GitPlatformBaseExtractor):
    """codemeta:readme"""

    extracts = {'https://codemeta.github.io/terms/readme'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        readmes = client.get_readme_candidate_files()
        urls = set()
        for readme in readmes:
            readme_content = readme.get_content()
            if readme_content:
                urls.add(readme.get_html_url(client))
        if urls:
            state.metadata_collector.collect("Platform API", "https://codemeta.github.io/terms/readme", list(urls), 0.95)
        return state

class GitPlatformVersionControlSystemExtractor(GitPlatformBaseExtractor):
    """maSMP:versionControlSystem - hardcoded, since Platform is a Git-only forge"""

    extracts = {'https://discovery.biothings.io/ns/maSMP/versionControlSystem'}

    def extract(self, context, state):
        state.metadata_collector.collect("Constant", "https://discovery.biothings.io/ns/maSMP/versionControlSystem", {
            "@type": "VersionControlSystem",
            "name": "Git",
            "url": "https://git-scm.com/",
        }, 1.0)
        return state

class GitPlatformArchivedAtExtractor(GitPlatformBaseExtractor):
    """schema:archivedAt"""

    extracts = {'https://schema.org/archivedAt'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        zenodoUrls = set()
        for file in client.get_readme_candidate_files():
            readme_content = file.get_content()
            candidates = URLPatternMatcher.check_zenodo_badge(readme_content)
            for url in candidates:
                zenodoUrls.add(url)
        if zenodoUrls:
            state.metadata_collector.collect("README", "https://schema.org/archivedAt", list(zenodoUrls), 0.6)
        waybackUrl = WaybackClient.get_or_create(context, state).get_archive_url()
        if waybackUrl:
            state.metadata_collector.collect("Wayback API", "https://schema.org/archivedAt", [waybackUrl], 0.95)
        softwareHeritageUrl = SoftwareHeritageClient.get_or_create(context, state).get_archive_url()
        if softwareHeritageUrl:
            state.metadata_collector.collect("SoftwareHeritage API", "https://schema.org/archivedAt", [softwareHeritageUrl], 0.95)
        return state


class GitPlatformContributorsExtractor(GitPlatformBaseExtractor):

    extracts = {'https://schema.org/contributor'}

    def extract(self, context, state):
        # extract from API
        contributors = [person.to_jsonld_dict() for person in self.get_client(context, state).get_contributors()]
        state.metadata_collector.collect("Platform API", "https://schema.org/contributor", contributors, 0.95)
        client = self.get_client(context, state)

        # from CONTRIBUTORS.md (unstructured, lower confidence)
        client = self.get_client(context, state)
        md_contributors = []
        for file in client.get_contributors_candidate_files():
            content = file.get_content()
            if not content:
                continue
            for value in parse_contributor_names(content):
                if value.startswith("@"):
                    person = Person(account=OnlineAccount(username=value[1:], serviceHomepage="https://github.com"))
                else:
                    person = Person(name=value)
                md_contributors.append(person.to_jsonld_dict())
        if md_contributors:
            state.metadata_collector.collect("CONTRIBUTORS File", "https://schema.org/contributor", md_contributors, 0.7)

        return state

    
class GitPlatformSoftwareVersionExtractor(GitPlatformBaseExtractor):
    """schema:softwareVersion"""

    extracts = {'https://schema.org/softwareVersion', 'https://schema.org/version'}

    def extract(self, context, state):
        # Extract from tags
        result = self.get_client(context, state).get_tags()
        if result and len(result) > 0:
            tag_name = result[0].get("name")
            if tag_name:
                state.metadata_collector.collect("Platform API", "https://schema.org/softwareVersion", tag_name, 0.85)
                state.metadata_collector.collect("Platform API", "https://schema.org/version", tag_name, 0.85)
        client = self.get_client(context, state)
        # Extract from Cff
        citations = client.get_parsed_citations()
        for citation in citations:
            if 'version' in citation:
                state.metadata_collector.collect("CFF File", "https://schema.org/softwareVersion", citation['version'], 0.90)
                state.metadata_collector.collect("CFF File", "https://schema.org/version", citation['version'], 0.90)
        return state

class GitPlatformHasSourceCodeExtractor(GitPlatformBaseExtractor):
    """maSMP:hasSourceCode"""

    extracts = {'https://codemeta.github.io/terms/hasSourceCode'}

    def extract(self, context, state):
        c = self.get_client(context, state)
        hasSourceCodeUrl = c.get_html_url() 
        if hasSourceCodeUrl:
            state.metadata_collector.collect("Pattern", "https://codemeta.github.io/terms/hasSourceCode", hasSourceCodeUrl, 0.75)
        return state

class GitPlatformConditionsOfAccessExtractor(GitPlatformBaseExtractor):
    """schema:conditionsOfAccess - SoftwareApplication slot, mirrors license"""

    extracts = {'https://schema.org/conditionOfAccess'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_repository()
        license_info = result.get("license")
        if license_info and isinstance(license_info, dict):
            license_url = license_info.get("url") or license_info.get("key")
            if license_url:
                state.metadata_collector.collect("Platform API", "https://schema.org/conditionOfAccess", license_url, 0.95)
        return state

class GitPlatformIsAccessibleForFreeExtractor(GitPlatformBaseExtractor):
    """maSMP:isAccessibleForFree - SoftwareApplication slot, hardcoded to True"""

    extracts = {'https://schema.org/isAccessibleForFree', 'https://schema.org/conditionOfAccess'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        repo = client.get_repository()
        private = repo.get("private")
        if private == False:
            state.metadata_collector.collect("Platform API", "https://schema.org/isAccessibleForFree", True, 0.95)
            state.metadata_collector.collect("Platform API", "https://schema.org/conditionOfAccess", 'Public', 0.95)
        elif private == True:
            state.metadata_collector.collect("Platform API", "https://schema.org/isAccessibleForFree", False, 0.95)
            state.metadata_collector.collect("Platform API", "https://schema.org/conditionOfAccess", 'Private', 0.95)
        return state

class GitPlatformDateExtractor(GitPlatformBaseExtractor):
    """extracts creation, modification, and publication dates for a Platform repository,
    falling back to the latest tag's commit date if no releases exist"""

    extracts = {'https://schema.org/dateCreated', 'https://schema.org/datePublished', 'https://schema.org/dateModified'}

    def extract(self, context, state):
        
        client = self.get_client(context, state)

        # generic
        created = client.get_date_created()
        if created:
            state.metadata_collector.collect("Platform API", 'https://schema.org/dateCreated', iso_dt_to_str(created), 0.95)
        modified = client.get_date_modified()
        if modified:
            state.metadata_collector.collect("Platform API", 'https://schema.org/dateModified', iso_dt_to_str(modified), 0.95)
        published = client.get_date_published()
        if published:
            state.metadata_collector.collect("Platform API", 'https://schema.org/datePublished', iso_dt_to_str(published), 0.95)

        # from CFF
        citations = client.get_parsed_citations()
        for citation in citations:
            if 'date-released' in citation:
                state.metadata_collector.collect('CFF File', 'https://schema.org/datePublished', iso_dt_to_str(citation['date-released']), 0.85)
        return state

class GitPlatformIssueTrackerExtractor(GitPlatformBaseExtractor):
    """extracts the issue tracker URL for a Platform repository"""

    extracts = {'https://schema.org/issueTracker','https://codemeta.github.io/terms/issueTracker'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        repo = client.get_repository()
        if repo.get('has_issues', False) and 'html_url' in repo:
            issue_tracker_url = f"{repo['html_url']}/issues"
            state.metadata_collector.collect("Platform API", 'https://schema.org/issueTracker', issue_tracker_url, 0.95)
            state.metadata_collector.collect("Platform API", 'https://codemeta.github.io/terms/issueTracker', issue_tracker_url, 0.95)
        return state

class GitPlatformChangelogExtractor(GitPlatformBaseExtractor):
    """maSMP:changeLog - derived from the releases page and/or a CHANGELOG file in the repo root"""

    extracts = {'https://discovery.biothings.io/ns/maSMP/changeLog'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        
        files = client.get_changelog_candidate_files()
        for file in files:
            if (file.get_content() or "").lower().startswith('changelog'):
                changelog_url = file.get_html_url(client)
                if changelog_url:
                    state.metadata_collector.collect("Changelog File", 'https://discovery.biothings.io/ns/maSMP/changeLog', changelog_url, 0.85)
        return state

class GitPlatformSoftwareRequirementExtractor(GitPlatformBaseExtractor):
    
    extracts = {'https://schema.org/softwareRequirements'}

    def extract(self, context, state):
        client = self.get_client(context, state)
        files = client.list_contents()
        found = []
        for file in files:
            if file.name.lower() in dependency_files:
                download_url = client.get_file(file.path).get_html_url(client)
                if download_url:
                    found.append(download_url)
        if len(found) > 0:
            state.metadata_collector.collect("Platform API", 'https://schema.org/softwareRequirements', found, 0.95)
        return state

class GitPlatformLicenseCopyrightHolderExtractor(GitPlatformBaseExtractor):
    """extracts the copyright holder and year from the license file"""

    extracts = {"https://schema.org/copyrightHolder", "https://schema.org/copyrightYear"}

    def extract(self, context, state):
        
        pattern = re.compile(
            r'Copyright\s*(?:\(c\)|©|\(C\))?\s*'
            r'(\d{4}(?:\s*[-–,]\s*\d{4})*)\s*,?\s*'
            r'([^\n\r]+?)'
            r'(?:\s*\.?\s*(?:[Aa]ll [Rr]ights [Rr]eserved\.?)?)?$',
            re.MULTILINE | re.IGNORECASE
        )

        def extract_copyright_holder(text) -> tuple[str, str]:
            match = pattern.search(text)
            if match:
                year, holder = match.groups()
                return year, holder
            return None, None

        client = self.get_client(context, state)
        licenses = client.get_license_candidate_files()
        for license in licenses:
            year, holder = extract_copyright_holder(license.get_content() or "")
            if holder:
                state.metadata_collector.collect("License File", "https://schema.org/copyrightHolder", holder.strip(), 0.85)
            if year:
                year = int(year)
                state.metadata_collector.collect("License File", "https://schema.org/copyrightYear", year, 0.85)
                
        return state 
    
class GitPlatformStorageReqExtractor(GitPlatformBaseExtractor):
    """extracts the copyright holder and year from the license file"""

    extracts = {"https://schema.org/storageRequirements"}

    def extract(self, context, state):
        client = self.get_client(context, state)
        repo = client.get_repository()
        size = repo.get('size')
        if size:
            size = float(size)  # size in KB from GitHub API
            units = ['KB', 'MB', 'GB', 'TB', 'PB']
            divider = 1
            for unit in units:
                if size / divider < 1024:
                    break
                divider *= 1024
            sizeStr = f"{size / divider:.2f} {unit}"
            state.metadata_collector.collect('Platform API', "https://schema.org/storageRequirements", sizeStr, 0.95)
        return state

class GitPlatformDownloadUrlExtractor(GitPlatformBaseExtractor):
    """extracts the copyright holder and year from the license file"""

    extracts = {"https://schema.org/downloadUrl"}
    
    def extract(self, context, state):
        download_url = self.get_client(context, state).get_download_url()
        if download_url:
            state.metadata_collector.collect("Platform API", "https://schema.org/downloadUrl", download_url, 0.95)
        return state


class GitPlatformDeveloperDocumentationExtractor(GitPlatformBaseExtractor):
    """schema:developerDocumentation - looks for developer-facing documentation files such as
    HACKING.md, DEVELOPERS.md, CONTRIBUTING.md, etc."""

    extracts = {'https://codemeta.github.io/terms/developerDocumentation'}

    developer_doc_filenames = {
        'hacking.md',
        'hacking.rst',
        'hacking.txt',
        'hacking',
        'developers.md',
        'developers.rst',
        'developers.txt',
        'developers',
        'developer.md',
        'developer.rst',
        'developer.txt',
        'developer',
        'contributing.md',
        'contributing.rst',
        'contributing.txt',
        'contributing',
        'development.md',
        'development.rst',
        'development.txt',
        'development',
    }

    def extract(self, context, state):
        client = self.get_client(context, state)
        found = []
        for entry in client.list_contents():
            if entry.name.lower() in self.developer_doc_filenames and not entry.is_dir:
                doc_file = client.get_file(entry.path)
                html_url = doc_file.get_html_url(client)
                if html_url:
                    found.append(html_url)
        if len(found) > 0:
            state.metadata_collector.collect("Pattern", 'https://codemeta.github.io/terms/developerDocumentation', found, 0.85)
        return state

class GitPlatformDocumentationExtractor(GitPlatformBaseExtractor):
    """schema:documentation - looks for general user-facing documentation, either as
    dedicated files/directories in the repo (docs/, DOCUMENTATION.md, mkdocs.yml, ...)
    or as links to external documentation sites referenced in the README."""

    extracts = {'https://schema.org/documentation'}

    # top-level files that indicate documentation
    doc_filenames = {
        'documentation.md',
        'documentation.rst',
        'documentation.txt',
        'documentation',
        'docs.md',
        'docs.rst',
        'docs.txt',
        'usage.md',
        'usage.rst',
        'usage.txt',
        'guide.md',
        'guide.rst',
        'manual.md',
        'manual.rst',
    }

    # directories whose mere presence strongly suggests documentation
    doc_dirnames = {
        'docs',
        'doc',
        'documentation',
        'wiki',
        'guides',
        'manual',
    }

    # config files that indicate a documentation-generator/site is in use
    doc_tool_filenames = {
        'mkdocs.yml',
        'mkdocs.yaml',
        '_config.yml',       # Jekyll
        'book.toml',         # mdBook
        'docusaurus.config.js',
        'docusaurus.config.ts',
        '.readthedocs.yml',
        '.readthedocs.yaml',
        'vuepress.config.js',
        'nextra.config.js',
        'typedoc.json',
        'jsdoc.json',
        '.jsdoc.json',
    }

    # known documentation hosting domains, used to scan README links
    doc_url_pattern = re.compile(
        r'https?://[^\s\)"\']*'
        r'(?:readthedocs\.(?:io|org)'
        r'|\.github\.io'
        r'|docs\.rs'
        r'|pkg\.go\.dev'
        r'|godoc\.org'
        r'|gitbook\.(?:io|com)'
        r'|docusaurus\.io'
        r'|readme\.io'
        r'|/docs?(?:/|$|[\?#])'
        r'|/wiki(?:/|$|[\?#])'
        r'|/documentation(?:/|$|[\?#])'
        r')[^\s\)"\']*',
        re.IGNORECASE
    )

    def extract(self, context, state):
        client = self.get_client(context, state)
        found = set()

        # 1. Look for dedicated documentation files/directories at repo root
        for entry in client.list_contents():
            name_lower = entry.name.lower()
            if entry.is_dir and name_lower in self.doc_dirnames:
                dir_url = entry.get_html_url(client)
                if dir_url:
                    found.add(dir_url)
            elif not entry.is_dir and (
                name_lower in self.doc_filenames or name_lower in self.doc_tool_filenames
            ):
                doc_file = client.get_file(entry.path)
                html_url = doc_file.get_html_url(client)
                if html_url:
                    found.add(html_url)

        if found:
            state.metadata_collector.collect(
                "Pattern", "https://schema.org/documentation", list(found), 0.85
            )

        # 2. Scan README(s) for links to external documentation sites
        readme_doc_urls = set()
        for readme in client.get_readme_candidate_files():
            content = readme.get_content()
            if not content:
                continue
            for match in self.doc_url_pattern.finditer(content):
                url = match.group(0).rstrip('.,;:)')
                readme_doc_urls.add(url)

        if readme_doc_urls:
            state.metadata_collector.collect(
                "README", "https://schema.org/documentation", list(readme_doc_urls), 0.7
            )

        # 3. Check CFF for an explicit documentation/url-like field, if present
        citations = client.get_parsed_citations()
        for cff in citations:
            # non-standard, but sometimes present in the wild
            doc_url = cff.get('documentation') or cff.get('docs-url')
            if doc_url:
                state.metadata_collector.collect(
                    "CFF File", "https://schema.org/documentation", doc_url, 0.75
                )

        return state