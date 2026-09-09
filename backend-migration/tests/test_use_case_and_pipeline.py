import pytest
from unittest.mock import Mock
from app.layer_2.use_cases.extract_metadata import ExtractMetadataUseCase, ExtractMetadataResult
from app.layer_2.contracts import ExtractionContext, ExtractionState, ExtractionPipeline, ExtractionStep
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
from app.layer_1.schemas.base_schema import BaseSchema

class _StubSchema(BaseSchema):
    def __init__(self, props=None, uris=None):
        self._p = props or ["name", "description"]; self._u = uris or {p: f"u://{p}" for p in self._p}
    def get_schema_name(self): return "s"
    def get_class_name(self): return "C"
    def get_property_list(self): return self._p
    def get_categories_of(self, property_name): return "recommended"
    def get_prefixes(self): return {}
    def get_uri(self, property_name): return self._u[property_name]
    def build_context(self): return {"@vocab": "u://"}

def test_use_case_executes_pipeline_and_returns_jsonld_and_result_shape(context):
    builder = Mock()
    builder.build_jsonld = Mock(return_value={"@type": "C", "name": "X"})
    composer = Mock(); runner = Mock()
    composer.compose = Mock(return_value=ExtractionPipeline(steps=()))
    runner.run = Mock(side_effect=lambda p, c, s: s)
    uc = ExtractMetadataUseCase(builder, composer, runner, MetadataCollector())
    r = uc.execute("https://github.com/x/y", context.schema, "t")
    assert isinstance(r, ExtractMetadataResult)
    assert r.jsonld_document == {"@type": "C", "name": "X"}
    assert r.extraction_metadata == {}
    assert composer.compose.called and runner.run.called and builder.build_jsonld.called

def test_use_case_reports_progress_when_no_single_property_and_skips_when_set(context):
    events = []
    def cb(step, status): events.append((step, status))
    uc = ExtractMetadataUseCase(Mock(), Mock(return_value=ExtractionPipeline(steps=())), Mock(side_effect=lambda p,c,s:s))
    uc.execute("https://github.com/x/y", context.schema, progress_callback=cb)
    assert events == [("pipeline","started"),("pipeline","completed"),("jsonld_build","started"),("jsonld_build","completed")]
    events.clear()
    uc.execute("https://github.com/x/y", context.schema, single_property="name", progress_callback=cb)
    assert events == []

def test_use_case_platform_must_be_non_empty(context):
    uc = ExtractMetadataUseCase(Mock(), Mock(), Mock())
    with pytest.raises(ValueError):
        uc.execute("", context.schema)

def test_compose_only_runs_for_applicable_platform_and_priority_order():
    from app.layer_2.extraction_plugin import ExtractionPlugin
    from app.layer_2.extraction_plugin_manager import ExtractionPluginManager
    from app.layer_2.contracts import ExtractionContext
    mgr = ExtractionPluginManager()
    class P(ExtractionPlugin):
        name="p"; extracts={"u://name"}; platforms={"github.com"}; priority_level=10
        def extract(self, c, s): return s
    mgr._register(P); mgr._on_plugin_registration(P)
    composer = mgr; ctx = ExtractionContext("u", "d", _StubSchema(["name"]), "github.com")
    from app.layer_3.composers.plugin_pipeline_composer import PluginPipelineComposer
    ppc = PluginPipelineComposer(); ppc.plugin_manager = mgr
    pipe = ppc.compose(ctx)
    assert [s.name for s in pipe.steps] == ["p"]

def test_get_returns_none_for_unknown_plugin():
    from app.layer_2.plugin_manager import PluginManager
    assert PluginManager().get("nope") is None
