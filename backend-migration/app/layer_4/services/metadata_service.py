"""
Metadata extraction service: wires adapters and use case, runs extraction.
Single place for composition; endpoints call this instead of building the use case themselves.
"""
import logging
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

logger = logging.getLogger(__name__)

# Stateless components (created once, reused)
_jsonld_builder = JSONLDBuilder()
_pipeline_composer = PluginPipelineComposer()
_pipeline_runner = ExtractionPipelineRunner()
_schema_registry = LinkMlSchemaRegistry()

_logging_configured = False

def _configure_logging() -> None:
    """
    Configure application-wide logging, but only if nothing else already has.

    This module is used from three different contexts:
      - FastAPI/Uvicorn: Uvicorn (or the app's own startup) typically attaches
        handlers to the root logger before this runs. In that case we must NOT
        touch logging config, or we risk duplicate handlers / clobbering
        Uvicorn's formatting.
      - Plain library usage: the importing application is responsible for its
        own logging config. We should stay out of the way and only set up a
        safety-net handler if truly nothing is configured (to avoid the
        "No handlers could be found" / silently-swallowed-log problem).
      - CLI tool: nobody else configures logging, so we're responsible for it.

    We use a module-level flag to only attempt this once per process, and we
    detect "already configured" by checking whether the root logger has any
    handlers attached.
    """
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True

    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Something else (Uvicorn, the host app, a test runner, ...) already
        # configured logging. Respect it and don't touch anything.
        logger.debug("Logging already configured by host process; skipping basicConfig.")
        return

    log_level = getattr(settings, "log_level", None) or "INFO"
    logging.basicConfig(
        level=getattr(logging, str(log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.debug("Configured logging via basicConfig (level=%s).", log_level)

def initialize():
    _configure_logging()
    schema_dir = settings.comet_schemas_path
    if not schema_dir:
        raise RuntimeError("COMET_SCHEMAS_PATH is not configured!")
    logger.info("Loading schemas from %s", schema_dir)
    loaded = _schema_registry.load(schema_dir)
    logger.info("Loaded %d schema(s)", len(loaded))

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
    with_enrichment: bool = False,
    schema_class: str = "SoftwareSourceCode",
    progress_callback: Optional[Callable[[str, str], None]] = None,
    single_property: Optional[str] = None,
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Core extraction runner shared by all extraction entry points.

    Returns:
        (jsonld_document, enriched_metadata or None)
    """
    logger.info(
        "Starting extraction: repo_url=%s schema=%s:%s single_property=%s",
        repo_url, schema_name, schema_class, single_property,
    )

    use_case, collector = _create_extraction_use_case()

    schema = _schema_registry.get(schema_name, schema_class)

    result = use_case.execute(
        repo_url=repo_url,
        schema=schema,
        access_token=access_token,
        progress_callback=progress_callback,
        single_property=single_property,
    )
    jsonld_document = result.jsonld_document

    logger.info("Extraction completed for repo_url=%s", repo_url)

    if with_enrichment:
        enriched = build_enriched_metadata(collector, schema)
        return jsonld_document, enriched
    return jsonld_document, None