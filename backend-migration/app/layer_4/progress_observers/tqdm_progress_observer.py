"""Tqdm-based progress observer for extraction pipeline steps."""
from app.layer_3.steps.contracts.progress_observer import ProgressObserver
from app.layer_3.steps.contracts.step import ExtractionStep
from app.layer_3.steps.contracts.pipeline import ExtractionPipeline
from tqdm import tqdm

class TqdmProgressObserver(ProgressObserver):
    """
    Reports extraction pipeline progress using tqdm progress bars.

    Displays a pipeline-level bar tracking completed steps, and logs
    individual step transitions as tqdm messages to avoid breaking
    the progress display.
    """

    def __init__(self):
        self._progress_bar: tqdm | None = None

    def on_pipeline_started(self, pipeline: ExtractionPipeline) -> None:
        self._progress_bar = tqdm(
            total=len(pipeline.steps),
            desc="Extracting metadata",
            unit="step",
        )

    def on_pipeline_completed(self, pipeline: ExtractionPipeline) -> None:
        if self._progress_bar is not None:
            self._progress_bar.close()
            self._progress_bar = None

    def on_step_started(self, step: ExtractionStep) -> None:
        if self._progress_bar is not None:
            self._progress_bar.set_postfix_str(f"{step.name} …")

    def on_step_completed(self, step: ExtractionStep) -> None:
        if self._progress_bar is not None:
            tqdm.write(f"  ✓ {step.name}")
            self._progress_bar.update(1)
            self._progress_bar.set_postfix_str("")

    def on_step_failed(self, step: ExtractionStep, error: Exception) -> None:
        if self._progress_bar is not None:
            tqdm.write(f"  ✗ {step.name}: {error}")
            self._progress_bar.set_postfix_str(f"failed at {step.name}")

    