import json, sys, pytest
from unittest.mock import patch, Mock
from app.layer_4.services.metadata_service import ExtractionResult
from app.cli import _property_key_candidates, _collect_property_results, main
from app.layer_2.contracts import ExtractionState
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector

def test_property_key_candidates_handles_colon_and_underscore():
    assert _property_key_candidates("codemeta:readme")[0] == "readme"
    assert "codemeta:readme" in _property_key_candidates("codemeta:readme")
    assert _property_key_candidates("codemeta_readme")[0] == "codemeta_readme"
    assert _property_key_candidates("name") == ["name"]

def test_collect_property_results_returns_match_with_enrichment_metadata():
    out = _collect_property_results("connoss", "u", {"name": "X", "@type": "Software"}, {"name": {"source": "API", "confidence": .8, "category": "recommended"}}, "name")
    assert out["matches"][0] == {"profile": "Software", "property": "name", "value": "X", "source": "API", "confidence": .8, "category": "recommended"}

def test_collect_property_results_normalizes_prefixed_property():
    out = _collect_property_results("connoss", "u", {"readme": "R", "@type": "Software"}, {"readme": {"source": "API", "confidence": .9}}, "codemeta:readme")
    assert out["matches"][0]["value"] == "R"
    assert out["matches"][0]["source"] == "API"

def test_collect_property_results_returns_empty_match_when_absent():
    assert _collect_property_results("connoss", "u", {"other": 1}, {}, "name")["matches"] == []

def test_cli_extract_property_exits_1_when_no_match(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"other": 1}, ExtractionState(MetadataCollector()), {})):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 1
    assert "No matches" in capsys.readouterr().err

def test_cli_extract_property_exits_2_when_unknown_property(capsys, monkeypatch):
    from app.layer_2.errors import UnknownPropertyError
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "bogus_property"])
    with patch("app.cli.run_extraction", side_effect=UnknownPropertyError("no plugin declares it")):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 2
    assert "Unknown property" in capsys.readouterr().err

def test_cli_extract_property_rate_limit_exits_1_with_real_error(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name"])
    with patch("app.cli.run_extraction", side_effect=RuntimeError("403 Client Error: rate limit exceeded")):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 1
    assert "rate limit" in capsys.readouterr().err
    assert "Unknown property" not in capsys.readouterr().err

def test_cli_extract_property_null_value_emits_null_and_errors_exit_0(capsys, monkeypatch):
    state = ExtractionState(MetadataCollector())
    state.errors["fetch_repository"] = Exception("403 rate limit exceeded")
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"name": None}, state, {})):
        main()
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["property_value"] is None
    assert "rate limit exceeded" in captured.err
    # exit code 0: no SystemExit raised

def test_cli_extract_property_no_match_with_errors_mentions_errors(capsys, monkeypatch):
    state = ExtractionState(MetadataCollector())
    state.errors["fetch_repository"] = Exception("403 rate limit exceeded")
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "other"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({}, state, {})):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 1
    err = capsys.readouterr().err
    assert "No matches" in err and "rate limit exceeded" in err

def test_cli_extract_property_success_emits_flat_output(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name", "--schema", "connoss", "--token", "T"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"name": "X"}, ExtractionState(MetadataCollector()), {"name":{"source":"API","confidence":.5,"category":"recommended"}})) as m:
        main()
    assert m.call_args.kwargs["fairness_assessment"] is False
    out = json.loads(capsys.readouterr().out)
    assert out == {"property_name": "name", "property_value": "X", "source": "API", "confidence": 0.5}

def test_cli_extract_property_success_does_not_crash_on_extraction_errors(capsys, monkeypatch):
    state = ExtractionState(MetadataCollector())
    state.errors["step"] = Exception("boom")
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://github.com/a/b", "name"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"name": "X"}, state, {"name": {"source": "API"}})):
        main()
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["property_value"] == "X"
    assert "boom" in captured.err

def test_cli_gitlab_url_picks_gitlab_token_from_env(capsys, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "gl-token"); monkeypatch.setenv("GITHUB_TOKEN", "gh-token")
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract_property", "https://gitlab.com/a/b", "name"])
    with patch("app.cli.run_extraction", return_value=ExtractionResult({"name": "X"}, ExtractionState(MetadataCollector()), {"name":{"source":"API","confidence":1,"category":"recommended"}})) as m:
        main()
    assert m.call_args.kwargs["access_token"] == "gl-token"

def test_cli_handles_service_exception_and_exits_1(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["comet-rs", "extract", "https://github.com/a/b", "connoss"])
    with patch("app.cli.run_extraction", side_effect=RuntimeError("boom")):
        with pytest.raises(SystemExit) as e: main()
    assert e.value.code == 1 and "boom" in capsys.readouterr().err
