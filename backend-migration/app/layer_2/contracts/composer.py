from typing import Protocol
from app.layer_2.contracts.step import ExtractionContext
from app.layer_2.contracts.pipeline import ExtractionPipeline

class PipelineComposer(Protocol):
    def compose(self, context: ExtractionContext, single_property: str = None) -> ExtractionPipeline: ...