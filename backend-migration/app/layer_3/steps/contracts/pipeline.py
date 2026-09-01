import logging
from app.layer_2.contracts.pipeline import ExtractionPipeline
from app.layer_2.contracts.step import ExtractionContext, ExtractionState

logger = logging.getLogger(__name__)

class ExtractionPipelineRunner:
    """Implements app.layer_2.contracts.pipeline.PipelineRunner (structural typing, no inheritance needed)."""
    def run(self, pipeline, context : ExtractionContext, state : ExtractionState) -> ExtractionState:
        current = state
        errors  = dict()
        for step in pipeline.steps:
            try:
                current = step.extract(context, current)
            except Exception as exp:
                logger.exception("step '%s' failed during extraction", step.name)
                errors[step.name] = exp
        current.errors = errors
        return current