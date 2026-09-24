import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from fastapi.encoders import jsonable_encoder

from app.layer_4.services.metadata_service import run_extraction, initialize
from app.layer_4.services.fairness_service import run_fairness_assessment

logger = logging.getLogger(__name__)


def _print_json(data: Any) -> None:
    """Print JSON-safe data to stdout."""
    safe_data = jsonable_encoder(data)
    json.dump(safe_data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

def _extract_command(args: argparse.Namespace) -> None:
    initialize()
    result = run_extraction(
        repo_url=args.url,
        schema_name=args.schema,
        access_token=args.token,
        with_enrichment=args.with_enrichment,
        schema_class=args.schema_class,
    )

    if result.extraction_state.errors:
        logger.warning("Extraction completed with errors: %s", result.extraction_state.errors)
        print("Extraction completed with errors:", file=sys.stderr)
        for step_name, error in result.extraction_state.errors.items():
            print(f"  Step '{step_name}': {error}", file=sys.stderr)

    result = {
        "schema": args.schema,
        "code_url": args.url,
        "results": result.jsonld_document,
        "enriched_metadata": result.enriched_metadata or {},
    }
    _print_json(result)

def _property_key_candidates(property_name: str) -> List[str]:
    """
    Return candidate keys to look up in the JSON-LD document / enrichment map.

    JSON-LD keys are plain schema property (slot) names, so a prefixed
    "codemeta:readme" or underscored "codemeta_readme" is normalized to
    "readme" first, with the raw input kept as fallback.
    """
    stripped = property_name.split(":")[-1]
    candidates = [stripped]
    for variant in (property_name, property_name.replace(":", "_")):
        if variant not in candidates:
            candidates.append(variant)
    return candidates


def _resolve_key(candidates: List[str], mapping: Dict[str, Any]) -> Optional[str]:
    for key in candidates:
        if key in mapping and mapping[key] is not None:
            return key
    return None


def _collect_property_results(
    schema: str,
    code_url: str,
    jsonld_document: Dict[str, Any],
    enriched_metadata: Dict[str, Any],
    property_name: str,
) -> Dict[str, Any]:
    candidates = _property_key_candidates(property_name)
    jsonld_key = _resolve_key(candidates, jsonld_document)

    matches: List[Dict[str, Any]] = []
    if jsonld_key is not None:
        meta = {}
        if isinstance(enriched_metadata, dict):
            enriched_key = _resolve_key(candidates, enriched_metadata)
            if enriched_key is not None:
                meta = enriched_metadata[enriched_key]
        matches.append(
            {
                "profile": jsonld_document.get("@type", schema),
                "property": jsonld_key,
                "value": jsonld_document[jsonld_key],
                "source": meta.get("source"),
                "confidence": meta.get("confidence"),
                "category": meta.get("category"),
            }
        )

    return {
        "schema": schema,
        "code_url": code_url,
        "property": property_name,
        "matches": matches,
    }


def _extract_property_command(args: argparse.Namespace) -> None:
    initialize()
    try:
        result = run_extraction(
            repo_url=args.url,
            schema_name=args.schema,
            access_token=args.token,
            with_enrichment=True,
            schema_class=args.schema_class,
            single_property=args.property,
            fairness_assessment=False,
        )
    except ValueError as e:
        logger.warning("Unknown property: %s", e)
        print(f"Unknown property '{args.property}' in schema '{args.schema}': {e}", file=sys.stderr)
        sys.exit(2)

    extraction_errors = result.extraction_state.errors if result.extraction_state else None

    summary = _collect_property_results(
        schema=args.schema,
        code_url=args.url,
        jsonld_document=result.jsonld_document,
        enriched_metadata=result.enriched_metadata or {},
        property_name=args.property,
    )

    if not summary["matches"]:
        message = (
            f"No matches found for property '{args.property}' "
            f"in schema '{args.schema}' for URL '{args.url}'."
        )
        logger.warning(message)
        print(message, file=sys.stderr)
        sys.exit(1)

    if extraction_errors:
        logger.warning("Extraction completed with errors: %s", extraction_errors)
        print("Extraction completed with errors:", file=sys.stderr)
        for step_name, error in extraction_errors.items():
            print(f"  Step '{step_name}': {error}", file=sys.stderr)

    for match in summary["matches"]:
        output = {
            "property_name": match["property"],
            "property_value": match["value"],
            "source": match.get("source"),
            "confidence": match.get("confidence"),
        }
        _print_json(output)

def _fairness_command(args: argparse.Namespace) -> None:
    """
    Compute a FAIRness report for a repository and print JSON.
    """
    initialize()
    result = run_extraction(
        repo_url=args.url,
        schema_name="ConnOSS",
        access_token=args.token,
        with_enrichment=False,
        schema_class="Software",
        fairness_assessment=True,
    )

    result = {
        "schema": "ConnOSS",
        "code_url": args.url,
        "results": result.jsonld_document,
        "fairness": asdict(result.fairness_report),
    }
    _print_json(result)

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="comet-rs",
        description=(
            "Extract metadata (and per-property sources) "
            "from code repositories, for any supported schema."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # comet-rs extract {GIT_URL} {SCHEMA}
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract full JSON-LD metadata for a repository.",
    )
    extract_parser.add_argument("url", help="Repository URL (GitHub, GitLab).")
    extract_parser.add_argument(
        "schema",
        help="Schema to analyze against (e.g. connoss, CODEMETA).",
    )
    extract_parser.add_argument(
        "--schema-class",
        default="software",
        help="Schema class to use (default: software).",
    )
    extract_parser.add_argument(
        "--token",
        help="GitHub/GitLab token (or set GITHUB_TOKEN / GITLAB_TOKEN). Raises rate limits when unset.",
    )
    extract_parser.add_argument(
        "--with-enrichment",
        action="store_true",
        help="Include per-property enrichment (source, confidence, category) when available.",
    )
    extract_parser.set_defaults(func=_extract_command)

    # comet-rs extract_property {GIT_URL} {PROPERTY_NAME} [--schema SCHEMA]
    extract_prop_parser = subparsers.add_parser(
        "extract_property",
        help=(
            "Extract a single property (value and source) for a repository. "
            "Schema defaults to connoss if not given."
        ),
    )
    extract_prop_parser.add_argument("url", help="Repository URL (GitHub, GitLab).")
    extract_prop_parser.add_argument(
        "property",
        help=(
            "Property name to extract, e.g. 'name', 'identifier', "
            "'codemeta:referencePublication' or 'codemeta_referencePublication'."
        ),
    )
    extract_prop_parser.add_argument(
        "--schema",
        default="connoss",
        help="Schema to use (default: connoss).",
    )
    extract_prop_parser.add_argument(
        "--schema-class",
        default="software",
        help="Schema class to use (default: software).",
    )
    extract_prop_parser.add_argument(
        "--token",
        help="GitHub/GitLab token (or set GITHUB_TOKEN / GITLAB_TOKEN). Raises rate limits when unset.",
    )
    extract_prop_parser.set_defaults(func=_extract_property_command)

    # comet-rs fairness {GIT_URL} {SCHEMA}
    fairness_parser = subparsers.add_parser(
        "fairness",
        help="Compute a FAIRness report (F/A/I/R scores) for a repository.",
    )
    fairness_parser.add_argument("url", help="Repository URL (GitHub, GitLab).")
    fairness_parser.add_argument(
        "--token",
        help="GitHub/GitLab token (or set GITHUB_TOKEN / GITLAB_TOKEN). Raises rate limits when unset.",
    )
    fairness_parser.set_defaults(func=_fairness_command)

    args = parser.parse_args()

    # Use env token if --token not provided; pick by repo URL so GitLab URLs get GITLAB_TOKEN
    if getattr(args, "token", None) is None:
        repo_url = (getattr(args, "url", None) or "").lower()
        if "gitlab" in repo_url:
            args.token = os.environ.get("GITLAB_TOKEN")
        elif "github" in repo_url:
            args.token = os.environ.get("GITHUB_TOKEN")
        elif 'codeberg' in repo_url:
            args.token = os.environ.get("CODEBERG_TOKEN")

    try:
        args.func(args)
    except Exception as e:
        logger.exception("comet-rs command failed")
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()