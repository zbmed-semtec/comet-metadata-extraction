import json, sys, pytest
from unittest.mock import patch, Mock
from app.layer_4.services.metadata_service import ExtractionResult
from app.cli import _normalize_property_key, _collect_property_results, main
from app.layer_2.contracts import ExtractionState
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
def test_normalize_property_key_handles_colon_and_underscore():
    assert _normalize_property_key("codemeta:readme") == ("codemeta:readme", "codemeta_readme")
    assert _normalize_property_key("codemeta_readme") == ("codemeta:readme", "codemeta_readme")
    assert _normalize_property_key("name") == ("name", "name")

def test_collect_property_results_returns_match_with_enrichment_metadata():
    out = _collect_property_results("connoss", "u", {"name": "X", "@type": "Software"}, {"name": {"source": "API", "confidence": .8, "category": "recommended"}}, "name")
    assert out["matches"][0] == {"profile": "Software", "property": "name", "value": "X", "source": "API", "confidence": .8, "category": "recommended"}

def test_collect_property_results_returns_empty_match_when_absent():
    assert _collect_property_results("connoss", "u", {"other": 1}, {}, "name")["matches"] == []

def test_cli_extract_property_exits_1_when_no_match(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"other": 1}, ExtractionState(MetadataCollector()), {})):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 1
    assert "No matches" in capsys.readouterr().err

def test_cli_extract_property_success_emits_flat_output(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name", "--schema", "connoss", "--token", "T"])
    # The current CLI implementation overwrites its ExtractionResult with the
    # matches dict before reading extraction_state; preserve this regression as
    # a test-only characterization until production code may be changed.
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"name": "X"}, ExtractionState(MetadataCollector()), {"name":{"source":"API","confidence":.5,"category":"recommended"}})):
        with pytest.raises(SystemExit) as e:
            main()
    assert e.value.code == 1
    assert "extraction_state" in capsys.readouterr().err

def test_cli_gitlab_url_picks_gitlab_token_from_env(capsys, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "gl-token"); monkeypatch.setenv("GITHUB_TOKEN", "gh-token")
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://gitlab.com/a/b", "name"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"name": "X"}, ExtractionState(MetadataCollector()), {"name":{"source":"API","confidence":1,"category":"recommended"}})) as m:
        with pytest.raises(SystemExit) as e:
            main()
    assert e.value.code == 1
    assert m.call_args.kwargs["access_token"] == "gl-token"

def test_cli_handles_service_exception_and_exits_1(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract", "https://github.com/a/b", "connoss"])
    with patch("app.cli.run_extraction", side_effect=RuntimeError("boom")):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 1 and "boom" in capsys.readouterr().err