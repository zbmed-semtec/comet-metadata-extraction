# Layer 1: Schema Contract And Collected Values

Layer 1 defines two things: what a schema can be asked for, and where extracted values are stored. It does not call GitHub, read files, or serve HTTP.

```text
app/layer_1/
|-- schemas/
|   |-- base_schema.py            # BaseSchema
|   `-- base_schema_registry.py   # BaseSchemaRegistry
`-- metadata_collector/
    `-- metadata_collector.py     # MetadataProperty, MetadataCollector
```

The concrete schema is LinkML, implemented in Layer 3 (`LinkMlSchema`). Layer 1 only declares the methods every schema must provide.

## Schema contract

`BaseSchema` is the view the rest of the backend uses:

| Method | Returns |
|--------|---------|
| `get_schema_name()` | Schema name (`connoss`, `maSMP`, `codemeta`) |
| `get_class_name()` | Class inside that schema (`Software`, `SoftwareSourceCode`, …) |
| `get_property_list()` | Slot names to extract and export |
| `get_uri(property_name)` | Expanded URI plugins use as the property key |
| `get_categories_of(property_name)` | Slot category, used in enriched responses |
| `get_prefixes()` / `build_context()` | JSON-LD `@context` |

Plugins and the composer key off the URI, not the slot name. `https://schema.org/name` is the same property whether the schema calls the slot `name`.

`BaseSchemaRegistry` loads schemas from a directory and returns one by name and class. `LinkMlSchemaRegistry` in Layer 3 is the implementation used at runtime.

## Collected values

`MetadataCollector` is the worksheet for one run. Plugins append; they do not overwrite.

```python
collector.collect(source, property_uri, value, confidence)
```

Each call stores a `MetadataProperty`:

| Field | Meaning |
|-------|---------|
| `source` | Short label, such as `Platform API` or `CFF File` |
| `property_name` | Property URI |
| `property_value` | Extracted value |
| `confidence` | Ranking weight for this source. Omitted callers are treated as `1.0` |
| `evidence` | Optional supporting text, used by the LLM plugins |
| `extraction_confidence` | Optional score from the LLM pipeline, kept separate from `confidence` |

`get_most_confident(uri)` returns the record with the highest `confidence`. That record is the one `JSONLDBuilder` and `build_enriched_metadata` publish. The other records stay on the collector. The enriched HTTP response exposes them as `alternatives`.

`confidence` becomes `source_reliability` in the API. It ranks sources against each other. `extraction_confidence` is only the LLM's own score for the text it read.

## What does not belong here

Parsing, HTTP clients, plugin discovery, and response models live in outer layers. A new source is a plugin that calls `collect`. A new schema is a LinkML file plus the existing registry, as long as it can implement `BaseSchema`.

## Where to read next

- [Layer 2](layer-2.md) — who runs the collector
- [Layer 3](layer-3.md) — who writes into it
