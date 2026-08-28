"""
AS OF 2026-06 THIS IS CURRENTLY ON HOLD.
THE FAIRness ASSESSMENT MIGHT BE REWORKED AT A LATER DATE.

Metadata + FAIRness service.

Provides a single entry point for running extraction and FAIRness assessment
for CLI, HTTP API, and the public Python API.

FAIRness scores are computed from the internal SoftwareMetadata entity so
that they are invariant to the exported schema (maSMP vs CODEMETA). The
schema still controls the shape of the JSON-LD returned alongside the report.
"""
from typing import Dict, Optional, Tuple

from app.layer_2.use_cases.extract_metadata import ExtractMetadataUseCase
from app.layer_3.evaluators.fairness_evaluator import evaluate_fairness_from_metadata
from app.layer_2.contracts import PipelineComposer
from app.layer_3.builders.jsonld_builder import JSONLDBuilder
from app.layer_3.steps.contracts import ExtractionPipelineRunner
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector


_jsonld_builder = JSONLDBuilder()
# _pipeline_composer = PipelineComposer()
_pipeline_runner = ExtractionPipelineRunner()


def run_fairness_assessment(
    repo_url: str,
    schema: str,
    access_token: Optional[str] = None,
    with_enrichment: bool = False,
) -> Tuple[Dict, "FairnessReport"]:
    """
    Run metadata extraction and FAIRness assessment once.

    FAIRness is computed from the unified SoftwareMetadata, so scores do not
    depend on whether maSMP or CODEMETA is chosen. The JSON-LD document that
    is returned does respect the requested schema.

    Returns:
        (jsonld_document, fairness_report)
    """
    collector = MetadataCollector()

    use_case = ExtractMetadataUseCase(
        jsonld_builder=_jsonld_builder,
        pipeline_composer=_pipeline_composer,
        pipeline_runner=_pipeline_runner,
        extraction_metadata_collector=collector,
    )

    result = use_case.execute(
        repo_url=repo_url,
        schema=schema,
        access_token=access_token,
    )

    jsonld_document = result.jsonld_document
    fairness_report = evaluate_fairness_from_metadata(result.metadata)
    return jsonld_document, fairness_report

