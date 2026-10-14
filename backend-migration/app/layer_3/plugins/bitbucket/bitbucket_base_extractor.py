from abc import ABC
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor
from app.layer_3.steps.contracts.step import ExtractionContext, ExtractionState
from app.layer_3.plugins.bitbucket.bitbucket_client import BitbucketClient

class BitbucketBaseExtractor(GitPlatformBaseExtractor, ABC):
    """Base extractor class for Bitbucket-hosted repositories.

    Provides common functionality for extracting metadata and content from Bitbucket repositories,
    including client initialization and caching.
    """

    platforms = {'bitbucket.org'}
    name = "please.specify.plugin.name"
    extracts = {'please.specify.what.is.being.extracted'}

    def get_client(self, context: ExtractionContext, state: ExtractionState) -> BitbucketClient:
        """Gets or creates a Bitbucket API client instance.

        The client is cached in the extraction state to avoid recreating it for multiple operations.

        Args:
            context: Extraction context containing repository URL and access token
            state: Extraction state for caching the client instance

        Returns:
            BitbucketClient: A cached Bitbucket API client instance
        """
        return BitbucketClient.get_or_create(context, state)