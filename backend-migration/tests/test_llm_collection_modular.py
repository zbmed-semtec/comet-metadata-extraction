from app.layer_3.plugins.llm.collection import build_prompt, extract_json, retrieve_top_chunks
from app.layer_3.plugins.llm.extraction import LlmNameExtractor


class _FakeReadmeFile:
    def __init__(self, content: str):
        self._content = content

    def get_content(self):
        return self._content


class _FakeClient:
    def __init__(self, files):
        self._files = files

    def get_readme_candidate_files(self):
        return self._files


class _FakeCollector:
    def __init__(self):
        self.calls = []

    def collect(self, source, property_name, property_value, confidence=1.0):
        self.calls.append(
            {
                "source": source,
                "property_name": property_name,
                "property_value": property_value,
                "confidence": confidence,
            }
        )


class _FakeState:
    def __init__(self):
        self.metadata_collector = _FakeCollector()


class _FakeContext:
    pass


class _TestableLlmNameExtractor(LlmNameExtractor):
    name = "test-llm-name-extractor"
    platforms = {"github"}

    def get_client(self, context, state):
        return context.client


def test_build_prompt_includes_rules_schema_and_context():
    prompt = build_prompt("license", "[Rank 1] MIT License")

    assert "You are extracting 'license'" in prompt
    assert "Expected value shape:" in prompt
    assert "No guessing. Return JSON only" in prompt
    assert "[Rank 1] MIT License" in prompt


def test_extract_json_parses_fenced_json():
    result = extract_json("```json\n{\"value\": \"MIT\", \"confidence\": 0.9}\n```")

    assert result["value"] == "MIT"
    assert result["confidence"] == 0.9


def test_extract_json_returns_empty_result_for_invalid_text():
    result = extract_json("not json")

    assert result["value"] is None
    assert result["evidence"] is None
    assert result["confidence"] == 0.0


def test_retrieve_top_chunks_prioritizes_keyword_matches_when_embeddings_disabled():
    index = {
        "records": [
            {"heading": "Installation", "content": "Run pip install package", "full_text": "Installation\nRun pip install package"},
            {"heading": "Overview", "content": "General project notes", "full_text": "Overview\nGeneral project notes"},
        ],
        "embedding_enabled": False,
        "embeddings": None,
        "model": None,
    }

    top_chunks = retrieve_top_chunks(index, "installation", top_k=1)

    assert len(top_chunks) == 1
    assert top_chunks[0]["heading"] == "Installation"
    assert top_chunks[0]["rank"] == 1


def test_llm_name_extractor_uses_readme_text_and_collects_result(monkeypatch):
    extractor = _TestableLlmNameExtractor()
    state = _FakeState()
    context = _FakeContext()
    context.client = _FakeClient([])
    fake_files = [_FakeReadmeFile("# Demo Project"), _FakeReadmeFile("The project is called Example App.")]

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.settings.llm_enabled", True)
    monkeypatch.setattr(context, "client", _FakeClient(fake_files))

    captured = {}

    def _fake_extract_property(property_name, readme_text, provider, model, base_url, top_k=5):
        captured["property_name"] = property_name
        captured["readme_text"] = readme_text
        captured["provider"] = provider
        captured["model"] = model
        captured["base_url"] = base_url
        captured["top_k"] = top_k
        return {"value": "Example App", "confidence": 0.87}

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.extract_property", _fake_extract_property)
    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.resolve_model_config", lambda: ("active", "ollama", "phi4-mini", "http://localhost:11434"))

    result_state = extractor.extract(context, state)

    assert result_state is state
    assert captured["property_name"] == "name"
    assert "# Demo Project" in captured["readme_text"]
    assert "The project is called Example App." in captured["readme_text"]
    assert captured["top_k"] == 5
    assert state.metadata_collector.calls == [
        {
            "source": "LLM README",
            "property_name": "https://schema.org/name",
            "property_value": "Example App",
            "confidence": 0.87,
        }
    ]


def test_llm_name_extractor_short_circuits_when_disabled(monkeypatch):
    extractor = _TestableLlmNameExtractor()
    state = _FakeState()
    context = _FakeContext()
    context.client = _FakeClient([_FakeReadmeFile("# Demo Project")])

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.settings.llm_enabled", False)

    called = {"extract_property": False}

    def _fail_extract_property(*args, **kwargs):
        called["extract_property"] = True
        raise AssertionError("extract_property should not run when LLM is disabled")

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.extract_property", _fail_extract_property)

    result_state = extractor.extract(context, state)

    assert result_state is state
    assert called["extract_property"] is False
    assert state.metadata_collector.calls == []
