import json
import datetime
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor

class GitPlatformConnossExtractor(GitPlatformBaseExtractor):
    """Extracts all properties from a connoss.json file
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
        # newly added
        'https://schema.org/codeSampleType',
        'https://schema.org/runtimePlatform',
        'https://schema.org/targetProduct',
        'https://schema.org/applicationCategory',
        'https://schema.org/applicationSubCategory',
        'https://schema.org/applicationSuite',
        'https://schema.org/availableOnDevice',
        'https://schema.org/countriesNotSupported',
        'https://schema.org/countriesSupported',
        'https://schema.org/featureList',
        'https://schema.org/fileSize',
        'https://schema.org/installUrl',
        'https://schema.org/memoryRequirements',
        'https://schema.org/operatingSystem',
        'https://schema.org/permissions',
        'https://schema.org/processorRequirements',
        'https://schema.org/screenshot',
        'https://schema.org/softwareAddOn',
        'https://schema.org/softwareHelp',
        'https://schema.org/supportingData',
        'https://schema.org/encodingFormat',
        'https://schema.org/funder',
        'https://schema.org/hasPart',
        'https://schema.org/isPartOf',
        'https://schema.org/publisher',
        'https://schema.org/review',
        'https://schema.org/sponsor',
        'https://schema.org/sameAs',
        'https://schema.org/relatedLink',
        'https://codemeta.github.io/terms/buildInstructions',
        'https://codemeta.github.io/terms/continuousIntegration',
        'https://codemeta.github.io/terms/developmentStatus',
        'https://codemeta.github.io/terms/embargoEndDate',
        'https://codemeta.github.io/terms/isSourceCodeOf',
        'https://schema.org/relatedSoftware',
        'https://schema.org/contactPoint',
        'https://schema.org/creditText',
        'https://schema.org/intendedUse',
        'https://schema.org/applicationDomain',
        'https://schema.org/legalConsiderations',
        'https://schema.org/ethicalSocialConsiderations',
        'https://schema.org/conditionsOfAccess',
        'https://codemeta.github.io/terms/userDocumentation',
        'https://schema.org/softwareInterface',
        'https://schema.org/testedWith',
        'https://schema.org/implementsSpecification',
        'https://schema.org/softwareContainer',
        'https://schema.org/input',
        'https://schema.org/output',
        'https://schema.org/partOfCommunity',
        'https://schema.org/latestRelease',
        'https://codemeta.github.io/terms/latestReleaseVersion',
    }

    SOURCE = "connoss.json"
    CONF = 0.99  # connoss.json is author-curated, structured, high-trust metadata

    def _get_connoss(self, client):
        """Fetches and parses connoss.json from repo root, if it exists."""
        try:
            files = client.list_contents()
        except Exception:
            return None

        for file in files:
            if file.name.lower() == "connoss.json":
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
        """Converts a connoss person object (schema.org Person) into our
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

    @staticmethod
    def _normalize_org(org_data):
        """Converts a connoss organization/person-like object into our
        internal representation. Used for funder, publisher, sponsor, etc."""
        if isinstance(org_data, str):
            return {"@type": "Organization", "name": org_data}
        if not isinstance(org_data, dict):
            return None
        org_type = org_data.get("@type") or org_data.get("type") or "Organization"
        org = {"@type": org_type}
        if "name" in org_data:
            org["name"] = org_data["name"]
        if "@id" in org_data:
            org["@id"] = org_data["@id"]
        elif "id" in org_data:
            org["@id"] = org_data["id"]
        if "url" in org_data:
            org["url"] = org_data["url"]
        return org if len(org) > 1 else None

    @staticmethod
    def _as_list(value):
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    @staticmethod
    def _string_list(value):
        """Extracts plain strings from a value that might be a string,
        a list of strings, or a list of dicts with a 'name' key."""
        result = []
        for item in GitPlatformConnossExtractor._as_list(value):
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and item.get("name"):
                result.append(item["name"])
        return result

    def _collect_simple(self, collector, connoss, key, predicate):
        """Collects a value as-is (string, number, or dict) if present."""
        value = connoss.get(key)
        if value is not None and value != "" and value != []:
            collector.collect(self.SOURCE, predicate, value, self.CONF)

    def _collect_string_list(self, collector, connoss, key, predicate):
        """Collects a value normalized into a list of strings."""
        value = connoss.get(key)
        if not value:
            return
        strings = self._string_list(value)
        if strings:
            collector.collect(self.SOURCE, predicate, strings, self.CONF)

    def _collect_entity_list(self, collector, connoss, key, predicate, normalizer):
        """Collects a value normalized into a list of entities (dicts)."""
        value = connoss.get(key)
        if not value:
            return
        entities = []
        for item in self._as_list(value):
            normalized = normalizer(item)
            if normalized:
                entities.append(normalized)
        if entities:
            collector.collect(self.SOURCE, predicate, entities, self.CONF)

    def extract(self, context, state):
        client = self.get_client(context, state)
        connoss = self._get_connoss(client)
        if not connoss:
            return state

        collector = state.metadata_collector

        # schema:name
        if connoss.get("name"):
            collector.collect(self.SOURCE, "https://schema.org/name", connoss["name"], self.CONF)

        # schema:description
        if connoss.get("description"):
            collector.collect(self.SOURCE, "https://schema.org/description", connoss["description"], self.CONF)

        # schema:url
        if connoss.get("url"):
            collector.collect(self.SOURCE, "https://schema.org/url", connoss["url"], self.CONF)

        # schema:codeRepository
        code_repo = connoss.get("codeRepository")
        if code_repo:
            collector.collect(self.SOURCE, "https://schema.org/codeRepository", code_repo, self.CONF)
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/codeRepository", code_repo, self.CONF)

        # schema:programmingLanguage
        prog_lang = connoss.get("programmingLanguage")
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
        author_field = connoss.get("author")
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
        contributor_field = connoss.get("contributor")
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
        license_field = connoss.get("license")
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
        identifier_field = connoss.get("identifier")
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

        # schema:citation (referencePublication typically maps here in connoss)
        citation_field = connoss.get("citation") or connoss.get("referencePublication")
        if citation_field:
            citations = citation_field if isinstance(citation_field, list) else [citation_field]
            for citation in citations:
                collector.collect(self.SOURCE, "https://schema.org/citation", citation, self.CONF)

        # schema:keywords
        keywords_field = connoss.get("keywords")
        if keywords_field:
            keywords = keywords_field if isinstance(keywords_field, list) else [keywords_field]
            collector.collect(self.SOURCE, "https://schema.org/keywords", keywords, self.CONF)

        # connoss:readme
        readme_field = connoss.get("readme")
        if readme_field:
            readmes = readme_field if isinstance(readme_field, list) else [readme_field]
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/readme", readmes, self.CONF)

        # schema:softwareVersion / schema:version
        version_field = connoss.get("softwareVersion") or connoss.get("version")
        if version_field:
            collector.collect(self.SOURCE, "https://schema.org/softwareVersion", version_field, self.CONF)
            collector.collect(self.SOURCE, "https://schema.org/version", version_field, self.CONF)

        # connoss:hasSourceCode
        has_source_code = connoss.get("hasSourceCode") or connoss.get("codeRepository")
        if has_source_code:
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/hasSourceCode", has_source_code, self.CONF)

        # schema:issueTracker
        issue_tracker = connoss.get("issueTracker")
        if issue_tracker:
            collector.collect(self.SOURCE, "https://schema.org/issueTracker", issue_tracker, self.CONF)
            collector.collect(self.SOURCE, "https://codemeta.github.io/terms/issueTracker", issue_tracker, self.CONF)

        # dates
        date_created = connoss.get("dateCreated")
        if date_created:
            collector.collect(self.SOURCE, "https://schema.org/dateCreated", self._iso_dt_to_str(date_created), self.CONF)

        date_modified = connoss.get("dateModified")
        if date_modified:
            collector.collect(self.SOURCE, "https://schema.org/dateModified", self._iso_dt_to_str(date_modified), self.CONF)

        date_published = connoss.get("datePublished")
        if date_published:
            collector.collect(self.SOURCE, "https://schema.org/datePublished", self._iso_dt_to_str(date_published), self.CONF)

        # schema:downloadUrl
        download_url = connoss.get("downloadUrl")
        if download_url:
            collector.collect(self.SOURCE, "https://schema.org/downloadUrl", download_url, self.CONF)

        # schema:softwareRequirements
        software_requirements = connoss.get("softwareRequirements")
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
        copyright_holder = connoss.get("copyrightHolder")
        if copyright_holder:
            holder_name = None
            if isinstance(copyright_holder, dict):
                holder_name = copyright_holder.get("name")
            elif isinstance(copyright_holder, str):
                holder_name = copyright_holder
            if holder_name:
                collector.collect(self.SOURCE, "https://schema.org/copyrightHolder", holder_name, self.CONF)

        copyright_year = connoss.get("copyrightYear")
        if copyright_year:
            try:
                collector.collect(self.SOURCE, "https://schema.org/copyrightYear", int(copyright_year), self.CONF)
            except (ValueError, TypeError):
                pass

        # ------------------------------------------------------------------
        # Newly added properties below
        # ------------------------------------------------------------------

        # Simple scalar/passthrough values
        self._collect_simple(collector, connoss, "codeSampleType", "https://schema.org/codeSampleType")
        self._collect_simple(collector, connoss, "fileSize", "https://schema.org/fileSize")
        self._collect_simple(collector, connoss, "installUrl", "https://schema.org/installUrl")
        self._collect_simple(collector, connoss, "applicationCategory", "https://schema.org/applicationCategory")
        self._collect_simple(collector, connoss, "applicationSubCategory", "https://schema.org/applicationSubCategory")
        self._collect_simple(collector, connoss, "applicationSuite", "https://schema.org/applicationSuite")
        self._collect_simple(collector, connoss, "creditText", "https://schema.org/creditText")
        self._collect_simple(collector, connoss, "intendedUse", "https://schema.org/intendedUse")
        self._collect_simple(collector, connoss, "applicationDomain", "https://schema.org/applicationDomain")
        self._collect_simple(collector, connoss, "legalConsiderations", "https://schema.org/legalConsiderations")
        self._collect_simple(collector, connoss, "ethicalSocialConsiderations", "https://schema.org/ethicalSocialConsiderations")
        self._collect_simple(collector, connoss, "conditionsOfAccess", "https://schema.org/conditionsOfAccess")
        self._collect_simple(collector, connoss, "userDocumentation", "https://codemeta.github.io/terms/userDocumentation")
        self._collect_simple(collector, connoss, "buildInstructions", "https://codemeta.github.io/terms/buildInstructions")
        self._collect_simple(collector, connoss, "continuousIntegration", "https://codemeta.github.io/terms/continuousIntegration")
        self._collect_simple(collector, connoss, "developmentStatus", "https://codemeta.github.io/terms/developmentStatus")
        self._collect_simple(collector, connoss, "embargoEndDate", "https://codemeta.github.io/terms/embargoEndDate")
        self._collect_simple(collector, connoss, "isSourceCodeOf", "https://codemeta.github.io/terms/isSourceCodeOf")
        self._collect_simple(collector, connoss, "softwareInterface", "https://schema.org/softwareInterface")
        self._collect_simple(collector, connoss, "implementsSpecification", "https://schema.org/implementsSpecification")
        self._collect_simple(collector, connoss, "softwareContainer", "https://schema.org/softwareContainer")
        self._collect_simple(collector, connoss, "input", "https://schema.org/input")
        self._collect_simple(collector, connoss, "output", "https://schema.org/output")
        self._collect_simple(collector, connoss, "partOfCommunity", "https://schema.org/partOfCommunity")
        self._collect_simple(collector, connoss, "latestRelease", "https://schema.org/latestRelease")
        self._collect_simple(collector, connoss, "latestReleaseVersion", "https://codemeta.github.io/terms/latestReleaseVersion")
        self._collect_simple(collector, connoss, "review", "https://schema.org/review")
        self._collect_simple(collector, connoss, "hasPart", "https://schema.org/hasPart")
        self._collect_simple(collector, connoss, "isPartOf", "https://schema.org/isPartOf")
        self._collect_simple(collector, connoss, "contactPoint", "https://schema.org/contactPoint")
        self._collect_simple(collector, connoss, "encodingFormat", "https://schema.org/encodingFormat")
        self._collect_simple(collector, connoss, "memoryRequirements", "https://schema.org/memoryRequirements")
        self._collect_simple(collector, connoss, "processorRequirements", "https://schema.org/processorRequirements")

        # Lists of strings (may be provided as string, list of strings, or list of dicts with 'name')
        self._collect_string_list(collector, connoss, "runtimePlatform", "https://schema.org/runtimePlatform")
        self._collect_string_list(collector, connoss, "targetProduct", "https://schema.org/targetProduct")
        self._collect_string_list(collector, connoss, "availableOnDevice", "https://schema.org/availableOnDevice")
        self._collect_string_list(collector, connoss, "countriesNotSupported", "https://schema.org/countriesNotSupported")
        self._collect_string_list(collector, connoss, "countriesSupported", "https://schema.org/countriesSupported")
        self._collect_string_list(collector, connoss, "featureList", "https://schema.org/featureList")
        self._collect_string_list(collector, connoss, "operatingSystem", "https://schema.org/operatingSystem")
        self._collect_string_list(collector, connoss, "permissions", "https://schema.org/permissions")
        self._collect_string_list(collector, connoss, "screenshot", "https://schema.org/screenshot")
        self._collect_string_list(collector, connoss, "softwareAddOn", "https://schema.org/softwareAddOn")
        self._collect_string_list(collector, connoss, "softwareHelp", "https://schema.org/softwareHelp")
        self._collect_string_list(collector, connoss, "supportingData", "https://schema.org/supportingData")
        self._collect_string_list(collector, connoss, "sameAs", "https://schema.org/sameAs")
        self._collect_string_list(collector, connoss, "relatedLink", "https://schema.org/relatedLink")
        self._collect_string_list(collector, connoss, "relatedSoftware", "https://schema.org/relatedSoftware")
        self._collect_string_list(collector, connoss, "testedWith", "https://schema.org/testedWith")

        # Entities (organizations/persons): funder, publisher, sponsor
        self._collect_entity_list(collector, connoss, "funder", "https://schema.org/funder", self._normalize_org)
        self._collect_entity_list(collector, connoss, "publisher", "https://schema.org/publisher", self._normalize_org)
        self._collect_entity_list(collector, connoss, "sponsor", "https://schema.org/sponsor", self._normalize_org)

        return state