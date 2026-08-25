from app.layer_3.plugins.codeberg.codeberg_base_extractor import CodebergBaseExtractor
from app.layer_3.plugins.llm.collection import LlmNameExtractor

class CodebergLlmNameExtractor(LlmNameExtractor, CodebergBaseExtractor):
    """schema:name"""
    name = "codeberg.llm_name_extractor"