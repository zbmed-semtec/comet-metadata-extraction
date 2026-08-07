# Layer 2: Application Use Cases

Layer 2 **orchestrates** metadata extraction: detect platform, compose and run the Layer 3 pipeline, build JSON-LD, return results to callers (Layer 4 services, CLI, or tests). It does not parse `CITATION.cff`, call GitHub, or merge author lists — that is Layer 3.

Read [Layer 1](layer-1.md) for `SoftwareMetadata` and [Architecture](architecture.md) for the full request path.

## What is a use case?

A **use case** is one application operation end to end. The main implementation is **`ExtractMetadataUseCase`** in `app/layer_2/use_cases/extract_metadata.py`.

```text
Repository URL + schema + optional token
              |
              v
    ExtractMetadataUseCase.execute()
              |
              +--> Layer 3: PipelineComposer + ExtractionPipelineRunner
              |
              +--> Layer 3: JSONLDBuilder.build_jsonld()
              |
              v
    ExtractMetadataResult
      - jsonld_document
      - extraction_metadata (optional, per-field source/confidence)
      - metadata (SoftwareMetadata, for FAIRness etc.)
```

The use case stays thin: collaborators are injected in the constructor for testing.

## What Layer 2 owns

- **Platform detection** from the repo URL (`URLPatternMatcher`, used from the use case).  
- **Pipeline selection** via `PipelineComposer.compose(domain, schema, platform)`.  
- **Initial state**: empty `SoftwareMetadata`, `ExtractionContext`, and `ExtractionState.data` (including `record_field` when a collector is configured).  
- **Running** the pipeline through `ExtractionPipelineRunner`.  
- **JSON-LD export** via the `JSONLDBuilder` protocol (implementation in `app/layer_3/builders/jsonld_builder.py`).  

## Folder structure

```text
app/layer_2/
`-- use_cases/
    `-- extract_metadata.py
```

`extract_metadata.py` contains:

- `ExtractMetadataUseCase`, `ExtractMetadataResult`  
- `_build_record_field()` — attaches `state.data["record_field"]` to the optional `ExtractionMetadataCollector`  
  - Steps may call `record(field)` for platform defaults, or `record(field, source=..., confidence=...)` for explicit provenance  
  - Merge steps typically use `record_field_provenance()` in Layer 3 (see [Layer 3](layer-3.md))

## How `execute()` works

1. Detect `github` or `gitlab`; error if unsupported.  
2. `PipelineComposer.compose(...)`.  
3. Build `ExtractionState` with `SoftwareMetadata()` and `data["record_field"]` when enrichment is enabled.  
4. Build `ExtractionContext` (repo URL, domain, schema, platform, token).  
5. `pipeline_runner.run(pipeline, context, state)`.  
6. `jsonld_builder.build_jsonld(state.metadata, schema, has_release)`.  
7. Return `ExtractMetadataResult` including `collector.get_all()` when configured.

Individual Layer 3 step names (for example `github.extract_keywords`) are separate from the coarse progress ids above.

## Imports from Layer 3

Layer 2 imports **contracts and composer**, not every step class:

```text
PipelineComposer
ExtractionPipelineRunner
ExtractionMetadataCollector (optional)
JSONLDBuilder (protocol; concrete class in Layer 3)
```

## Adding a new use case

1. New module under `app/layer_2/use_cases/`.  
2. Constructor injection for collaborators.  
3. No direct HTTP or parsing in the use case body.  
4. Small result dataclass.  
5. Tests with stubs (`tests/test_extract_metadata_usecase.py`).

## Extraction metadata (UI provenance)

For fields to appear in `enriched_metadata` on the API:

1. **Layer 3** — record source/confidence in extract or merge steps (`record_field`, `record_field_provenance`). For multi-source fields, record once per contributing source (`MULTI_SOURCE_PROPERTIES` in Layer 1).  
2. **Layer 4** — `build_enriched_metadata()` maps entity field names to JSON-LD keys and attaches `category` for maSMP.

Layer 1 defines which sources are valid; Layer 3 records what actually contributed.

## Design principles

- Sequence work for one user request here.  
- Put parsing, HTTP, and merge logic in Layer 3 steps.

## Where to read next

- [Layer 3](layer-3.md) — steps, bundles, composer  
- [Layer 4](layer-4.md) — HTTP API  
- [Architecture](architecture.md)  
