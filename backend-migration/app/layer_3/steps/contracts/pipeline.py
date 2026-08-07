"""Pipeline contracts and default runner for composable extraction steps."""

from dataclasses import dataclass

from app.layer_3.steps.contracts.step import ExtractionStep, ExtractionContext, ExtractionState
from .progress_observer import ProgressObserver


@dataclass(frozen=True)
class ExtractionPipeline:
    """Ordered extraction pipeline."""

    steps: tuple[ExtractionStep, ...]

from traceback import print_exc
from app.layer_2.contracts.pipeline import ExtractionPipeline
from app.layer_2.contracts.step import ExtractionContext, ExtractionState

class ExtractionPipelineRunner:
    """Executes extraction steps sequentially."""

    def run(self, pipeline: ExtractionPipeline, context: ExtractionContext, state: ExtractionState, progress_observer: ProgressObserver = None) -> ExtractionState:
        """Implements app.layer_2.contracts.pipeline.PipelineRunner (structural typing, no inheritance needed)."""
        current = state
        if progress_observer:
            progress_observer.on_pipeline_started(pipeline)
        for step in pipeline.steps:
            if progress_observer:
                progress_observer.on_step_started(step)
            try:
                current = step.extract(context, current)
            except Exception:
                print_exc()
            if progress_observer:
                progress_observer.on_step_completed(step)
        if progress_observer:
            progress_observer.on_pipeline_completed(pipeline)
        return current