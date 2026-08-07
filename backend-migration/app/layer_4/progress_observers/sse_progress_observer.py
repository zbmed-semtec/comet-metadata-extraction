from app.layer_3.steps.contracts.progress_observer import ProgressObserver
from app.layer_3.steps.contracts.step import ExtractionStep
from app.layer_3.steps.contracts.pipeline import ExtractionPipeline

class SSEProgressObserver(ProgressObserver):
        
        def __init__(self, progress_queue):
            self.progress_queue = progress_queue

        def on_step_started(self, step : ExtractionStep) -> None:
            self.progress_queue.put({
                "event": "progress",
                "step": step.name,
                "status": "started",
                "label": step.name,
            })

        def on_step_completed(self, step : ExtractionStep) -> None:
            self.progress_queue.put({
                "event": "progress",
                "step": step.name,
                "status": "completed",
                "label": step.name,
            })
        def on_step_failed(self, step : ExtractionStep, error: Exception) -> None:
            self.progress_queue.put({
                "event": "error",
                "step": step.name,
                "message": f"Step '{step.name}' failed: {str(error)}",
            })
        def on_pipeline_started(self, pipeline : ExtractionPipeline) -> None:
            self.progress_queue.put({
                "event": "progress",
                "step": "pipeline",
                "status": "started",
                "pipeline_size": len(pipeline.steps),
                "label": "Pipeline started",
            })
        def on_pipeline_completed(self, pipeline : ExtractionPipeline) -> None:
            self.progress_queue.put({
                "event": "progress",
                "step": "pipeline",
                "status": "completed",
                "label": "Pipeline completed",
            })