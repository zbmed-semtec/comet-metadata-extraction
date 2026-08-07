"""
Layer 2 — Application / use cases (`app.layer_2`).
Orchestration: compose and run extraction pipeline, then build JSON-LD.
"""
from dataclasses import dataclass
from typing import Protocol, Optional, Dict, Any, Callable
from app.layer_2.contracts import ExtractionContext, ExtractionState, ExtractionPipeline, PipelineRunner, PipelineComposer
from app.layer_1.schemas.base_schema import BaseSchema
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
from app.layer_3.steps.contracts.progress_observer import ProgressObserver

# ---------------------------------------------------------------------------
# Extraction metadata collector (optional enrichment for UI)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractMetadataResult:
    """
    Result of the extract metadata use case.

    Exposes both the final JSON-LD document (for API/CLI consumers) and
    the internal SoftwareMetadata instance so that other services
    (e.g. FAIRness assessment) can perform schema-independent analysis.
    """
    jsonld_document: dict
    extraction_metadata: Dict[str, Dict[str, Any]]  # entity_field -> {source, confidence}


class JSONLDBuilderBase(Protocol):
    """Protocol for building JSON-LD documents"""
    def build_jsonld(self, metadata: MetadataCollector, schema: BaseSchema) -> dict:
        """Build JSON-LD document from metadata"""
        ...


class ExtractMetadataUseCase:
    """
    The main use case: compose a Layer 3 pipeline, run it, then export JSON-LD.
    """
    
    def __init__(
        self,
        jsonld_builder: JSONLDBuilderBase,
        pipeline_composer: Optional[PipelineComposer] = None,
        pipeline_runner: Optional[PipelineRunner] = None,
        extraction_metadata_collector: Optional[MetadataCollector] = None,
        progress_observer: Optional[ProgressObserver] = None,
    ):
        """
        Initialize the use case with all required tools.
        
        Args:
            jsonld_builder: Builds the final JSON-LD document
            pipeline_composer: Selects the extraction pipeline profile
            pipeline_runner: Runs the composed extraction pipeline
            extraction_metadata_collector: Optional collector for source/confidence per property (for UI)
        """
        self.jsonld_builder = jsonld_builder
        self.pipeline_composer = pipeline_composer
        self.pipeline_runner = pipeline_runner
        self.extraction_metadata_collector = extraction_metadata_collector
        self.progress_observer = progress_observer
    def execute(
        self,
        repo_url: str,
        schema: BaseSchema,
        access_token: Optional[str] = None,
    ) -> ExtractMetadataResult:
        """
        Execute metadata extraction for one repository.

        Args:
            repo_url: URL of the repository
            schema: Schema to use (maSMP or CODEMETA)
            access_token: Optional access token for private repositories
            progress_observer: Optional observer for streaming progress

        Returns:
            ExtractMetadataResult with jsonld_document and extraction_metadata (for UI enrichment)
        """
        collector = self.extraction_metadata_collector
        platform = repo_url
        if not platform:
            raise ValueError("Unsupported repository platform. Supported: GitHub, GitLab")

        state = ExtractionState(
            metadata_collector=self.extraction_metadata_collector,
            data={
            },
        )
        context = ExtractionContext(
            repo_url=repo_url,
            domain="software",
            schema=schema,
            platform=platform,
            access_token=access_token,
        )

        pipeline = self.pipeline_composer.compose(context)
        
        metadata = self.pipeline_runner.run(pipeline, context, state, self.progress_observer).metadata_collector

        # Step 5: Build JSON-LD document
        jsonld_document = self.jsonld_builder.build_jsonld(metadata, schema)

        # extraction_metadata = collector.get_all() if collector else {}
        extraction_metadata = {}

        return ExtractMetadataResult(
            jsonld_document=jsonld_document,
            extraction_metadata=extraction_metadata,
        )
