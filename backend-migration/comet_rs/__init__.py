"""
Public Python API for comet_rs.

Provides simple, stable functions for extracting metadata and assessing FAIRness
without exposing internal app.* wiring.
"""
from typing import Any, Dict, Optional, Tuple, List

from app.layer_4.services.metadata_service import run_extraction, initialize

def extract_metadata(
    repo_url: str,
    schema_name: str = "connoss",
    schema_class: str = "Software",
    *,
    token: Optional[str] = None,
    with_enrichment: bool = False,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    High-level wrapper to extract connoss/CODEMETA metadata for a repository.

    Returns:
        (jsonld_document, enriched_metadata or None)
    """
    initialize()

    return run_extraction(
        repo_url=repo_url,
        schema_name=schema_name,
        schema_class=schema_class,
        access_token=token,
        with_enrichment=with_enrichment,
    )


def extract_property(
    repo_url: str,
    property_name: str,
    schema_name: str = "connoss",
    schema_class: str = "Software",
    *,
    token: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract a single property (value + source + confidence) for a repository.

    Returns:
        (extracted_at_iso, [ {profile, value, source, confidence}, ... ])

    For connoss, the property may be present in both SoftwareSourceCode and
    SoftwareApplication profiles; all matches are returned. For CODEMETA,
    a single synthetic \"codemeta\" profile is used.
    """
    initialize()
    return run_extraction(
        repo_url=repo_url,
        schema_name=schema_name,
        schema_class=schema_class,
        access_token=token,
        single_property=property_name,
    )

__all__ = ["extract_metadata", "extract_property"]

