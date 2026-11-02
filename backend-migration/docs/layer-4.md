# Layer 4: API (FastAPI)

Layer 4 exposes the backend over HTTP: **routes**, **Pydantic response models**, and **services** that wire `ExtractMetadataUseCase` and shape responses for clients.

Entry point: `app/main.py` (CORS, router registration). Routes: `app/layer_4/endpoints/metadata.py`.

## Base URL

- API prefix: `/api`  
- Local server: `http://localhost:8000`  
- Interactive docs: `http://localhost:8000/docs`

## Folder structure

```text
app/layer_4/
|-- endpoints/
|   `-- metadata.py          # All /api routes
|-- services/
|   |-- metadata_service.py  # run_extraction, streaming, single property
|   `-- fairness_service.py  # FAIRness assessment
|-- builders/
|   `-- enriched_metadata.py # Map collector output to enriched_metadata
`-- schemas/
    `-- metadata.py          # MetadataPlainResponse, MetadataEnrichedResponse, ...
```

Layer 2 runs the use case; Layer 3 fills `SoftwareMetadata` and records provenance; Layer 4 returns JSON to the client.

## Common query parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `repo_url` | yes | GitHub or GitLab repository URL |
| `schema` | no (default `maSMP`) | `maSMP` or `CODEMETA` |
| `access_token` | no | Token for private repositories |

## Endpoints

### `GET /api/health`

Health check: `{"status": "healthy", "service": "metadata-extractor"}`.

### `GET /`

Welcome JSON with links to `/docs` and `/api/health`.

### `GET /api/platforms`

Lists supported host patterns (GitHub, GitLab).

### `GET /api/metadata`

Returns **JSON-LD only** (`MetadataPlainResponse.results`).

Use when you need the schema document without per-property `source` / `source_reliability`.

### `GET /api/metadata/enriched`

Returns JSON-LD plus **`enriched_metadata`** (`MetadataEnrichedResponse`).

- **maSMP** — nested by profile (`maSMP:SoftwareSourceCode`, `maSMP:SoftwareApplication`); each property has `source`, `source_reliability`, `category`.  
- **CODEMETA** — flat `codemeta` profile with `source` and `source_reliability`.

**Provenance flow:**

1. Layer 3 merge/extract steps record into `ExtractionMetadataCollector`.  
2. Use case returns `extraction_metadata` from `collector.get_all()`.  
3. `build_enriched_metadata()` aligns entity field names with JSON-LD keys.

Multi-source fields expose `source` as a **list**; `source_reliability` is how reliable the winning source is. It is separate from the confidence score produced by the LLM extraction pipeline.

### `GET /api/metadata/stream` (SSE)

Same final payload as `/api/metadata/enriched`, with **Server-Sent Events** during the run.

Events:

| Event | Payload |
|-------|---------|
| `progress` | `{ "step": "pipeline" \| "jsonld_build", "status": "started" \| "completed", "label": "..." }` |
| `result` | Full enriched response (same shape as `/api/metadata/enriched`) |
| `error` | `{ "detail": "..." }` |

Example:

```bash
curl -N "http://localhost:8000/api/metadata/stream?repo_url=https://github.com/owner/repo&schema=maSMP"
```

### `GET /api/metadata/property`

Extract one JSON-LD property with value, source, and source reliability.

| Parameter | Description |
|-----------|-------------|
| `property` | JSON-LD key (e.g. `author`, `license`, `softwareRequirements`) |

Returns `results`: `[{ "profile", "value", "source", "source_reliability" }, ...]`.  
On maSMP, the same key may appear in more than one profile.

### `GET /api/fairness`

Runs extraction and returns JSON-LD plus a **FAIRness** report (`fairness` object with F/A/I/R scores).  
Scoring uses `SoftwareMetadata` in Layer 3 (`fairness_evaluator.py`), so scores do not depend on maSMP vs CODEMETA choice; only the JSON-LD shape does.

## Services (wiring)

**`metadata_service.py`** — shared `JSONLDBuilder`, `PipelineComposer`, `PipelineRunner`; creates the use case with optional `InMemoryExtractionMetadataCollector`.

**`fairness_service.py`** — extraction + `evaluate_fairness_from_metadata()`.

Endpoints stay thin: validate platform, call service, map to response schema.

## Where to read next

- [Getting started](getting-started.md) — run server and try endpoints  
- [Layer 2](layer-2.md) — use case  
- [Layer 3](layer-3.md) — steps and provenance recording  
