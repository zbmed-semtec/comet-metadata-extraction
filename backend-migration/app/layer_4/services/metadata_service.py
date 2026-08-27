"""
Metadata extraction service: wires adapters and use case, runs extraction.
Single place for composition; endpoints call this instead of building the use case themselves.
"""
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List

from app.layer_3.composers.plugin_pipeline_composer import PluginPipelineComposer
from app.layer_3.builders.jsonld_builder import JSONLDBuilder
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
from app.layer_3.steps.contracts import ExtractionPipelineRunner
from app.layer_2.use_cases.extract_metadata import ExtractMetadataUseCase
from app.layer_4.builders.enriched_metadata import build_enriched_metadata
from app.layer_3.schemas.linkml.linkml_schema_registry import LinkMlSchemaRegistry
from app.config.settings import settings

# Stateless components (created once, reused)
_jsonld_builder = JSONLDBuilder()
_pipeline_composer = PluginPipelineComposer()
_pipeline_runner = ExtractionPipelineRunner()
_schema_registry = LinkMlSchemaRegistry()

def initialize():
    schema_dir = settings.comet_schemas_path
    if not schema_dir:
        raise RuntimeError("COMET_SCHEMAS_PATH is not configured!")
    _schema_registry.load(schema_dir)

def _create_extraction_use_case() -> tuple[ExtractMetadataUseCase, Optional[MetadataCollector]]:
    """
    Internal helper to create a fully-wired ExtractMetadataUseCase plus optional collector.

    This centralises the orchestration wiring so that different services
    (plain extraction, extraction with progress, FAIRness assessment, etc.)
    can all share the same composition.
    """
    collector = MetadataCollector()

    use_case = ExtractMetadataUseCase(
        jsonld_builder=_jsonld_builder,
        pipeline_composer=_pipeline_composer,
        pipeline_runner=_pipeline_runner,
        extraction_metadata_collector=collector,
    )

    return use_case, collector

def run_extraction(
    repo_url: str,
    schema_name: str,
    access_token: Optional[str],
    with_enrichment: bool,
    schema_class: str = "SoftwareSourceCode",
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Run metadata extraction once.
    
    Returns:
        (jsonld_document, enriched_metadata or None)
    """
    use_case, collector = _create_extraction_use_case(
    )

    schema = _schema_registry.get(schema_name, schema_class)

    result = use_case.execute(repo_url=repo_url, schema=schema, access_token=access_token)
    jsonld_document = result.jsonld_document

    if with_enrichment:
        enriched = build_enriched_metadata(
            collector,
            schema,
        )
        return jsonld_document, enriched
    return jsonld_document, None


def run_extraction_with_progress(
    repo_url: str,
    schema_name: str,
    access_token: Optional[str],
    with_enrichment: bool,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    schema_class: str = "SoftwareSourceCode",
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Run metadata extraction with optional progress callbacks.

    progress_callback(step_id, status) is called for each step; step_id is one of
    platform, file_parsing, external_data, llm, jsonld_build; status is "started" or "completed".

    Returns:
        (jsonld_document, enriched_metadata or None)
    """
    use_case, collector = _create_extraction_use_case(
    )

    schema = _schema_registry.get(schema_name, schema_class)

    result = use_case.execute(
        repo_url=repo_url,
        schema=schema,
        access_token=access_token,
        progress_callback=progress_callback,
    )
    jsonld_document = result.jsonld_document

    if with_enrichment:
        enriched = build_enriched_metadata(
            collector,
            schema,
        )
        return jsonld_document, enriched
    return jsonld_document, None


def run_single_property_extraction(
    repo_url: str,
    schema_name: str,
    access_token: Optional[str],
    property_name: str,
    schema_class: str = "SoftwareSourceCode",
    with_enrichment: bool = True,
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Run extraction with enrichment and project down to a single property's
    value, source, and confidence.

    Returns:
        (extracted_at_iso, [ {profile, value, source, confidence}, ... ])
    """
    use_case, collector = use_case, collector = _create_extraction_use_case(
        )

    schema = _schema_registry.get(schema_name, schema_class)

    result = use_case.execute(repo_url=repo_url, schema=schema, access_token=access_token, single_property=property_name)
    jsonld_document = result.jsonld_document

    if with_enrichment:
        enriched = build_enriched_metadata(
            collector,
            schema,
        )
        return jsonld_document, enriched
    return jsonld_document, None

