# Layer 4: API

Layer 4 is the FastAPI surface: routes, response models, and the service that wires `ExtractMetadataUseCase`.

Entry point: `app/main.py` (CORS, router, schema load on startup). Routes: `app/layer_4/endpoints/metadata.py`.

## Layout

```text
app/layer_4/
|-- endpoints/metadata.py           # /api routes
|-- services/metadata_service.py    # run_extraction
|-- services/fairness_service.py    # older helper, not used by the routes
|-- builders/enriched_metadata.py   # collector -> enriched_metadata
`-- schemas/metadata.py             # response models
```

## Base URL

- Prefix: `/api`
- Local server: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

Startup calls `metadata_service.initialize()`, which loads every LinkML file from `COMET_SCHEMAS_PATH` (default `schemas/`).

## Query parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `repo_url` | yes | GitHub, GitLab, or Codeberg repository URL |
| `schema` | no, default `ConnOSS` | `ConnOSS`, `maSMP`, or `CODEMETA` |
| `schema_class` | no, default `Software` | LinkML class. Use `SoftwareSourceCode` or `SoftwareApplication` for maSMP, and `SoftwareSourceCode` for CodeMeta |
| `access_token` | no | Token for private repositories |

## Wiring

`run_extraction` in `metadata_service.py` is the function every route calls.

1. Create a `MetadataCollector` and an `ExtractMetadataUseCase` with the shared `JSONLDBuilder`, `PluginPipelineComposer`, and `ExtractionPipelineRunner`.
2. Resolve `schema` + `schema_class` through `LinkMlSchemaRegistry`.
3. `use_case.execute(...)`.
4. If enrichment was requested, `build_enriched_metadata(collector, schema)`.
5. If a FAIR assessment was requested, `evaluate_fairness` on the JSON-LD.

A plugin failure stays on `extraction_state.errors` and is returned as `errors`. It does not fail the HTTP call by itself. Unknown schema, unknown property, and unsupported input surface as HTTP 400.

## Endpoints

### `GET /api/health`

`{"status": "healthy", "service": "metadata-extractor"}`.

### `GET /`

Welcome payload with links to `/docs` and `/api/health`.

### `GET /api/platforms`

GitHub (`github.com`), GitLab (`gitlab.com`), Codeberg (`codeberg.org`).

### `GET /api/metadata`

JSON-LD only (`MetadataPlainResponse.results`). Use this when the caller does not need source or confidence.

### `GET /api/metadata/enriched`

JSON-LD plus `enriched_metadata`. This route also runs the FAIR assessment. The `fairness` field is included only when `schema` is `ConnOSS`.

`enriched_metadata` is one object per slot that has a winning record:

| Field | Source |
|-------|--------|
| `source` | Winning `MetadataProperty.source` |
| `source_reliability` | Winning `confidence` |
| `category` | LinkML slot category, or `optional` |
| `confidence` | Present when the winner set `extraction_confidence` |
| `evidence` | Present when the winner attached evidence |

`alternatives` is the collector's full list of records for every URI, including the ones that lost on confidence.

Provenance path:

1. Plugins `collect` into the `MetadataCollector`.
2. `JSONLDBuilder` reads `get_most_confident` into `results`.
3. `build_enriched_metadata` reads the same winner into `enriched_metadata`.

### `GET /api/metadata/stream`

Server-Sent Events, then the enriched payload.

| Event | Payload |
|-------|---------|
| `progress` | `{ "step": "pipeline" \| "jsonld_build", "status": "started" \| "completed", "label": "..." }` |
| `result` | Enriched response |
| `error` | `{ "detail": "..." }` |

```bash
curl -N "http://localhost:8000/api/metadata/stream?repo_url=https://github.com/owner/repo&schema=ConnOSS"
```

### `GET /api/metadata/property`

One slot. Query parameter `property` is the slot name (`name`, `license`, `softwareRequirements`).

The route runs extraction with `single_property` set, so the composer only includes plugins that declare that slot. The response `results` list holds `value`, `source`, `source_reliability`, and, when present, `confidence` and `evidence`.

### FAIR route

`GET /api/fairness` is not registered. FAIR scores are the `fairness` object on `GET /api/metadata/enriched` for ConnOSS.

## Where to read next

- [Getting started](getting-started.md) — copy-paste calls
- [Layer 2](layer-2.md) — the use case these routes invoke
- [Layer 3](layer-3.md) — plugins and JSON-LD export
