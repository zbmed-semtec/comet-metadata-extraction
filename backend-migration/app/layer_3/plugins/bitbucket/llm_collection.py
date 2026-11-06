from app.layer_3.plugins.bitbucket.bitbucket_base_extractor import BitbucketBaseExtractor
from app.layer_3.plugins.llm.extraction import (
    LlmAlternateNameExtractor,
    LlmApplicationCategoryExtractor,
    LlmBuildInstructionsExtractor,
    LlmContactExtractor,
    LlmDescriptionExtractor,
    LlmInstallationExtractor,
    LlmIntendedUseExtractor,
    # LlmNameExtractor,
)


# class BitbucketLlmNameExtractor(LlmNameExtractor, BitbucketBaseExtractor):
#     """schema:name"""
#     name = "bitbucket.llm_name_extractor"


class BitbucketLlmDescriptionExtractor(LlmDescriptionExtractor, BitbucketBaseExtractor):
    """schema:description"""
    name = "bitbucket.llm_description_extractor"


class BitbucketLlmBuildInstructionsExtractor(LlmBuildInstructionsExtractor, BitbucketBaseExtractor):
    """maSMP/codemeta:buildInstructions"""
    name = "bitbucket.llm_build_instructions_extractor"


class BitbucketLlmInstallationExtractor(LlmInstallationExtractor, BitbucketBaseExtractor):
    """maSMP:installInstructions"""
    name = "bitbucket.llm_installation_extractor"


class BitbucketLlmAlternateNameExtractor(LlmAlternateNameExtractor, BitbucketBaseExtractor):
    """schema:alternateName"""
    name = "bitbucket.llm_alternate_name_extractor"


class BitbucketLlmApplicationCategoryExtractor(LlmApplicationCategoryExtractor, BitbucketBaseExtractor):
    """schema:applicationCategory"""
    name = "bitbucket.llm_application_category_extractor"


class BitbucketLlmIntendedUseExtractor(LlmIntendedUseExtractor, BitbucketBaseExtractor):
    """maSMP/schema:intendedUse"""
    name = "bitbucket.llm_intended_use_extractor"


class BitbucketLlmContactExtractor(LlmContactExtractor, BitbucketBaseExtractor):
    """schema:contactPoint"""
    name = "bitbucket.llm_contact_extractor"
