from app.layer_3.plugins.llm.confidence import normalize_confidence
from app.layer_3.plugins.llm.prompt import build_prompt
from app.layer_3.plugins.llm.extraction import (
    LlmBuildInstructionsExtractor,
    LlmIntendedUseExtractor,
    LlmNameExtractor,
    extract_json,
    normalize_readme_property,
)
from app.layer_3.plugins.llm.retrieval import retrieve_top_chunks


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

    def get_most_confident(self, property_name):
        matches = [call for call in self.calls if call["property_name"] == property_name]
        return max(matches, key=lambda call: call["confidence"]) if matches else None


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


class _TestableLlmBuildInstructionsExtractor(LlmBuildInstructionsExtractor):
    name = "test-llm-build-instructions-extractor"
    platforms = {"github"}

    def get_client(self, context, state):
        return context.client


class _TestableLlmIntendedUseExtractor(LlmIntendedUseExtractor):
    name = "test-llm-intended-use-extractor"
    platforms = {"github"}

    def get_client(self, context, state):
        return context.client


class _FakeSchema:
    def __init__(self, properties):
        self._properties = properties

    def get_property_list(self):
        return list(self._properties)

    def get_uri(self, property_name):
        return self._properties[property_name]


def test_build_prompt_includes_rules_schema_and_context():
    prompt = build_prompt("license", "[Rank 1] MIT License")

    assert "You are extracting 'license'" in prompt
    assert "Expected value shape:" in prompt
    assert "No guessing. Return JSON only" in prompt
    assert "[Rank 1] MIT License" in prompt


def test_build_prompt_uses_intended_use_specific_rules():
    prompt = build_prompt(
        "intendedUse",
        "[Rank 1] Use this tool to extract repository metadata.",
    )

    assert "tasks or use cases" in prompt
    assert "Do not infer uses from features" in prompt
    assert "one concise string" in prompt


def test_extract_json_parses_fenced_json():
    result = extract_json("```json\n{\"value\": \"MIT\", \"confidence\": 0.9}\n```")

    assert result["value"] == "MIT"
    assert result["confidence"] == 0.9


def test_extract_json_returns_empty_result_for_invalid_text():
    result = extract_json("not json")

    assert result["value"] is None
    assert result["evidence"] is None
    assert result["confidence"] == 0.0


def test_normalize_confidence_caps_llm_source_at_point_seven():
    assert normalize_confidence(0.9) == 0.7
    assert normalize_confidence(0.4) == 0.4


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
            "confidence": 0.7,
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


def test_normalize_readme_property_enforces_url_and_deduplicates_lists():
    assert normalize_readme_property("See https://example.org/build.", "url") == "https://example.org/build"
    assert normalize_readme_property("Run make", "url") is None
    assert normalize_readme_property(["Tool", "tool", " CLI "], "string_list") == ["Tool", "CLI"]


def test_llm_build_instructions_collects_schema_mapped_fallback(monkeypatch):
    extractor = _TestableLlmBuildInstructionsExtractor()
    state = _FakeState()
    context = _FakeContext()
    context.client = _FakeClient([_FakeReadmeFile("## Build\nInstructions: https://example.org/build")])
    context.schema = _FakeSchema(
        {"buildInstructions": "https://discovery.biothings.io/ns/maSMP/buildInstructions"}
    )

    captured = {}

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.settings.llm_enabled", True)
    monkeypatch.setattr(
        "app.layer_3.plugins.llm.extraction.resolve_model_config",
        lambda: ("ollama", "ollama", "test-model", "http://localhost:11434"),
    )

    def _fake_extract_property(property_name, readme_text, provider, model, base_url, top_k=5):
        captured["property_name"] = property_name
        return {"value": "https://example.org/build", "confidence": 0.81}

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.extract_property", _fake_extract_property)

    extractor.extract(context, state)

    assert captured["property_name"] == "buildInstructions"
    assert state.metadata_collector.calls == [
        {
            "source": "LLM README",
            "property_name": "https://discovery.biothings.io/ns/maSMP/buildInstructions",
            "property_value": "https://example.org/build",
            "confidence": 0.7,
        }
    ]


def test_llm_intended_use_collects_masmp_schema_value(monkeypatch):
    extractor = _TestableLlmIntendedUseExtractor()
    state = _FakeState()
    context = _FakeContext()
    context.client = _FakeClient(
        [_FakeReadmeFile("Use this tool to extract metadata from software repositories.")]
    )
    context.schema = _FakeSchema(
        {"intendedUse": "https://discovery.biothings.io/ns/maSMP/intendedUse"}
    )

    monkeypatch.setattr("app.layer_3.plugins.llm.extraction.settings.llm_enabled", True)
    monkeypatch.setattr(
        "app.layer_3.plugins.llm.extraction.resolve_model_config",
        lambda: ("ollama", "ollama", "test-model", "http://localhost:11434"),
    )

    captured = {}

    def _fake_extract_property(property_name, readme_text, provider, model, base_url, top_k=5):
        captured["property_name"] = property_name
        return {
            "value": "Extract metadata from software repositories",
            "confidence": 0.82,
        }

    monkeypatch.setattr(
        "app.layer_3.plugins.llm.extraction.extract_property",
        _fake_extract_property,
    )

    extractor.extract(context, state)

    assert captured["property_name"] == "intendedUse"
    assert state.metadata_collector.calls == [
        {
            "source": "LLM README",
            "property_name": "https://discovery.biothings.io/ns/maSMP/intendedUse",
            "property_value": "Extract metadata from software repositories",
            "confidence": 0.7,
        }
    ]


def test_llm_intended_use_supports_connoss_schema_uri():
    assert "https://schema.org/intendedUse" in LlmIntendedUseExtractor.extracts
