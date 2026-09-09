from pydantic import BaseModel
from app.layer_3.builders.jsonld_builder import JSONLDBuilder
from app.layer_4.builders.enriched_metadata import build_enriched_metadata

def test_linkml_registry_loads_current_yaml_schemas_and_lookup(connoss_schema, schema_registry):
    assert "connoss:software" in schema_registry.list()
    assert connoss_schema.get_schema_name() == "connoss"
    assert connoss_schema.get_class_name() == "Software"
    assert "name" in connoss_schema.get_property_list()
    assert connoss_schema.get_uri("name") == "https://schema.org/name"
    assert connoss_schema.build_context()["sdo"] == "https://schema.org/"

def test_registry_missing_schema_raises(schema_registry):
    import pytest
    from app.layer_3.schemas.linkml.linkml_schema_registry import MissingSchemaError
    with pytest.raises(MissingSchemaError): schema_registry.get("nope", "Software")

def test_jsonld_builder_adds_context_type_values_and_missing_none(collector, connoss_schema):
    out = JSONLDBuilder().build_jsonld(collector, connoss_schema)
    assert out["@type"] == "Software" and isinstance(out["@context"], dict)
    assert out["name"] == "Better Widget" and out["description"] == "A tool"
    assert out["codeRepository"] is None

def test_jsonld_builder_serializes_pydantic_values(connoss_schema):
    class Item(BaseModel): name: str
    from app.layer_1.metadata_collector.metadata_collector import MetadataCollector
    c = MetadataCollector(); c.collect("x", "https://schema.org/name", Item(name="nested"))
    assert JSONLDBuilder().build_jsonld(c, connoss_schema)["name"] == {"name": "nested"}

def test_enriched_metadata_uses_best_record_and_schema_category(collector, connoss_schema):
    out = build_enriched_metadata(collector, connoss_schema)
    assert out["name"] == {"confidence": .95, "source": "CFF", "category": "Minimum"}
    assert "codeRepository" not in out
