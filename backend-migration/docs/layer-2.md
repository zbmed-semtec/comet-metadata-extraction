# Layer 2: Use Case And Plugin Contracts

Layer 2 turns one repository URL into a pipeline run and a JSON-LD document. It does not parse citation files or call a platform API. Those are Layer 3 plugins.

Read [Layer 1](layer-1.md) for the collector and [Architecture](architecture.md) for the full request path.

## Use case

`ExtractMetadataUseCase` in `app/layer_2/use_cases/extract_metadata.py` is the operation the API and CLI share.

```text
repo URL + schema + optional token
        |
        v
ExtractMetadataUseCase.execute()
        |
        +--> PluginPipelineComposer.compose(context)
        |
        +--> ExtractionPipelineRunner.run(...)
        |
        +--> JSONLDBuilder.build_jsonld(collector, schema)
        |
        v
ExtractMetadataResult
    jsonld_document
    extraction_state   # collector, scratchpad, per-plugin errors
```

`execute()`:

1. Builds an `ExtractionState` whose collector is the one injected by the caller.
2. Builds an `ExtractionContext`: repository URL, domain `"software"`, schema, the URL again as `platform`, and the optional token.
3. Asks the composer for a pipeline. `single_property` limits the pipeline to plugins for that one slot.
4. Runs every step. A failing plugin is recorded on `state.errors` and the rest continue.
5. Builds JSON-LD from the collector.

`EXTRACTION_STEPS` is the progress vocabulary for the streaming endpoint: `pipeline`, then `jsonld_build`.

Collaborators are constructor arguments: `JSONLDBuilder`, `PipelineComposer`, `PipelineRunner`, and the `MetadataCollector`. Tests can pass stubs.

## Contracts

`app/layer_2/contracts/` holds the types the use case and the plugins share.

| Type | Role |
|------|------|
| `ExtractionContext` | Immutable: `repo_url`, `domain`, `schema`, `platform`, `access_token` |
| `ExtractionState` | Mutable: `metadata_collector`, `data` scratchpad, `errors` |
| `ExtractionStep` | `name`, `extracts` (URI set), `platforms`, and `extract(context, state)` |
| `ExtractionPipeline` | Ordered steps |
| `PipelineComposer` | `compose(context, single_property) -> pipeline` |
| `PipelineRunner` | `run(pipeline, context, state) -> state` |

`platform` on the context is the repository URL. A plugin is applicable when one of its `platforms` strings occurs in that URL (`github.com`, `gitlab.com`, `codeberg.org`).

## Plugins

```text
app/layer_2/
|-- base_plugin.py                  # name, version, priority_level, on_load
|-- extraction_plugin.py            # ExtractionPlugin.applicable()
|-- plugin_manager.py               # discover and instantiate
`-- extraction_plugin_manager.py    # index by extracted URI
```

`PluginManager.discover(package)` imports every module under the package and registers concrete `BasePlugin` subclasses. `ExtractionPluginManager` indexes each plugin by the URIs in `extracts`.

`select(property_name, context)`:

1. Resolves the slot to a URI through the schema.
2. Looks up plugins that declared that URI.
3. Keeps those for which `applicable(context)` is true.

An unknown slot raises `UnknownPropertyError`. A known slot with no applicable plugin is a warning; the property is left empty. In single-property mode that empty selection is an error.

`priority_level` lives on `BasePlugin` (default `100`). The composer uses it. The manager does not.

## Where to read next

- [Layer 3](layer-3.md) — composer and the plugins it discovers
- [Layer 4](layer-4.md) — who constructs the use case
