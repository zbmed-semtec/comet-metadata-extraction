"""
Layer 2 — Application / use cases (`app.layer_2`).
Orchestration: compose and run extraction pipeline, then build JSON-LD.
"""
from dataclasses import dataclass
from typing import Protocol, Optional, Dict, Any, Callable
from app.layer_2.contracts import ExtractionContext, ExtractionState, ExtractionPipeline, PipelineRunner, PipelineComposer
from app.layer_1.schemas.base_schema import BaseSchema
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector

# Step IDs for progress streaming (used by SSE endpoint and frontend)
EXTRACTION_STEPS = [
    ("pipeline", "Running extraction pipeline"),
    ("jsonld_build", "Building JSON-LD document"),
]


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
    ):
        self.jsonld_builder = jsonld_builder
        self.pipeline_composer = pipeline_composer
        self.pipeline_runner = pipeline_runner
        self.extraction_metadata_collector = extraction_metadata_collector

    def execute(
        self,
        repo_url: str,
        schema: BaseSchema,
        access_token: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
        single_property: Optional[str] = None,
    ) -> ExtractMetadataResult:
        """
        Execute metadata extraction for one repository.

        Args:
            repo_url: URL of the repository
            schema: Schema to use (maSMP or CODEMETA)
            access_token: Optional access token for private repositories
            progress_callback: Optional callback(step_id, status) for streaming progress.
                Ignored when single_property is set (kept lightweight for that path).
            single_property: If set, only extract this single property instead of
                the full schema (used by the `extract_property` CLI command).

        Returns:
            ExtractMetadataResult with jsonld_document and extraction_metadata
        """
        platform = repo_url
        if not platform:
            raise ValueError("Unsupported repository platform. Supported: GitHub, GitLab")

        # Progress streaming only applies to the full pipeline use case
        report_progress = progress_callback if not single_property else None

        if report_progress:
            report_progress("pipeline", "started")

        state = ExtractionState(
            metadata_collector=self.extraction_metadata_collector,
            data={},
        )
        context = ExtractionContext(
            repo_url=repo_url,
            domain="software",
            schema=schema,
            platform=platform,
            access_token=access_token,
        )

        compose_kwargs = {"single_property": single_property} if single_property else {}
        pipeline = self.pipeline_composer.compose(context, **compose_kwargs)

        metadata = self.pipeline_runner.run(pipeline, context, state).metadata_collector

        if report_progress:
            report_progress("pipeline", "completed")
            report_progress("jsonld_build", "started")

        jsonld_document = self.jsonld_builder.build_jsonld(metadata, schema)

        if report_progress:
            report_progress("jsonld_build", "completed")

        return ExtractMetadataResult(
            jsonld_document=jsonld_document,
            extraction_metadata={},
        )