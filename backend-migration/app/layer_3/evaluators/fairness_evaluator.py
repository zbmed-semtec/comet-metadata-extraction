"""
FAIRness evaluator – computes FAIR scores from JSON-LD and SoftwareMetadata.
"""
from collections import defaultdict
import re
from typing import Any, Dict, List, Literal
from dataclasses import dataclass

FairPrinciple = Literal["F", "A", "I", "R"]

@dataclass(frozen=True)
class FairnessIndicator:
    """
    Single FAIRness indicator result.

    Each indicator contributes a score to one FAIR principle.
    """

    id: str
    title: str
    principle: FairPrinciple
    score: float
    details: Dict[str, Any]


@dataclass(frozen=True)
class FairnessReport:
    """
    Aggregated FAIRness assessment for a repository.
    """

    overall_score: float
    findable: float
    accessible: float
    interoperable: float
    reusable: float
    indicators: List[FairnessIndicator]
    model_version: str = "1.0.0"


def _bool_to_score(value: bool) -> float:
    return 1.0 if value else 0.0


def _get_profile_view(jsonld_document: Dict[str, Any], schema: str) -> Dict[str, Any]:
    if schema == "maSMP":
        profile = jsonld_document.get("maSMP:SoftwareSourceCode")
        if isinstance(profile, dict):
            return profile
        return {}
    return jsonld_document


_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z\.-]+)?$")


def _looks_like_semver(version: str | None) -> bool:
    return isinstance(version, str) and bool(_SEMVER_PATTERN.match(version.strip()))


def _has_doi(identifiers: Any) -> bool:
    if isinstance(identifiers, str):
        values = [identifiers]
    elif isinstance(identifiers, list):
        values = identifiers
    else:
        return False
    return any(isinstance(v, str) and ("doi.org" in v or v.startswith("10.")) for v in values)


def evaluate_fairness(jsonld_document: Dict[str, Any]) -> FairnessReport:
    indicators: List[FairnessIndicator] = []

    has_description = bool(jsonld_document.get("description") or jsonld_document.get("readme"))
    indicators.append(FairnessIndicator(
        id="bp1_description_present",
        title="Description / README available",
        principle="F",
        score=_bool_to_score(has_description),
        details={
            "description_present": bool(jsonld_document.get("description")),
            "readme_present": bool(jsonld_document.get("readme")),
        },
    ))

    identifiers = jsonld_document.get("identifier")
    indicators.append(FairnessIndicator(
        id="bp2_persistent_identifier",
        title="Persistent identifier (e.g. DOI) available",
        principle="F",
        score=_bool_to_score(_has_doi(identifiers)),
        details={"identifier": identifiers},
    ))

    has_download = bool(jsonld_document.get("codeRepository") or jsonld_document.get("downloadUrl"))
    indicators.append(FairnessIndicator(
        id="bp3_download_url_available",
        title="Download URL / code repository available",
        principle="A",
        score=_bool_to_score(has_download),
        details={
            "codeRepository": jsonld_document.get("codeRepository"),
            "downloadUrl": jsonld_document.get("downloadUrl"),
        },
    ))

    version_fields = [jsonld_document.get("softwareVersion"), jsonld_document.get("latestReleaseVersion")]
    indicators.append(FairnessIndicator(
        id="bp4_semver_like_version",
        title="Version field resembles semantic versioning",
        principle="A",
        score=_bool_to_score(any(_looks_like_semver(v) for v in version_fields)),
        details={"version_fields": version_fields},
    ))

    usage_keys = ["documentation", "developerDocumentation", "userDocumentation", "softwareHelp"]
    indicators.append(FairnessIndicator(
        id="bp5_usage_documentation",
        title="Usage / user documentation available",
        principle="I",
        score=_bool_to_score(any(key in jsonld_document for key in usage_keys)),
        details={"keys_checked": usage_keys},
    ))

    indicators.append(FairnessIndicator(
        id="bp6_license_declared",
        title="License is declared",
        principle="R",
        score=_bool_to_score(bool(jsonld_document.get("license"))),
        details={"license": jsonld_document.get("license")},
    ))

    has_citation = bool(jsonld_document.get("citation") or jsonld_document.get("referencePublication"))
    indicators.append(FairnessIndicator(
        id="bp7_explicit_citation",
        title="Explicit citation information available",
        principle="R",
        score=_bool_to_score(has_citation),
        details={
            "citation": jsonld_document.get("citation"),
            "referencePublication": jsonld_document.get("referencePublication"),
        },
    ))

    has_software_metadata = bool(jsonld_document.get("keywords") or jsonld_document.get("programmingLanguage"))
    indicators.append(FairnessIndicator(
        id="bp8_software_metadata",
        title="Software metadata (keywords / language) available",
        principle="F",
        score=_bool_to_score(has_software_metadata),
        details={
            "keywords": jsonld_document.get("keywords"),
            "programmingLanguage": jsonld_document.get("programmingLanguage"),
        },
    ))

    install_keys = ["installUrl", "buildInstructions"]
    indicators.append(FairnessIndicator(
        id="bp9_install_instructions",
        title="Installation instructions available",
        principle="R",
        score=_bool_to_score(any(key in jsonld_document for key in install_keys)),
        details={"keys_checked": install_keys},
    ))

    indicators.append(FairnessIndicator(
        id="bp10_software_requirements",
        title="Software requirements specified",
        principle="R",
        score=_bool_to_score(bool(jsonld_document.get("softwareRequirements"))),
        details={"softwareRequirements": jsonld_document.get("softwareRequirements")},
    ))

    scores_by_principle: Dict[FairPrinciple, List[float]] = defaultdict(list)
    multi_principle_mapping: Dict[str, List[FairPrinciple]] = {
        "bp5_usage_documentation": ["I", "R"],
        "bp8_software_metadata": ["F", "R"],
    }
    for indicator in indicators:
        for principle in multi_principle_mapping.get(indicator.id, [indicator.principle]):
            scores_by_principle[principle].append(indicator.score)

    _avg = lambda values: sum(values) / len(values) if values else 0.0
    f_score, a_score, i_score, r_score = (
        _avg(scores_by_principle.get("F", [])),
        _avg(scores_by_principle.get("A", [])),
        _avg(scores_by_principle.get("I", [])),
        _avg(scores_by_principle.get("R", [])),
    )
    non_zero = [s for s in [f_score, a_score, i_score, r_score] if s > 0]
    overall = _avg(non_zero) if non_zero else 0.0

    return FairnessReport(
        overall_score=overall,
        findable=f_score,
        accessible=a_score,
        interoperable=i_score,
        reusable=r_score,
        indicators=indicators,
    )


def evaluate_fairness_from_metadata(metadata: "SoftwareMetadata") -> FairnessReport:
    indicators: List[FairnessIndicator] = []
    indicators.append(FairnessIndicator(id="bp1_description_present", title="Description / README available", principle="F", score=_bool_to_score(bool(metadata.description or metadata.codemeta_readme)), details={"description_present": bool(metadata.description), "codemeta_readme_present": bool(metadata.codemeta_readme)}))
    identifier_values: List[str] = []
    if metadata.identifier:
        identifier_values.extend(metadata.identifier)
    if metadata.doi:
        identifier_values.append(metadata.doi)
    if metadata.codemeta_referencePublication and metadata.codemeta_referencePublication.id:
        identifier_values.append(metadata.codemeta_referencePublication.id)
    indicators.append(FairnessIndicator(id="bp2_persistent_identifier", title="Persistent identifier (e.g. DOI) available", principle="F", score=_bool_to_score(_has_doi(identifier_values)), details={"identifier": identifier_values}))
    indicators.append(FairnessIndicator(id="bp3_download_url_available", title="Download URL / code repository available", principle="A", score=_bool_to_score(bool(metadata.codeRepository or metadata.downloadUrl)), details={"codeRepository": metadata.codeRepository, "downloadUrl": metadata.downloadUrl}))
    version_fields = [metadata.softwareVersion, metadata.version]
    indicators.append(FairnessIndicator(id="bp4_semver_like_version", title="Version field resembles semantic versioning", principle="A", score=_bool_to_score(any(_looks_like_semver(v) for v in version_fields)), details={"version_fields": version_fields}))
    has_usage_docs = bool(metadata.documentation or metadata.masmp_developerDocumentation or metadata.masmp_userDocumentation or metadata.masmp_learningResource)
    indicators.append(FairnessIndicator(id="bp5_usage_documentation", title="Usage / user documentation available", principle="I", score=_bool_to_score(has_usage_docs), details={"documentation": bool(metadata.documentation), "masmp_developerDocumentation": bool(metadata.masmp_developerDocumentation), "masmp_userDocumentation": bool(metadata.masmp_userDocumentation), "masmp_learningResource": bool(metadata.masmp_learningResource)}))
    indicators.append(FairnessIndicator(id="bp6_license_declared", title="License is declared", principle="R", score=_bool_to_score(bool(metadata.license)), details={"license": metadata.license.dict(exclude_none=True) if metadata.license else None}))
    has_citation = bool(metadata.citation or metadata.codemeta_referencePublication)
    indicators.append(FairnessIndicator(id="bp7_explicit_citation", title="Explicit citation information available", principle="R", score=_bool_to_score(has_citation), details={"citation": metadata.citation, "referencePublication": metadata.codemeta_referencePublication.dict(exclude_none=True) if metadata.codemeta_referencePublication else None}))
    has_software_metadata = bool(metadata.keywords or metadata.programmingLanguage)
    indicators.append(FairnessIndicator(id="bp8_software_metadata", title="Software metadata (keywords / language) available", principle="F", score=_bool_to_score(has_software_metadata), details={"keywords": metadata.keywords, "programmingLanguage": metadata.programmingLanguage}))
    has_install = bool(metadata.masmp_installInstructions or metadata.codemeta_buildInstructions)
    indicators.append(FairnessIndicator(id="bp9_install_instructions", title="Installation instructions available", principle="R", score=_bool_to_score(has_install), details={"masmp_installInstructions": bool(metadata.masmp_installInstructions), "codemeta_buildInstructions": bool(metadata.codemeta_buildInstructions)}))
    indicators.append(FairnessIndicator(id="bp10_software_requirements", title="Software requirements specified", principle="R", score=_bool_to_score(bool(metadata.softwareRequirements)), details={"softwareRequirements": metadata.softwareRequirements}))

    scores_by_principle: Dict[FairPrinciple, List[float]] = defaultdict(list)
    multi_principle_mapping: Dict[str, List[FairPrinciple]] = {"bp5_usage_documentation": ["I", "R"], "bp8_software_metadata": ["F", "R"]}
    for indicator in indicators:
        for principle in multi_principle_mapping.get(indicator.id, [indicator.principle]):
            scores_by_principle[principle].append(indicator.score)
    _avg = lambda values: sum(values) / len(values) if values else 0.0
    f_score, a_score, i_score, r_score = _avg(scores_by_principle.get("F", [])), _avg(scores_by_principle.get("A", [])), _avg(scores_by_principle.get("I", [])), _avg(scores_by_principle.get("R", []))
    non_zero = [s for s in [f_score, a_score, i_score, r_score] if s > 0]
    overall = _avg(non_zero) if non_zero else 0.0
    return FairnessReport(overall_score=overall, findable=f_score, accessible=a_score, interoperable=i_score, reusable=r_score, indicators=indicators)


__all__ = ["evaluate_fairness", "evaluate_fairness_from_metadata"]
