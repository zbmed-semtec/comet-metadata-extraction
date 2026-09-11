from app.layer_3.plugins.gitlab.gitlab_base_extractor import GitLabBaseExtractor
from app.layer_3.plugins.shared.json_files.connoss_json import GitPlatformConnossExtractor
from app.layer_3.plugins.shared.json_files.codemeta_json import GitPlatformCodemetaExtractor
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
,GitPlatformDocumentationExtractor
,GitPlatformDeveloperDocumentationExtractor
,GitPlatformDownloadUrlExtractor)

class GitLabNameExtractor(GitPlatformNameExtractor, GitLabBaseExtractor):
    """schema:name"""
    name = "gitlab.name_extractor"
    
class GitLabDescriptionExtractor(GitPlatformDescriptionExtractor, GitLabBaseExtractor):
    """schema:description"""
    name = "gitlab.description_extractor"
    
class GitLabUrlExtractor(GitPlatformUrlExtractor, GitLabBaseExtractor):
    """schema:url"""
    name = "gitlab.url_extractor"

class GitLabCloneUrlExtractor(GitPlatformCodeRepositoryExtractor, GitLabBaseExtractor):
    """schema:codeRepository"""
    name = 'gitlab.code_repository_extractor'
    
class GitLabProgrammingLanguageExtractor(GitPlatformProgrammingLanguageExtractor, GitLabBaseExtractor):
    """schema:programmingLanguage"""
    name = "gitlab.programming_language_extractor"

class GitLabKeywordsExtractor(GitPlatformKeywordsExtractor, GitLabBaseExtractor):
    """schema:keywords"""
    name = "gitlab.keywords_extractor"

class GitLabAuthorExtractor(GitPlatformAuthorExtractor, GitLabBaseExtractor):
    """schema:author"""
    name = "gitlab.author_extractor"

class GitLabLicenseExtractor(GitPlatformLicenseExtractor, GitLabBaseExtractor):
    """schema:license"""
    name = "gitlab.license_extractor"

class GitLabIdentifierExtractor(GitPlatformIdentifierExtractor, GitLabBaseExtractor):
    """schema:identifier"""
    name = "gitlab.identifier_extractor"

class GitLabCitationExtractor(GitPlatformCitationExtractor, GitLabBaseExtractor):
    """schema:citation - derived from a CFF file's preferred-citation entry"""
    name = "gitlab.citation_extractor"

class GitLabReadmeExtractor(GitPlatformReadmeExtractor, GitLabBaseExtractor):
    """codemeta:readme"""
    name = "gitlab.readme_extractor"

class GitLabVersionControlSystemExtractor(GitPlatformVersionControlSystemExtractor, GitLabBaseExtractor):
    """maSMP:versionControlSystem - hardcoded, since GitLab is a Git-only forge"""
    name = "gitlab.version_control_system_extractor"

class GitLabContributorsExtractor(GitPlatformContributorsExtractor, GitLabBaseExtractor):
    """schema:contributor"""
    name = "gitlab.contributors_extractor"

class GitLabReleaseNotesExtractor(GitLabBaseExtractor):
    """schema:releaseNotes"""
    name = "gitlab.release_notes_extractor"

    extracts = {'https://schema.org/releaseNotes','https://codemeta.github.io/terms/releaseNotes'}

    def extract(self, context, state):
        result = self.get_client(context, state).get_releases()
        if isinstance(result, list) and len(result) > 0:
            url = result[0].get("_links", {}).get("self")
            if url:
                state.metadata_collector.collect("Platform API", "https://schema.org/releaseNotes", url, 0.95)
                state.metadata_collector.collect("Platform API", 'https://codemeta.github.io/terms/releaseNotes', url, 0.95)
        return state

class GitLabVersionExtractor(GitPlatformSoftwareVersionExtractor, GitLabBaseExtractor):
    """schema:softwareVersion / schema:version"""
    name = "gitlab.version_extractor"

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

class GitLabHasSourceCodeExtractor(GitPlatformHasSourceCodeExtractor, GitLabBaseExtractor):
    """maSMP:hasSourceCode"""
    name = "gitlab.has_source_code_extractor"

class GitLabConditionsOfAccessExtractor(GitPlatformConditionsOfAccessExtractor, GitLabBaseExtractor):
    """schema:conditionOfAccess - SoftwareApplication slot, mirrors license"""
    name = "gitlab.conditions_of_access_extractor"

class GitLabIsAccessibleForFreeExtractor(GitPlatformIsAccessibleForFreeExtractor, GitLabBaseExtractor):
    """maSMP:isAccessibleForFree - SoftwareApplication slot, based on repository visibility"""
    name = "gitlab.is_accessible_for_free_extractor"

class GitLabDateExtractor(GitPlatformDateExtractor, GitLabBaseExtractor):
    """schema:dateCreated / schema:dateModified / schema:datePublished"""
    name = "gitlab.date_extractor"

class GitLabIssueTrackerExtractor(GitPlatformIssueTrackerExtractor, GitLabBaseExtractor):
    """extracts the issue tracker URL for a GitLab repository"""
    name = "gitlab.issue_tracker_extractor"

class GitLabChangelogExtractor(GitPlatformChangelogExtractor, GitLabBaseExtractor):
    """maSMP:changeLog - derived from the releases page and/or a CHANGELOG file in the repo root"""
    name = "gitlab.changelog_extractor"

    def extract(self, context, state):
        client = self.get_client(context, state)
        releases = client.get_releases()
        if releases and len(releases) > 0:
            latest_release = releases[0]
            changelog_url = latest_release.get("_links", {}).get("self")
            if changelog_url:
                state.metadata_collector.collect("Pattern", 'https://discovery.biothings.io/ns/maSMP/changeLog', changelog_url, 0.75)
        
        return super().extract(context, state)

class GitLabSoftwareRequirementExtractor(GitPlatformSoftwareRequirementExtractor, GitLabBaseExtractor):
    """schema:softwareRequirements"""
    name = "gitlab.software_requirements_extractor"

class GitLabArchivedAtExtractor(GitPlatformArchivedAtExtractor, GitLabBaseExtractor):
    """schema:archivedAt"""
    name = "gitlab.archived_at_extractor"

class GitLabLicenseCopyrightHolderExtractor(GitPlatformLicenseCopyrightHolderExtractor, GitLabBaseExtractor):
    """extracts the copyright holder and year from the license file"""
    name = "gitlab.extract_copyright_year_and_holder"
    
class GitLabStorageRequirementExtractor(GitPlatformStorageReqExtractor, GitLabBaseExtractor):
    """extracts storage requirements from repository size"""
    name = "gitlab.storage_requirement_extractor"

class GitLabDownloadUrlExtractor(GitPlatformDownloadUrlExtractor, GitLabBaseExtractor):
    """extracts the download URL for the repository's default branch as a zip file"""
    name = "gitlab.download_url_extractor"

class GitLabDeveloperDocumentationExtractor(GitPlatformDeveloperDocumentationExtractor, GitLabBaseExtractor):
    """extracts the developer documentation URL for the repository"""
    name = "gitlab.developer_documentation_extractor"

class GitLabDocumentationExtractor(GitPlatformDocumentationExtractor, GitLabBaseExtractor):
    """extracts the documentation URL for the repository"""
    name = "gitlab.documentation_extractor"

class GitLabCodemetaExtractor(GitPlatformCodemetaExtractor, GitLabBaseExtractor):
    """extracts metadata from a repository's codemeta.json file"""
    name = "gitlab.codemeta_extractor"

class GitLabConnossExtractor(GitPlatformConnossExtractor, GitLabBaseExtractor):
    """extracts metadata from a repository's connoss.json file"""
    name = "gitlab.connoss_extractor"