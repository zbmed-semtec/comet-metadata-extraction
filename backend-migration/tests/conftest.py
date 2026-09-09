import base64
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock
import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
from app.layer_2.contracts import ExtractionContext, ExtractionState
from app.layer_3.schemas.linkml.linkml_schema_registry import LinkMlSchemaRegistry

@pytest.fixture
def repo_urls():
    return {"github": "https://github.com/acme/widget", "gitlab": "https://gitlab.com/acme/tools/widget", "codeberg": "https://codeberg.org/acme/widget"}

@pytest.fixture
def schema_registry():
    r = LinkMlSchemaRegistry()
    r.load(ROOT / "schemas")
    return r

@pytest.fixture
def connoss_schema(schema_registry):
    return schema_registry.get("connoss", "Software")

@pytest.fixture
def collector():
    c = MetadataCollector()
    c.collect("API", "https://schema.org/name", "Widget", .7)
    c.collect("CFF", "https://schema.org/name", "Better Widget", .95)
    c.collect("API", "https://schema.org/description", "A tool", .9)
    return c

@pytest.fixture
def context(connoss_schema, repo_urls):
    return ExtractionContext(repo_urls["github"], "software", connoss_schema, "github.com", "secret")

@pytest.fixture
def state():
    return ExtractionState(MetadataCollector())

class FakeResponse:
    def __init__(self, payload, status_code=200, text=None):
        self._payload, self.status_code = payload, status_code
        self.text = text if text is not None else __import__("json").dumps(payload)
        self.ok = 200 <= status_code < 400
    def json(self): return self._payload
    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            r = requests.exceptions.HTTPError(f"HTTP {self.status_code}"); r.response = self; raise r

@pytest.fixture
def fake_response():
    return FakeResponse
