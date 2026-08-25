from app.layer_3.plugins.gitlab.gitlab_base_extractor import GitLabBaseExtractor
from app.layer_3.plugins.llm.collection import LlmNameExtractor

class GitLabLlmNameExtractor(LlmNameExtractor, GitLabBaseExtractor):
    """schema:name"""
    name = "gitlab.llm_name_extractor"