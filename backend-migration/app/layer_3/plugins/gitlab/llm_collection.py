from app.layer_3.plugins.gitlab.gitlab_base_extractor import GitLabBaseExtractor
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


class GitLabLlmNameExtractor(LlmNameExtractor, GitLabBaseExtractor):
    """schema:name"""
    name = "gitlab.llm_name_extractor"


class GitLabLlmDescriptionExtractor(LlmDescriptionExtractor, GitLabBaseExtractor):
    """schema:description"""
    name = "gitlab.llm_description_extractor"


class GitLabLlmBuildInstructionsExtractor(LlmBuildInstructionsExtractor, GitLabBaseExtractor):
    """maSMP/codemeta:buildInstructions"""
    name = "gitlab.llm_build_instructions_extractor"


class GitLabLlmInstallationExtractor(LlmInstallationExtractor, GitLabBaseExtractor):
    """maSMP:installInstructions"""
    name = "gitlab.llm_installation_extractor"


class GitLabLlmAlternateNameExtractor(LlmAlternateNameExtractor, GitLabBaseExtractor):
    """schema:alternateName"""
    name = "gitlab.llm_alternate_name_extractor"


class GitLabLlmApplicationCategoryExtractor(LlmApplicationCategoryExtractor, GitLabBaseExtractor):
    """schema:applicationCategory"""
    name = "gitlab.llm_application_category_extractor"


class GitLabLlmIntendedUseExtractor(LlmIntendedUseExtractor, GitLabBaseExtractor):
    """maSMP/schema:intendedUse"""
    name = "gitlab.llm_intended_use_extractor"


class GitLabLlmContactExtractor(LlmContactExtractor, GitLabBaseExtractor):
    """schema:contactPoint"""
    name = "gitlab.llm_contact_extractor"
