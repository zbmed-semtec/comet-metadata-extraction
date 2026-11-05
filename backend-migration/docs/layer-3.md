# Layer 3: Plugins, Composition, And Export

Layer 3 extracts values, loads schemas, and builds JSON-LD. Layer 2 runs the pipeline. Layer 4 serves it.

```text
app/layer_3/
|-- plugins/
|   |-- github/          # client + GitHub plugin classes
|   |-- gitlab/
|   |-- codeberg/
|   |-- llm/             # optional README extraction
|   |-- shared/          # one extractor per property, HTTP clients, types
|   `-- url_pattern_matcher_plugin.py
|-- composers/plugin_pipeline_composer.py
|-- steps/contracts/pipeline.py    # ExtractionPipelineRunner
|-- builders/jsonld_builder.py
|-- evaluators/fairness_evaluator.py
`-- schemas/linkml/                # LinkMlSchema, LinkMlSchemaRegistry
```

## How a plugin is shaped

A runnable plugin is a platform base mixed with a shared property extractor.

`GitPlatformNameExtractor` in `plugins/shared/collection.py` declares `extracts = {'https://schema.org/name'}` and reads the name from the platform API, `CITATION.cff`, and BibTeX. It has no host. `GitHubNameExtractor` adds `platforms = {'github.com'}` and a `GitHubClient`. GitLab and Codeberg do the same with their own clients. The composer discovers the concrete classes, not the shared bases.

`extract` records every candidate it finds:

```python
state.metadata_collector.collect("Platform API", "https://schema.org/name", name, 0.95)
state.metadata_collector.collect("CFF File", "https://schema.org/name", title, 0.90)
```

Typical source labels are `Platform API`, `CFF File`, and `BibTeX`. Confidence is a fixed weight per source, not a model score. The collector keeps all of them. Export later picks the highest confidence.

Shared extractors also cover description, license, authors, keywords, identifiers, citation, README, version, dates, issue tracker, software requirements, and related fields. External clients used from those extractors:

- OpenAlex
- Software Heritage
- Wayback Machine

The platform client is cached on `state.data` for the rest of the run.

## Composer

`PluginPipelineComposer.compose`:

1. Asks the schema for its property list, or for the single requested property.
2. Asks `ExtractionPluginManager` for applicable plugins per property.
3. Groups them by `priority_level` and runs higher numbers first. Ties break by plugin name.
4. Returns an `ExtractionPipeline`.

On the first compose, the manager walks `app.layer_3.plugins` and registers every concrete plugin. A property with no plugin is skipped on a full run and reported in the log. Single-property mode raises instead.

`ExtractionPipelineRunner` calls `extract` on each step. An exception is stored on `state.errors` under the plugin name and does not stop the pipeline.

## LLM plugins

`plugins/llm/` is off unless `COMET_LLM_ENABLED` is set. See `plugins/llm/README.md` for Ollama settings.

LLM extractors use `priority_level = 10`, so they run after the default platform plugins (`100`). They return immediately when the property already has a candidate, and they attach `extraction_confidence` and `evidence` on the record they collect.

## LinkML schemas

`LinkMlSchemaRegistry.load` reads every `*.yaml` in the schemas directory (`schemas/` by default, or `COMET_SCHEMAS_PATH`). Each class in a file becomes one schema, keyed as `schema_name:class_name` in lowercase:

| File | Lookup examples |
|------|-----------------|
| `schemas/connoss.yaml` | `connoss:software` |
| `schemas/maSMP.yaml` | `masmp:softwaresourcecode`, `masmp:softwareapplication` |
| `schemas/codemeta.yaml` | `codemeta:softwaresourcecode` |

`LinkMlSchema` implements `BaseSchema`. `get_uri` expands the slot URI. An unknown slot raises `UnknownPropertyError` and suggests close slot names.

`JSONLDBuilder.build_jsonld` writes `@context` and `@type` from the schema, then one key per slot. The value is `get_most_confident` for that slot's URI, or `null` when nothing was collected.

## FAIR scores

`evaluate_fairness(jsonld_document)` scores the exported document (description, identifier, license, version, and related signals) into F, A, I, and R. The enriched API attaches that report only for ConnOSS. `app/layer_4/services/fairness_service.py` is an older entry point and is not what the HTTP API calls.

## Adding a plugin

1. Subclass the platform base and the shared extractor, or write a new extractor with `name`, `extracts`, and `platforms`.
2. Implement `extract` and call `collector.collect` once per source.
3. Put the module under `app/layer_3/plugins/` so discovery imports it.
4. Set `priority_level` below `100` only when the plugin must run after the platform extractors.
5. Add the slot to the LinkML schema if it is a new property.

## Where to read next

- [Layer 2](layer-2.md) — selection and the use case
- [Layer 4](layer-4.md) — how export becomes an HTTP response
- [Layer 1](layer-1.md) — the collector fields
