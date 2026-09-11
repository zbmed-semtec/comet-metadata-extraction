from app.config.settings import settings
from app.layer_2.contracts.step import ExtractionContext
from app.layer_3.plugins.shared.git_platform_base_extractor import GitPlatformBaseExtractor
from app.layer_3.plugins.llm.bootstrap import bootstrap_ollama_if_configured

class LlmBaseExtractor(GitPlatformBaseExtractor):
    """Base class for LLM extractors."""

    def applicable(self, context: ExtractionContext):
        """Check if the extractor is applicable to the given context."""
        return super().applicable(context) and settings.llm_enabled

    def on_load(self):
        """Perform any necessary setup when the extractor is loaded."""
        if settings.llm_enabled:
            bootstrap_ollama_if_configured(log_prefix="llm", strict=True)
        return super().on_load()