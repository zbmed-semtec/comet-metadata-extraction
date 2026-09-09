from app.layer_3.plugins.github.github_base_extractor import GitHubBaseExtractor
from app.layer_3.plugins.llm.extraction import (
    LlmAlternateNameExtractor,
    LlmApplicationCategoryExtractor,
    LlmBuildInstructionsExtractor,
    LlmContactExtractor,
    LlmDescriptionExtractor,
    LlmInstallationExtractor,
    LlmIntendedUseExtractor,
    LlmNameExtractor,
)


class GitHubLlmNameExtractor(LlmNameExtractor, GitHubBaseExtractor):
    """schema:name"""
    name = "github.llm_name_extractor"


class GitHubLlmDescriptionExtractor(LlmDescriptionExtractor, GitHubBaseExtractor):
    """schema:description"""
    name = "github.llm_description_extractor"


class GitHubLlmBuildInstructionsExtractor(LlmBuildInstructionsExtractor, GitHubBaseExtractor):
    """maSMP/codemeta:buildInstructions"""
    name = "github.llm_build_instructions_extractor"


class GitHubLlmInstallationExtractor(LlmInstallationExtractor, GitHubBaseExtractor):
    """maSMP:installInstructions"""
    name = "github.llm_installation_extractor"


class GitHubLlmAlternateNameExtractor(LlmAlternateNameExtractor, GitHubBaseExtractor):
    """schema:alternateName"""
    name = "github.llm_alternate_name_extractor"


class GitHubLlmApplicationCategoryExtractor(LlmApplicationCategoryExtractor, GitHubBaseExtractor):
    """schema:applicationCategory"""
    name = "github.llm_application_category_extractor"


class GitHubLlmIntendedUseExtractor(LlmIntendedUseExtractor, GitHubBaseExtractor):
    """maSMP/schema:intendedUse"""
    name = "github.llm_intended_use_extractor"


class GitHubLlmContactExtractor(LlmContactExtractor, GitHubBaseExtractor):
    """schema:contactPoint"""
    name = "github.llm_contact_extractor"
