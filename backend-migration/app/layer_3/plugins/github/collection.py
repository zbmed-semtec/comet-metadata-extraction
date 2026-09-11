"""GitHub extractor plugins for populating schema.org / codemeta / maSMP
metadata fields from a repository's GitHub API data, CITATION.cff files,
README files, and license files."""

from app.layer_3.plugins.github.github_base_extractor import GitHubBaseExtractor
from app.layer_3.plugins.shared.json_files.connoss_json import GitPlatformConnossExtractor
from app.layer_3.plugins.shared.json_files.codemeta_json import GitPlatformCodemetaExtractor
from app.layer_3.plugins.shared.collection import (
    GitPlatformDescriptionExtractor
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
    ,GitPlatformDownloadUrlExtractor
    ,GitPlatformDeveloperDocumentationExtractor
    ,GitPlatformDocumentationExtractor
    )

class GitHubNameExtractor(GitPlatformNameExtractor, GitHubBaseExtractor):
    """schema:name"""
    name = "github.name_extractor"

class GitHubDescriptionExtractor(GitPlatformDescriptionExtractor, GitHubBaseExtractor):
    name = "github.description_extractor"

class GitHubUrlExtractor(GitPlatformUrlExtractor, GitHubBaseExtractor):
    """schema:url"""
    name = "github.url_extractor"

class GitHubCodeRepositoryExtractor(GitPlatformCodeRepositoryExtractor, GitHubBaseExtractor):
    """schema:codeRepository"""
    name = "github.code_repository_extractor"

class GitHubProgrammingLanguageExtractor(GitPlatformProgrammingLanguageExtractor, GitHubBaseExtractor):
    """schema:programmingLanguage"""
    name = "github.programming_language_extractor"

class GitHubAuthorExtractor(GitPlatformAuthorExtractor, GitHubBaseExtractor):
    """schema:author"""
    name = "github.author_extractor"

class GitHubLicenseExtractor(GitPlatformLicenseExtractor, GitHubBaseExtractor):
    """schema:license"""
    name = "github.license_extractor"

    def extract(self, context, state):

        # GitHub specific License Extraction:
        try:
            license_dict = self.get_client(context, state).get_license()
            license_object = {
                '@type': 'CreativeWork',
                '@context': 'https://schema.org',
                'name': license_dict.get('name'),
                'url' : f"https://spdx.org/licenses/{license_dict.get('spdx_id')}.html"
            }
            state.metadata_collector.collect("Platform API", 'https://schema.org/license', license_object, 0.95)
        except Exception as e:
            pass
        return super().extract(context, state)

class GitHubIdentifierExtractor(GitPlatformIdentifierExtractor, GitHubBaseExtractor):
    """schema:identifier"""
    name = "github.identifier_extractor"

class GitHubCitationExtractor(GitPlatformCitationExtractor, GitHubBaseExtractor):
    """schema:citation"""
    name = "github.citation_extractor"

class GitHubKeywordsExtractor(GitPlatformKeywordsExtractor, GitHubBaseExtractor):
    """schema:keywords"""
    name = "github.keywords_extractor"

class GitHubReadmeExtractor(GitPlatformReadmeExtractor, GitHubBaseExtractor):
    """codemeta:readme"""
    name = "github.readme_extractor"

class GitHubVersionControlSystemExtractor(GitPlatformVersionControlSystemExtractor, GitHubBaseExtractor):
    """maSMP:versionControlSystem - hardcoded, since GitHub is a Git-only forge"""
    name = "github.version_control_system_extractor"

class GitHubArchivedAtExtractor(GitPlatformArchivedAtExtractor, GitHubBaseExtractor):
    """schema:archivedAt"""
    name = "github.archived_at_extractor"

class GitHubContributorsExtractor(GitPlatformContributorsExtractor, GitHubBaseExtractor):
    name = "github.contributors_extractor"

class GitHubReleaseNotesExtractor(GitHubBaseExtractor):
    """schema:releaseNotes"""
    name = "github.release_notes_extractor"

    extracts = {'https://schema.org/releaseNotes','https://codemeta.github.io/terms/releaseNotes'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_releases()
        if isinstance(result, list) and len(result) > 0:
            url = result[0].get("html_url")
            if url:
                state.metadata_collector.collect("Platform API", "https://schema.org/releaseNotes", url, 0.95)
                state.metadata_collector.collect("Platform API", 'https://codemeta.github.io/terms/releaseNotes', url, 0.95)
        return state

class GitHubSoftwareVersionExtractor(GitPlatformSoftwareVersionExtractor, GitHubBaseExtractor):
    """schema:softwareVersion"""
    name = "github.software_version_extractor"

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

class GitHubHasSourceCodeExtractor(GitPlatformHasSourceCodeExtractor, GitHubBaseExtractor):
    """maSMP:hasSourceCode"""
    name = "github.has_source_code_extractor"

class GitHubConditionsOfAccessExtractor(GitPlatformConditionsOfAccessExtractor, GitHubBaseExtractor):
    """schema:conditionsOfAccess - SoftwareApplication slot, mirrors license"""
    name = "github.conditions_of_access_extractor"

class GitHubIsAccessibleForFreeExtractor(GitPlatformIsAccessibleForFreeExtractor, GitHubBaseExtractor):
    """maSMP:isAccessibleForFree - SoftwareApplication slot, hardcoded to True"""
    name = "github.is_accessible_for_free_extractor"

class GitHubDateExtractor(GitPlatformDateExtractor, GitHubBaseExtractor):
    """extracts creation, modification, and publication dates for a GitHub repository,
    falling back to the latest tag's commit date if no releases exist"""
    name = "github.date_extractor"

class GitHubIssueTrackerExtractor(GitPlatformIssueTrackerExtractor, GitHubBaseExtractor):
    """extracts the issue tracker URL for a GitHub repository"""
    name = "github.issue_tracker_extractor"

class GitHubChangelogExtractor(GitPlatformChangelogExtractor, GitHubBaseExtractor):
    """maSMP:changeLog - derived from the releases page and/or a CHANGELOG file in the repo root"""
    name = "github.changelog_extractor"

    def extract(self, context, state):
        client = self.get_client(context, state)
        repo = client.get_repository()
        if repo.get('has_releases', False):
            if 'html_url' in repo:
                changelog_url = f"{repo['html_url']}/releases"
                state.metadata_collector.collect("Pattern", 'https://discovery.biothings.io/ns/maSMP/changeLog', changelog_url, 0.75)
        
        return super().extract(context, state)

class GitHubSoftwareRequirementExtractor(GitPlatformSoftwareRequirementExtractor, GitHubBaseExtractor):

    name = "github.software_requirements_extractor"

class GitHubLicenseCopyrightHolderExtractor(GitPlatformLicenseCopyrightHolderExtractor, GitHubBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "github.extract_copyright_year_and_holder"
    
class GitHubStorageReqExtractor(GitPlatformStorageReqExtractor, GitHubBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "github.storage_requirement_extractor"

class GitHubDownloadUrlExtractor(GitPlatformDownloadUrlExtractor, GitHubBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "github.GitHub_download_url_extractor"

class GitHubDeveloperDocumentationExtractor(GitPlatformDeveloperDocumentationExtractor, GitHubBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "github.developer_documentation_extractor"

class GitHubDocumentationExtractor(GitPlatformDocumentationExtractor, GitHubBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "github.documentation_extractor"

class GitHubCodemetaExtractor(GitPlatformCodemetaExtractor, GitHubBaseExtractor):
    """extracts metadata from a repository's codemeta.json file"""
    name = "github.codemeta_extractor"

class GitHubConnossExtractor(GitPlatformConnossExtractor, GitHubBaseExtractor):
    """extracts metadata from a repository's connoss.json file"""
    name = "github.connoss_extractor"