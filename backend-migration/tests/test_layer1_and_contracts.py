import dataclasses
import pytest
from app.layer_1.metadata_collector.metadata_collector import MetadataCollector, MetadataProperty
from app.layer_1.schemas.base_schema import BaseSchema
from app.layer_1.schemas.base_schema_registry import BaseSchemaRegistry
from app.layer_2.contracts import ExtractionContext, ExtractionState, ExtractionPipeline

def test_collector_appends_records_and_selects_highest_confidence():
    c = MetadataCollector(); c.collect("low", "p", 1, .2); c.collect("high", "p", 2, .9)
    assert [r.source for r in c.get("p")] == ["low", "high"]
    assert c.get_most_confident("p").property_value == 2
    assert c.get("missing") == {}
    assert c.get_most_confident("missing") is None

def test_metadata_property_defaults_and_iteration_over_collector_data():
    p = MetadataProperty("s", "n", "v")
    assert p.confidence == 1.0
    c = MetadataCollector(); c.collect("s", "n", "v")
    assert list(c.data) == ["n"] and list(c.data["n"])[0] == p

def test_context_is_frozen_but_state_is_mutable():
    schema = type("S", (), {})()
    ctx = ExtractionContext("u", "d", schema, token := "github.com", "t")
    with pytest.raises(dataclasses.FrozenInstanceError): ctx.repo_url = "x"
    st = ExtractionState(MetadataCollector()); st.data["x"] = 1; st.errors["e"] = ValueError()
    assert st.data["x"] == 1 and isinstance(st.errors["e"], ValueError)

def test_context_token_is_optional():
    ctx = ExtractionContext("u", "d", object())
    assert ctx.access_token is None and ctx.platform is None

def test_base_schema_and_registry_are_abstract_contracts():
    assert BaseSchema.__abstractmethods__ == {"get_schema_name", "get_class_name", "get_property_list", "get_categories_of", "get_prefixes", "get_uri", "build_context"}
    assert BaseSchemaRegistry.__abstractmethods__ == {"load", "get", "list"}

def test_pipeline_is_frozen_tuple_of_steps():
    p = ExtractionPipeline(steps=())
    assert p.steps == ()
    with pytest.raises(dataclasses.FrozenInstanceError): p.steps = (1,)
