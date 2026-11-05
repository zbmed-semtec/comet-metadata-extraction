# Architecture

CoMET-RS keeps four layers. Outer layers call inward. Plugins do not import FastAPI, and the API does not parse `CITATION.cff`.

- **Layer 1** — schema contract and the collector that stores candidates
- **Layer 2** — one use case, plugin contracts, and plugin discovery
- **Layer 3** — platform and LLM plugins, pipeline composition, JSON-LD export, LinkML loading, FAIR scoring
- **Layer 4** — HTTP routes and response shaping

## One request

```text
GET /api/metadata/enriched
        |
        v
Layer 4  metadata_service.run_extraction
        |
        v
Layer 2  ExtractMetadataUseCase
        |  builds ExtractionContext + ExtractionState
        v
Layer 3  PluginPipelineComposer
        |  plugins whose `extracts` URIs match the schema,
        |  and whose `platforms` match the repository URL
        v
Layer 3  ExtractionPipelineRunner
        |  each plugin calls MetadataCollector.collect(...)
        v
Layer 1  MetadataCollector
        |
        v
Layer 3  JSONLDBuilder  (highest confidence per property)
        |
        v
Layer 4  JSON-LD, and enriched_metadata when requested
```

The schema decides which properties exist. Plugins decide which of those properties they can fill, and for which hosts. Several plugins may record the same property. Export keeps the record with the highest `confidence`.

`priority_level` only controls run order. The default is `100`. LLM plugins use `10`, so they run after platform plugins. A higher number runs first.

## The four layers

**Layer 1** (`app/layer_1/`) defines `BaseSchema` and `MetadataCollector`. A collector holds a list of `MetadataProperty` records per URI: source label, value, confidence, and optional LLM evidence.

**Layer 2** (`app/layer_2/`) runs `ExtractMetadataUseCase`: compose a pipeline, run it, call `JSONLDBuilder`. `ExtractionPlugin` is the contract plugins implement. `ExtractionPluginManager` discovers plugin classes under `app.layer_3.plugins` and indexes them by the URIs they extract.

**Layer 3** (`app/layer_3/`) is the extraction engine. GitHub, GitLab, and Codeberg plugins mix a platform client with shared property extractors. `PluginPipelineComposer` builds the step list. `LinkMlSchemaRegistry` loads `schemas/*.yaml`. `JSONLDBuilder` writes the document. `evaluate_fairness` scores the JSON-LD.

**Layer 4** (`app/layer_4/`) exposes `/api/*`, wires the use case in `metadata_service.py`, and builds `enriched_metadata`.

## Dependency direction

```text
Layer 4  API
    |
    v
Layer 2  use case + plugin contracts
    |
    +--> Layer 3  plugins, composer, builder, LinkML, evaluator
    |
    v
Layer 1  schema contract + collector
```

## Extending the system

| Change | Where |
|--------|--------|
| New repository host | Layer 3 platform package: client, base extractor (`platforms` set to the host), and one plugin class per shared extractor |
| New output schema | LinkML YAML in `schemas/`, loaded by `LinkMlSchemaRegistry` |
| New property on an existing schema | Slot in the YAML, then a plugin whose `extracts` contains that slot's URI |
| New source for an existing property | Another plugin that `collect`s the same URI with its own source label and confidence |
| New API behavior | Layer 4 routes and `metadata_service.run_extraction` |

## Where to read next

- [Layer 1](layer-1.md) — collector and schema contract
- [Layer 2](layer-2.md) — use case and plugin manager
- [Layer 3](layer-3.md) — plugins and export
- [Layer 4](layer-4.md) — HTTP API
