"""Bitbucket extractor plugins for populating schema.org / codemeta / maSMP
metadata fields from a repository's Bitbucket API data, CITATION.cff files,
README files, and license files."""

from app.layer_3.plugins.bitbucket.bitbucket_base_extractor import BitbucketBaseExtractor
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

class BitbucketNameExtractor(GitPlatformNameExtractor, BitbucketBaseExtractor):
    """schema:name"""
    name = "bitbucket.name_extractor"

class BitbucketDescriptionExtractor(GitPlatformDescriptionExtractor, BitbucketBaseExtractor):
    name = "bitbucket.description_extractor"

class BitbucketUrlExtractor(GitPlatformUrlExtractor, BitbucketBaseExtractor):
    """schema:url"""
    name = "bitbucket.url_extractor"

class BitbucketCodeRepositoryExtractor(GitPlatformCodeRepositoryExtractor, BitbucketBaseExtractor):
    """schema:codeRepository"""
    name = "bitbucket.code_repository_extractor"

class BitbucketProgrammingLanguageExtractor(GitPlatformProgrammingLanguageExtractor, BitbucketBaseExtractor):
    """schema:programmingLanguage"""
    name = "bitbucket.programming_language_extractor"

class BitbucketAuthorExtractor(GitPlatformAuthorExtractor, BitbucketBaseExtractor):
    """schema:author"""
    name = "bitbucket.author_extractor"

class BitbucketLicenseExtractor(GitPlatformLicenseExtractor, BitbucketBaseExtractor):
    """schema:license"""
    name = "bitbucket.license_extractor"

    def extract(self, context, state):

        # Bitbucket specific License Extraction:
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

class BitbucketIdentifierExtractor(GitPlatformIdentifierExtractor, BitbucketBaseExtractor):
    """schema:identifier"""
    name = "bitbucket.identifier_extractor"

class BitbucketCitationExtractor(GitPlatformCitationExtractor, BitbucketBaseExtractor):
    """schema:citation"""
    name = "bitbucket.citation_extractor"

class BitbucketKeywordsExtractor(GitPlatformKeywordsExtractor, BitbucketBaseExtractor):
    """schema:keywords"""
    name = "bitbucket.keywords_extractor"

class BitbucketReadmeExtractor(GitPlatformReadmeExtractor, BitbucketBaseExtractor):
    """codemeta:readme"""
    name = "bitbucket.readme_extractor"

class BitbucketVersionControlSystemExtractor(GitPlatformVersionControlSystemExtractor, BitbucketBaseExtractor):
    """maSMP:versionControlSystem - Bitbucket supports both Git and (historically) Mercurial,
    so this may need to check the repo's `scm` field rather than being hardcoded."""
    name = "bitbucket.version_control_system_extractor"

class BitbucketArchivedAtExtractor(GitPlatformArchivedAtExtractor, BitbucketBaseExtractor):
    """schema:archivedAt"""
    name = "bitbucket.archived_at_extractor"

class BitbucketContributorsExtractor(GitPlatformContributorsExtractor, BitbucketBaseExtractor):
    name = "bitbucket.contributors_extractor"

class BitbucketReleaseNotesExtractor(BitbucketBaseExtractor):
    """schema:releaseNotes"""
    name = "bitbucket.release_notes_extractor"

    extracts = {'https://schema.org/releaseNotes','https://codemeta.github.io/terms/releaseNotes'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_releases()
        if isinstance(result, list) and len(result) > 0:
            url = result[0].get("html_url")
            if url:
                state.metadata_collector.collect("Platform API", "https://schema.org/releaseNotes", url, 0.95)
                state.metadata_collector.collect("Platform API", 'https://codemeta.github.io/terms/releaseNotes', url, 0.95)
        return state

class BitbucketSoftwareVersionExtractor(GitPlatformSoftwareVersionExtractor, BitbucketBaseExtractor):
    """schema:softwareVersion"""
    name = "bitbucket.software_version_extractor"

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

class BitbucketHasSourceCodeExtractor(GitPlatformHasSourceCodeExtractor, BitbucketBaseExtractor):
    """maSMP:hasSourceCode"""
    name = "bitbucket.has_source_code_extractor"

class BitbucketConditionsOfAccessExtractor(GitPlatformConditionsOfAccessExtractor, BitbucketBaseExtractor):
    """schema:conditionsOfAccess - SoftwareApplication slot, mirrors license"""
    name = "bitbucket.conditions_of_access_extractor"

class BitbucketIsAccessibleForFreeExtractor(GitPlatformIsAccessibleForFreeExtractor, BitbucketBaseExtractor):
    """maSMP:isAccessibleForFree - SoftwareApplication slot, hardcoded to True"""
    name = "bitbucket.is_accessible_for_free_extractor"

class BitbucketDateExtractor(GitPlatformDateExtractor, BitbucketBaseExtractor):
    """extracts creation, modification, and publication dates for a Bitbucket repository,
    falling back to the latest tag's commit date if no releases exist"""
    name = "bitbucket.date_extractor"

class BitbucketIssueTrackerExtractor(GitPlatformIssueTrackerExtractor, BitbucketBaseExtractor):
    """extracts the issue tracker URL for a Bitbucket repository"""
    name = "bitbucket.issue_tracker_extractor"

class BitbucketChangelogExtractor(GitPlatformChangelogExtractor, BitbucketBaseExtractor):
    """maSMP:changeLog - derived from the releases page and/or a CHANGELOG file in the repo root"""
    name = "bitbucket.changelog_extractor"

    def extract(self, context, state):
        client = self.get_client(context, state)
        repo = client.get_repository()
        if repo.get('has_releases', False):
            if 'html_url' in repo:
                changelog_url = f"{repo['html_url']}/releases"
                state.metadata_collector.collect("Pattern", 'https://discovery.biothings.io/ns/maSMP/changeLog', changelog_url, 0.75)

        return super().extract(context, state)

class BitbucketSoftwareRequirementExtractor(GitPlatformSoftwareRequirementExtractor, BitbucketBaseExtractor):

    name = "bitbucket.software_requirements_extractor"

class BitbucketLicenseCopyrightHolderExtractor(GitPlatformLicenseCopyrightHolderExtractor, BitbucketBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "bitbucket.extract_copyright_year_and_holder"

class BitbucketStorageReqExtractor(GitPlatformStorageReqExtractor, BitbucketBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "bitbucket.storage_requirement_extractor"

class BitbucketDownloadUrlExtractor(GitPlatformDownloadUrlExtractor, BitbucketBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "bitbucket.Bitbucket_download_url_extractor"

class BitbucketDeveloperDocumentationExtractor(GitPlatformDeveloperDocumentationExtractor, BitbucketBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "bitbucket.developer_documentation_extractor"

class BitbucketDocumentationExtractor(GitPlatformDocumentationExtractor, BitbucketBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "bitbucket.documentation_extractor"

class BitbucketCodemetaExtractor(GitPlatformCodemetaExtractor, BitbucketBaseExtractor):
    """extracts metadata from a repository's codemeta.json file"""
    name = "bitbucket.codemeta_extractor"

class BitbucketConnossExtractor(GitPlatformConnossExtractor, BitbucketBaseExtractor):
    """extracts metadata from a repository's connoss.json file"""
    name = "bitbucket.connoss_extractor"