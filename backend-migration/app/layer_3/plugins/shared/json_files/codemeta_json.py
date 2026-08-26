import json
import datetime
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor


class GitPlatformCodemetaExtractor(GitPlatformBaseExtractor):
    """Extracts schema.org/codemeta properties from a codemeta.json file
    found in the repository root, if present."""

    extracts = {
        'https://schema.org/name',
        'https://schema.org/description',
        'https://schema.org/url',
        'https://schema.org/codeRepository',
        'https://codemeta.github.io/terms/codeRepository',
        'https://schema.org/programmingLanguage',
        'https://schema.org/author',
        'https://schema.org/license',
        'https://schema.org/identifier',
        'https://schema.org/citation',
        'https://schema.org/keywords',
        'https://codemeta.github.io/terms/readme',
        'https://schema.org/softwareVersion',
        'https://schema.org/version',
        'https://codemeta.github.io/terms/hasSourceCode',
        'https://schema.org/issueTracker',
        'https://codemeta.github.io/terms/issueTracker',
        'https://schema.org/dateCreated',
        'https://schema.org/dateModified',
        'https://schema.org/datePublished',
        'https://schema.org/downloadUrl',
        'https://schema.org/softwareRequirements',
        'https://schema.org/copyrightHolder',
        'https://schema.org/copyrightYear',
        'https://schema.org/contributor',
    }

    SOURCE = "codemeta.json"
    CONF = 0.99  # codemeta.json is author-curated, structured, high-trust metadata

    def _get_codemeta(self, client):
        """Fetches and parses codemeta.json from repo root, if it exists."""
        try:
            files = client.list_contents()
        except Exception:
            return None

        for file in files:
            if file.name.lower() == "codemeta.json":
                try:
                    file_obj = client.get_file(file.path)
                    content = file_obj.get_content()
                    if content:
                        return json.loads(content)
                except (json.JSONDecodeError, Exception):
                    return None
        return None

    @staticmethod
    def _iso_dt_to_str(iso_dt):
        try:
            return str(datetime.datetime.fromisoformat(str(iso_dt)).date())
        except Exception:
            return str(iso_dt)

    @staticmethod
    def _normalize_person(person_data):
        """Converts a codemeta person object (schema.org Person) into our
        internal representation."""
        if not isinstance(person_data, dict):
            return None
        person = {"@type": "Person"}
        if "givenName" in person_data:
            person["givenName"] = person_data["givenName"]
        if "familyName" in person_data:
            person["familyName"] = person_data["familyName"]
        if "name" in person_data and "givenName" not in person_data and "familyName" not in person_data:
            person["name"] = person_data["name"]
        if "@id" in person_data:
            person["@id"] = person_data["@id"]
        elif "id" in person_data:
            person["@id"] = person_data["id"]
        return person if len(person) > 1 else None

    def extract(self, context, state):
        client = self.get_client(context, state)
        codemeta = self._get_codemeta(client)
        if not codemeta:
            return state

        collector = state.metadata_collector

        # schema:name
        if codemeta.get("name"):
            collector.collect(self.SOURCE, "https://schema.org/name", codemeta["name"], self.CONF)

        # schema:description
        if codemeta.get("description"):
            collector.collect(self.SOURCE, "https://schema.org/description", codemeta["description"], self.CONF)

        # schema:url
        if codemeta.get("url"):
            collector.collect(self.SOURCE, "https://schema.org/url", codemeta["url"], self.CONF)

        # schema:codeRepository
        code_repo = codemeta.get("codeRepository")
        if code_repo:
            collector.collect(self.SOURCE, "https://schema.org/codeRepository", code_repo, self.CONF)
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/codeRepository", code_repo, self.CONF)

        # schema:programmingLanguage
        prog_lang = codemeta.get("programmingLanguage")
        if prog_lang:
            if isinstance(prog_lang, list):
                languages = []
                for lang in prog_lang:
                    if isinstance(lang, dict) and lang.get("name"):
                        languages.append(lang["name"])
                    elif isinstance(lang, str):
                        languages.append(lang)
                if languages:
                    collector.collect(self.SOURCE, "https://schema.org/programmingLanguage", languages, self.CONF)
            elif isinstance(prog_lang, dict) and prog_lang.get("name"):
                collector.collect(self.SOURCE, "https://schema.org/programmingLanguage", [prog_lang["name"]], self.CONF)
            elif isinstance(prog_lang, str):
                collector.collect(self.SOURCE, "https://schema.org/programmingLanguage", [prog_lang], self.CONF)

        # schema:author
        author_field = codemeta.get("author")
        if author_field:
            authors_raw = author_field if isinstance(author_field, list) else [author_field]
            authors = []
            for author_data in authors_raw:
                person = self._normalize_person(author_data)
                if person:
                    authors.append(person)
            if authors:
                collector.collect(self.SOURCE, "https://schema.org/author", authors, self.CONF)

        # schema:contributor
        contributor_field = codemeta.get("contributor")
        if contributor_field:
            contributors_raw = contributor_field if isinstance(contributor_field, list) else [contributor_field]
            contributors = []
            for contrib_data in contributors_raw:
                person = self._normalize_person(contrib_data)
                if person:
                    contributors.append(person)
            if contributors:
                collector.collect(self.SOURCE, "https://schema.org/contributor", contributors, self.CONF)

        # schema:license
        license_field = codemeta.get("license")
        if license_field:
            license_entries = license_field if isinstance(license_field, list) else [license_field]
            for license_entry in license_entries:
                if isinstance(license_entry, str):
                    # could be an SPDX URL or plain string
                    if license_entry.startswith("http"):
                        license_object = {
                            '@type': 'CreativeWork',
                            '@context': 'https://schema.org',
                            'url': license_entry,
                        }
                    else:
                        license_object = {
                            '@type': 'CreativeWork',
                            '@context': 'https://schema.org',
                            'name': license_entry,
                        }
                    collector.collect(self.SOURCE, "https://schema.org/license", license_object, self.CONF)
                elif isinstance(license_entry, dict):
                    license_object = {
                        '@type': 'CreativeWork',
                        '@context': 'https://schema.org',
                    }
                    if license_entry.get("name"):
                        license_object["name"] = license_entry["name"]
                    if license_entry.get("url") or license_entry.get("id"):
                        license_object["url"] = license_entry.get("url") or license_entry.get("id")
                    collector.collect(self.SOURCE, "https://schema.org/license", license_object, self.CONF)

        # schema:identifier
        identifier_field = codemeta.get("identifier")
        if identifier_field:
            identifiers = identifier_field if isinstance(identifier_field, list) else [identifier_field]
            resolved_identifiers = []
            for ident in identifiers:
                if isinstance(ident, str):
                    resolved_identifiers.append(ident)
                elif isinstance(ident, dict) and ident.get("value"):
                    resolved_identifiers.append(ident["value"])
            if resolved_identifiers:
                collector.collect(self.SOURCE, "https://schema.org/identifier", resolved_identifiers, self.CONF)

        # schema:citation (referencePublication typically maps here in codemeta)
        citation_field = codemeta.get("citation") or codemeta.get("referencePublication")
        if citation_field:
            citations = citation_field if isinstance(citation_field, list) else [citation_field]
            for citation in citations:
                collector.collect(self.SOURCE, "https://schema.org/citation", citation, self.CONF)

        # schema:keywords
        keywords_field = codemeta.get("keywords")
        if keywords_field:
            keywords = keywords_field if isinstance(keywords_field, list) else [keywords_field]
            collector.collect(self.SOURCE, "https://schema.org/keywords", keywords, self.CONF)

        # codemeta:readme
        readme_field = codemeta.get("readme")
        if readme_field:
            readmes = readme_field if isinstance(readme_field, list) else [readme_field]
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/readme", readmes, self.CONF)

        # schema:softwareVersion / schema:version
        version_field = codemeta.get("version")
        if version_field:
            collector.collect(self.SOURCE, "https://schema.org/softwareVersion", version_field, self.CONF)
            collector.collect(self.SOURCE, "https://schema.org/version", version_field, self.CONF)

        # codemeta:hasSourceCode
        has_source_code = codemeta.get("hasSourceCode") or codemeta.get("codeRepository")
        if has_source_code:
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/hasSourceCode", has_source_code, self.CONF)

        # schema:issueTracker
        issue_tracker = codemeta.get("issueTracker")
        if issue_tracker:
            collector.collect(self.SOURCE, "https://schema.org/issueTracker", issue_tracker, self.CONF)
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/issueTracker", issue_tracker, self.CONF)

        # dates
        date_created = codemeta.get("dateCreated")
        if date_created:
            collector.collect(self.SOURCE, "https://schema.org/dateCreated", self._iso_dt_to_str(date_created), self.CONF)

        date_modified = codemeta.get("dateModified")
        if date_modified:
            collector.collect(self.SOURCE, "https://schema.org/dateModified", self._iso_dt_to_str(date_modified), self.CONF)

        date_published = codemeta.get("datePublished")
        if date_published:
            collector.collect(self.SOURCE, "https://schema.org/datePublished", self._iso_dt_to_str(date_published), self.CONF)

        # schema:downloadUrl
        download_url = codemeta.get("downloadUrl")
        if download_url:
            collector.collect(self.SOURCE, "https://schema.org/downloadUrl", download_url, self.CONF)

        # schema:softwareRequirements
        software_requirements = codemeta.get("softwareRequirements")
        if software_requirements:
            requirements = software_requirements if isinstance(software_requirements, list) else [software_requirements]
            resolved_requirements = []
            for req in requirements:
                if isinstance(req, str):
                    resolved_requirements.append(req)
                elif isinstance(req, dict) and req.get("name"):
                    resolved_requirements.append(req["name"])
            if resolved_requirements:
                collector.collect(self.SOURCE, "https://schema.org/softwareRequirements", resolved_requirements, self.CONF)

        # schema:copyrightHolder / schema:copyrightYear
        copyright_holder = codemeta.get("copyrightHolder")
        if copyright_holder:
            holder_name = None
            if isinstance(copyright_holder, dict):
                holder_name = copyright_holder.get("name")
            elif isinstance(copyright_holder, str):
                holder_name = copyright_holder
            if holder_name:
                collector.collect(self.SOURCE, "https://schema.org/copyrightHolder", holder_name, self.CONF)

        copyright_year = codemeta.get("copyrightYear")
        if copyright_year:
            try:
                collector.collect(self.SOURCE, "https://schema.org/copyrightYear", int(copyright_year), self.CONF)
            except (ValueError, TypeError):
                pass

        return state