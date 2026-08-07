from abc import ABC, abstractmethod

class ProgressObserver(ABC):
    """
    Abstract base class for observing progress of metadata extraction steps.

    This allows us to decouple the core extraction logic from the specifics of how progress is reported (e.g. CLI output, SSE events, etc.). 
    """

    @abstractmethod
    def on_step_started(self, step : "ExtractionStep") -> None:
        """Called when a step starts. step_name is a string identifier for the step."""
        pass

    @abstractmethod
    def on_step_completed(self, step : "ExtractionStep") -> None:
        """Called when a step completes successfully."""
        pass

    @abstractmethod
    def on_step_failed(self, step : "ExtractionStep", error: Exception) -> None:
        """Called when a step fails with an error."""
        pass
    
    @abstractmethod
    def on_pipeline_started(self, pipeline : "ExtractionPipeline") -> None:
        """Called when the entire pipeline starts."""
        pass

    @abstractmethod
    def on_pipeline_completed(self, pipeline : "ExtractionPipeline") -> None:
        """Called when the entire pipeline completes successfully."""
        pass