"""Codeberg extractor plugins for populating schema.org / codemeta / maSMP
metadata fields from a repository's Codeberg API data, CITATION.cff files,
README files, and license files."""

from app.layer_3.plugins.codeberg.codeberg_base_extractor import CodebergBaseExtractor
from app.layer_3.plugins.shared.json_files.codemeta_json import GitPlatformCodemetaExtractor
from app.layer_3.plugins.shared.json_files.connoss_json import GitPlatformConnossExtractor
from app.layer_3.plugins.shared.collection import (GitPlatformDescriptionExtractor
,GitPlatformNameExtractor
,GitPlatformUrlExtractor
,GitPlatformCodeRepositoryExtractor
,GitPlatformProgrammingLanguageExtractor
,GitPlatformAuthorExtractor
,GitPlatformLicenseExtractor
,GitPlatformIdentifierExtractor
,GitPlatformCitationExtractor
,GitPlatformKeywordsExtractor
,GitPlatformReadmeExtractor
,GitPlatformVersionControlSystemExtractor
,GitPlatformArchivedAtExtractor
,GitPlatformContributorsExtractor
,GitPlatformSoftwareVersionExtractor
,GitPlatformHasSourceCodeExtractor
,GitPlatformConditionsOfAccessExtractor
,GitPlatformIsAccessibleForFreeExtractor
,GitPlatformDateExtractor
,GitPlatformIssueTrackerExtractor
,GitPlatformChangelogExtractor
,GitPlatformSoftwareRequirementExtractor
,GitPlatformLicenseCopyrightHolderExtractor
,GitPlatformStorageReqExtractor
,GitPlatformDeveloperDocumentationExtractor
,GitPlatformDocumentationExtractor
,GitPlatformDownloadUrlExtractor)

class CodebergNameExtractor(GitPlatformNameExtractor, CodebergBaseExtractor):
    """schema:name"""
    name = "codeberg.name_extractor"

class CodebergDescriptionExtractor(GitPlatformDescriptionExtractor, CodebergBaseExtractor):
    name = "codeberg.description_extractor"

class CodebergUrlExtractor(GitPlatformUrlExtractor, CodebergBaseExtractor):
    """schema:url"""
    name = "codeberg.url_extractor"

class CodebergCodeRepositoryExtractor(GitPlatformCodeRepositoryExtractor, CodebergBaseExtractor):
    """schema:codeRepository"""
    name = "codeberg.code_repository_extractor"

class CodebergProgrammingLanguageExtractor(GitPlatformProgrammingLanguageExtractor, CodebergBaseExtractor):
    """schema:programmingLanguage"""
    name = "codeberg.programming_language_extractor"

class CodebergAuthorExtractor(GitPlatformAuthorExtractor, CodebergBaseExtractor):
    """schema:author"""
    name = "codeberg.author_extractor"

class CodebergLicenseExtractor(GitPlatformLicenseExtractor, CodebergBaseExtractor):
    """schema:license"""
    name = "codeberg.license_extractor"

class CodebergIdentifierExtractor(GitPlatformIdentifierExtractor, CodebergBaseExtractor):
    """schema:identifier"""
    name = "codeberg.identifier_extractor"

class CodebergCitationExtractor(GitPlatformCitationExtractor, CodebergBaseExtractor):
    """schema:citation"""
    name = "codeberg.citation_extractor"

class CodebergKeywordsExtractor(GitPlatformKeywordsExtractor, CodebergBaseExtractor):
    """schema:keywords"""
    name = "codeberg.keywords_extractor"

class CodebergReadmeExtractor(GitPlatformReadmeExtractor, CodebergBaseExtractor):
    """codemeta:readme"""
    name = "codeberg.readme_extractor"

class CodebergVersionControlSystemExtractor(GitPlatformVersionControlSystemExtractor, CodebergBaseExtractor):
    """maSMP:versionControlSystem - hardcoded, since Codeberg is a Git-only forge"""
    name = "codeberg.version_control_system_extractor"

class CodebergArchivedAtExtractor(GitPlatformArchivedAtExtractor, CodebergBaseExtractor):
    """schema:archivedAt"""
    name = "codeberg.archived_at_extractor"

class CodebergContributorsExtractor(GitPlatformContributorsExtractor, CodebergBaseExtractor):
    name = "codeberg.contributors_extractor"

class CodebergReleaseNotesExtractor(CodebergBaseExtractor):
    """schema:releaseNotes"""
    name = "codeberg.release_notes_extractor"

    extracts = {'https://schema.org/releaseNotes','https://codemeta.github.io/terms/releaseNotes'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_releases()
        if isinstance(result, list) and len(result) > 0:
            url = result[0].get("html_url")
            if url:
                state.metadata_collector.collect("Platform API", "https://schema.org/releaseNotes", url, 0.95)
                state.metadata_collector.collect("Platform API", 'https://codemeta.github.io/terms/releaseNotes', url, 0.95)
        return state

class CodebergSoftwareVersionExtractor(GitPlatformSoftwareVersionExtractor, CodebergBaseExtractor):
    """schema:softwareVersion"""
    name = "codeberg.software_version_extractor"

    def extract(self, context, state):
        # Extract from releases
        result = self.get_client(context, state).get_releases()
        if result and len(result) > 0:
            version = result[0].get("tag_name")
            if version:
                state.metadata_collector.collect("Platform API", 'https://schema.org/softwareVersion', version, 0.95)
                state.metadata_collector.collect("Platform API", 'https://schema.org/version', version, 0.95)
        # Extract from tags if no releases found
        if not result or len(result) == 0:
            result = self.get_client(context, state).get_tags()
            if result and len(result) > 0:
                version = result[0].get("name")
                if version:
                    state.metadata_collector.collect("Platform API", 'https://schema.org/softwareVersion', version, 0.95)
                    state.metadata_collector.collect("Platform API", 'https://schema.org/version', version, 0.95)
        return super().extract(context, state)

class CodebergHasSourceCodeExtractor(GitPlatformHasSourceCodeExtractor, CodebergBaseExtractor):
    """maSMP:hasSourceCode"""
    name = "codeberg.has_source_code_extractor"

class CodebergConditionsOfAccessExtractor(GitPlatformConditionsOfAccessExtractor, CodebergBaseExtractor):
    """schema:conditionsOfAccess - SoftwareApplication slot, mirrors license"""
    name = "codeberg.conditions_of_access_extractor"

class CodebergIsAccessibleForFreeExtractor(GitPlatformIsAccessibleForFreeExtractor, CodebergBaseExtractor):
    """maSMP:isAccessibleForFree - SoftwareApplication slot, hardcoded to True"""
    name = "codeberg.is_accessible_for_free_extractor"

class CodebergDateExtractor(GitPlatformDateExtractor, CodebergBaseExtractor):
    """extracts creation, modification, and publication dates for a Codeberg repository,
    falling back to the latest tag's commit date if no releases exist"""
    name = "codeberg.date_extractor"

class CodebergIssueTrackerExtractor(GitPlatformIssueTrackerExtractor, CodebergBaseExtractor):
    """extracts the issue tracker URL for a Codeberg repository"""
    name = "codeberg.issue_tracker_extractor"

class CodebergChangelogExtractor(GitPlatformChangelogExtractor, CodebergBaseExtractor):
    """maSMP:changeLog - derived from the releases page and/or a CHANGELOG file in the repo root"""
    name = "codeberg.changelog_extractor"

    def extract(self, context, state):
        client = self.get_client(context, state)
        repo = client.get_repository()
        if repo.get('has_releases', False):
            if 'html_url' in repo:
                changelog_url = f"{repo['html_url']}/releases"
                state.metadata_collector.collect("Pattern", 'https://discovery.biothings.io/ns/maSMP/changeLog', changelog_url, 0.75)
        
        return super().extract(context, state)

class CodebergSoftwareRequirementExtractor(GitPlatformSoftwareRequirementExtractor, CodebergBaseExtractor):

    name = "codeberg.software_requirements_extractor"

class CodebergLicenseCopyrightHolderExtractor(GitPlatformLicenseCopyrightHolderExtractor, CodebergBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "codeberg.extract_copyright_year_and_holder"
    
class CodebergStorageReqExtractor(GitPlatformStorageReqExtractor, CodebergBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "codeberg.storage_requirement_extractor"

class CodebergDownloadUrlExtractor(GitPlatformDownloadUrlExtractor, CodebergBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "codeberg.codeberg_download_url_extractor"

class CodebergDeveloperDocumentationExtractor(GitPlatformDeveloperDocumentationExtractor, CodebergBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "codeberg.developer_documentation_extractor"

class CodebergDocumentationExtractor(GitPlatformDocumentationExtractor, CodebergBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "codeberg.documentation_extractor"

class CodebergCodemetaExtractor(GitPlatformCodemetaExtractor, CodebergBaseExtractor):
    """extracts metadata from a repository's codemeta.json file"""
    name = "codeberg.codemeta_extractor"

class CodebergConnossExtractor(GitPlatformConnossExtractor, CodebergBaseExtractor):
    """extracts metadata from a repository's connoss.json file"""
    name = "codeberg.connoss_extractor"