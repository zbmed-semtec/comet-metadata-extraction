import argparse
import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from fastapi.encoders import jsonable_encoder

from app.layer_4.services.metadata_service import run_extraction, run_extraction_with_progress, initialize
from app.layer_4.services.fairness_service import run_fairness_assessment

def _print_json(data: Any) -> None:
    """Print JSON-safe data to stdout."""
    safe_data = jsonable_encoder(data)
    json.dump(safe_data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

def _extract_command(args: argparse.Namespace) -> None:

    initialize()
    progress_observer = None
    if args.show_progress:
        from app.layer_4.progress_observers.tqdm_progress_observer import TqdmProgressObserver
        progress_observer = TqdmProgressObserver()

    jsonld_document, enriched = run_extraction_with_progress(
        repo_url=args.url,
        schema_name=args.schema,
        access_token=args.token,
        with_enrichment=args.with_enrichment,
        schema_class=args.schema_class,
        progress_observer=progress_observer,  # +1 for JSON-LD build step
    )

    result = {
        "schema": args.schema,
        "code_url": args.url,
        "results": jsonld_document,
        "enriched_metadata": enriched or {},
    }
    _print_json(result)

def _normalize_property_key(property_name: str) -> Tuple[str, str]:
    """
    Return a tuple of (jsonld_style, entity_style) keys for flexible matching.

    Example:
        "codemeta:readme" -> ("codemeta:readme", "codemeta_readme")
        "codemeta_readme" -> ("codemeta:readme", "codemeta_readme")
        "name"            -> ("name", "name")
    """
    if ":" in property_name:
        jsonld_key = property_name
        entity_key = property_name.replace(":", "_")
    else:
        entity_key = property_name
        jsonld_key = property_name.replace("_", ":")
    return jsonld_key, entity_key

def _collect_property_results(
    schema: str,
    code_url: str,
    jsonld_document: Dict[str, Any],
    enriched_metadata: Dict[str, Any],
    property_name: str,
) -> Dict[str, Any]:
    jsonld_key, _ = _normalize_property_key(property_name)

    matches: List[Dict[str, Any]] = []
    value = jsonld_document.get(jsonld_key)
    if value is not None:
        meta = enriched_metadata.get(jsonld_key, {}) if isinstance(enriched_metadata, dict) else {}
        matches.append(
            {
                "profile": jsonld_document.get("@type", schema),
                "property": jsonld_key,
                "value": value,
                "source": meta.get("source"),
                "confidence": meta.get("confidence"),
                "category": meta.get("category"),
            }
        )

    return {
        "schema": schema,
        "code_url": code_url,
        "property": jsonld_key,
        "matches": matches,
    }

def _extract_property_command(args: argparse.Namespace) -> None:

    jsonld_document, enriched = run_extraction(
        repo_url=args.url,
        schema_name=args.schema,
        access_token=args.token,
        with_enrichment=True,
        schema_class=args.schema_class,
    )

    result = _collect_property_results(
        schema=args.schema,
        code_url=args.url,
        jsonld_document=jsonld_document,
        enriched_metadata=enriched or {},
        property_name=args.property,
    )

    if not result["matches"]:
        message = (
            f"No matches found for property '{args.property}' "
            f"in schema '{args.schema}' for URL '{args.url}'."
        )
        print(message, file=sys.stderr)
        sys.exit(1)

    # Single flat dict: property_name, property_value, source(s), confidence
    first = result["matches"][0]
    source = first.get("source")
    # Keep list when multiple sources contributed; single value when one
    output = {
        "property_name": first["property"],
        "property_value": first["value"],
        "source": source,
        "confidence": first.get("confidence"),
    }
    _print_json(output)

def _fairness_command(args: argparse.Namespace) -> None:
    """
    Compute a FAIRness report for a repository and print JSON.
    """
    jsonld_document, fairness_report = run_fairness_assessment(
        repo_url=args.url,
        schema=args.schema,
        access_token=args.token,
        with_enrichment=False,
    )

    result = {
        "schema": args.schema,
        "code_url": args.url,
        "results": jsonld_document,
        "fairness": asdict(fairness_report),
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
        help="Schema to analyze against (e.g. masmp, CODEMETA).",
    )
    extract_parser.add_argument(
        "--schema-class",
        default="SoftwareApplication",
        help="Schema class to use (default: SoftwareApplication).",
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
    extract_parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Show progress bars for extraction steps (requires tqdm).",
    )
    extract_parser.set_defaults(func=_extract_command)

    # comet-rs extract_property {GIT_URL} {PROPERTY_NAME} [--schema SCHEMA]
    extract_prop_parser = subparsers.add_parser(
        "extract_property",
        help=(
            "Extract a single property (value and source) for a repository. "
            "Schema defaults to masmp if not given."
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
        default="masmp",
        help="Schema to use (default: masmp).",
    )
    extract_prop_parser.add_argument(
        "--schema-class",
        default="SoftwareApplication",
        help="Schema class to use (default: SoftwareApplication).",
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
        "schema",
        help="Schema to analyze against (e.g. masmp, CODEMETA).",
    )
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
            args.token = os.environ.get("GITLAB_TOKEN") or os.environ.get("GITHUB_TOKEN")
        else:
            args.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITLAB_TOKEN")

    try:
        args.func(args)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()