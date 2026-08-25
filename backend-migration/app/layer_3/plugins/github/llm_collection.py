from app.layer_3.plugins.github.github_base_extractor import GitHubBaseExtractor
from app.layer_3.plugins.llm.collection import LlmNameExtractor

class GitHubLlmNameExtractor(LlmNameExtractor, GitHubBaseExtractor):
    """schema:name"""
    name = "github.llm_name_extractor"