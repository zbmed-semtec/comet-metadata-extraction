from traceback import print_exc
from app.layer_2.contracts.pipeline import ExtractionPipeline
from app.layer_2.contracts.step import ExtractionContext, ExtractionState

class ExtractionPipelineRunner:
    """Implements app.layer_2.contracts.pipeline.PipelineRunner (structural typing, no inheritance needed)."""
    def run(self, pipeline, context : ExtractionContext, state : ExtractionState) -> ExtractionState:
        current = state
        errors  = dict()
        for step in pipeline.steps:
            try:
                current = step.extract(context, current)
            except Exception as exp:
                errors[step.name] = exp
        current.errors = errors
        return current