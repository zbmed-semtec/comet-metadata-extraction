from dataclasses import asdict
import pytest
from app.layer_3.evaluators.fairness_evaluator import evaluate_fairness, FairnessReport, _has_doi, _looks_like_semver

def test_fairness_empty_document_has_ten_zero_indicators_and_model_version():
    r = evaluate_fairness({}, "CODEMETA")
    assert isinstance(r, FairnessReport); assert len(r.indicators) == 10
    assert r.overall_score == r.findable == r.accessible == r.interoperable == r.reusable == 0
    assert r.model_version == "1.0.0"

def test_fairness_scores_populated_fields_and_masmp_profile():
    doc = {"maSMP:SoftwareSourceCode": {"description":"d", "identifier":"10.1/x", "codeRepository":"u", "softwareVersion":"1.2.3", "documentation":"d", "license":"MIT", "citation":"c", "keywords":["k"], "softwareRequirements":"r"}}
    r = evaluate_fairness(doc, "maSMP")
    assert r.findable > 0 and r.accessible == 1 and r.interoperable == 1 and r.reusable > 0
    assert {i.id for i in r.indicators} == {f"bp{i}_" + x for i,x in [(1,"description_present"),(2,"persistent_identifier"),(3,"download_url_available"),(4,"semver_like_version"),(5,"usage_documentation"),(6,"license_declared"),(7,"explicit_citation"),(8,"software_metadata"),(9,"install_instructions"),(10,"software_requirements")]}

def test_fairness_helpers_handle_edge_values():
    assert _has_doi("https://doi.org/10.123/x") and _has_doi(["10.1/x"])
    assert not _has_doi(None) and _has_doi([]) is False
    assert _looks_like_semver("1.2.3-alpha") and not _looks_like_semver("v1.2.3") and not _looks_like_semver(None)
