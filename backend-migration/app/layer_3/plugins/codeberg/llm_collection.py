from app.layer_3.plugins.codeberg.codeberg_base_extractor import CodebergBaseExtractor
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


class CodebergLlmNameExtractor(LlmNameExtractor, CodebergBaseExtractor):
    """schema:name"""
    name = "codeberg.llm_name_extractor"


class CodebergLlmDescriptionExtractor(LlmDescriptionExtractor, CodebergBaseExtractor):
    """schema:description"""
    name = "codeberg.llm_description_extractor"


class CodebergLlmBuildInstructionsExtractor(LlmBuildInstructionsExtractor, CodebergBaseExtractor):
    """maSMP/codemeta:buildInstructions"""
    name = "codeberg.llm_build_instructions_extractor"


class CodebergLlmInstallationExtractor(LlmInstallationExtractor, CodebergBaseExtractor):
    """maSMP:installInstructions"""
    name = "codeberg.llm_installation_extractor"


class CodebergLlmAlternateNameExtractor(LlmAlternateNameExtractor, CodebergBaseExtractor):
    """schema:alternateName"""
    name = "codeberg.llm_alternate_name_extractor"


class CodebergLlmApplicationCategoryExtractor(LlmApplicationCategoryExtractor, CodebergBaseExtractor):
    """schema:applicationCategory"""
    name = "codeberg.llm_application_category_extractor"


class CodebergLlmIntendedUseExtractor(LlmIntendedUseExtractor, CodebergBaseExtractor):
    """maSMP/schema:intendedUse"""
    name = "codeberg.llm_intended_use_extractor"


class CodebergLlmContactExtractor(LlmContactExtractor, CodebergBaseExtractor):
    """schema:contactPoint"""
    name = "codeberg.llm_contact_extractor"
