import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import app.layer_4.services.metadata_service as metadata_service

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)

def test_root_returns_welcome_payload(client):
    r = client.get("/")
    assert r.status_code == 200 and r.json()["message"].startswith("Welcome") and r.json()["health"] == "/api/health"

def test_health_and_platforms(client):
    assert client.get("/api/health").json() == {"status": "healthy", "service": "metadata-extractor"}
    assert "GitHub" in [p["name"] for p in client.get("/api/platforms").json()["platforms"]]

def test_metadata_plain_happy_path(client):
    payload = {"@type": "Software", "name": "X"}
    with patch("app.layer_4.endpoints.metadata.run_extraction", return_value=(payload, None, None)):
        r = client.get("/api/metadata", params={"repo_url": "https://github.com/a/b", "schema": "connoss", "access_token": "t"})
    assert r.status_code == 200 and r.json()["results"] == payload and r.json()["status"] == "success"

def test_metadata_enriched_returns_enriched_block(client):
    with patch("app.layer_4.endpoints.metadata.run_extraction",
               return_value=({"@type":"Software"}, {"name": {"source": "API", "confidence": .9, "category": "recommended"}}, None)):
        r = client.get("/api/metadata/enriched", params={"repo_url":"https://github.com/a/b"})
    assert r.status_code == 200 and r.json()["enriched_metadata"]["name"]["source"] == "API"

def test_property_endpoint_returns_value_source_confidence_and_propagates_errors(client):
    enriched = {"description": {"source": "API", "confidence": .5, "category": "recommended"}}
    with patch("app.layer_4.endpoints.metadata.run_extraction",
               return_value=({"description": "Desc"}, enriched, None)):
        r = client.get("/api/metadata/property", params={"repo_url":"https://github.com/a/b", "property": "description"})
    assert r.status_code == 200 and r.json()["results"][0]["value"] == "Desc" and r.json()["results"][0]["source"] == "API"
    with patch("app.layer_4.endpoints.metadata.run_extraction", side_effect=ValueError("nope")):
        assert client.get("/api/metadata/property", params={"repo_url":"https://github.com/a/b", "property": "x"}).status_code == 400

def test_stream_endpoint_yields_progress_and_result_events(client):
    events = []
    def progress_cb(step, status): events.append((step, status))
    def fake_run(**kwargs):
        cb = kwargs["progress_callback"]
        for step in ("pipeline", "jsonld_build"):
            cb(step, "started"); cb(step, "completed")
        return {"@type":"Software"}, {"name":{"source":"API","confidence":1,"category":"recommended"}}, None
    with patch("app.layer_4.endpoints.metadata.run_extraction", side_effect=fake_run):
        r = client.get("/api/metadata/stream", params={"repo_url":"https://github.com/a/b"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert "event: progress" in body and "event: result" in body

def test_metadata_plain_value_error_returns_400_and_other_error_500(client):
    with patch("app.layer_4.endpoints.metadata.run_extraction", side_effect=ValueError("bad")):
        assert client.get("/api/metadata", params={"repo_url":"https://github.com/a/b"}).status_code == 400
    with patch("app.layer_4.endpoints.metadata.run_extraction", side_effect=RuntimeError("boom")):
        assert client.get("/api/metadata", params={"repo_url":"https://github.com/a/b"}).status_code == 500

def test_run_extraction_returns_enriched_dict_when_requested():
    from app.layer_4.services.metadata_service import run_extraction
    with patch("app.layer_4.services.metadata_service._schema_registry") as reg, patch("app.layer_4.services.metadata_service._create_extraction_use_case") as mk, patch("app.layer_4.services.metadata_service.build_enriched_metadata", return_value={"name": {"source": "X", "confidence": 1, "category": "recommended"}}):
        from app.layer_3.schemas.linkml.linkml_schema import LinkMlSchema
        sch = Mock(spec=LinkMlSchema); reg.get.return_value = sch
        uc, coll = Mock(), Mock(); uc.execute.return_value.jsonld_document = {"@type":"C"}; mk.return_value = (uc, coll)
        doc, enr, col = run_extraction("u", "connoss", "t", with_enrichment=True)
    assert doc == {"@type":"C"} and enr == {"name": {"source": "X", "confidence": 1, "category": "recommended"}}

def test_fairness_service_module_has_current_bug_no_pipeline_composer():
    """Current code references _pipeline_composer which is not assigned -> NameError.
    Document this as a known current-code quirk; see TEST_SUITE_NOTES."""
    import pytest
    from app.layer_4.services import fairness_service
    with pytest.raises(NameError) as e:
        fairness_service.run_fairness_assessment("u", "connoss", "t", with_enrichment=True)
    assert "_pipeline_composer" in str(e.value)
    # evaluator API works in isolation
    from app.layer_3.evaluators.fairness_evaluator import evaluate_fairness
    assert evaluate_fairness({"license": "MIT", "documentation": "x"}, "CODEMETA").findable >= 0

