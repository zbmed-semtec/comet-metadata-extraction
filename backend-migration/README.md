# CoMET-RS Backend

Metadata extraction for research software repositories (GitHub, GitLab, Codeberg), with ConnOSS, maSMP, and CodeMeta JSON-LD output.

## Architecture

Four layers under `app/`:

| Layer | Location | Role |
|-------|----------|------|
| **1** | `app/layer_1/` | Schema contracts (`BaseSchema`, `BaseSchemaRegistry`) and `MetadataCollector` (source, confidence, evidence) |
| **2** | `app/layer_2/` | `ExtractMetadataUseCase`, plugin contracts, and `ExtractionPluginManager` |
| **3** | `app/layer_3/` | Platform and LLM plugins, pipeline composer, JSON-LD builder, FAIR evaluator, LinkML schemas |
| **4** | `app/layer_4/` | FastAPI routes, services, API schemas, and response builders |

A request runs through the layers like this:

```text
Layer 4 route
    → ExtractMetadataUseCase
    → PluginPipelineComposer (plugins by schema property and priority)
    → plugins write into MetadataCollector
    → JSONLDBuilder
    → Layer 4 response (JSON-LD, optionally enriched)
```

Layer 3 layout:

- `plugins/github/`, `plugins/gitlab/`, `plugins/codeberg/` — platform clients and collection
- `plugins/llm/` — LLM extraction
- `plugins/shared/` — shared types, HTTP clients, and external services (OpenAlex, Software Heritage, Wayback)
- `composers/plugin_pipeline_composer.py` — selects applicable plugins and orders them by priority
- `builders/jsonld_builder.py` — exports the collector to JSON-LD
- `evaluators/fairness_evaluator.py` — FAIR assessment from collected metadata
- `schemas/linkml/` — LinkML schema loading

## Installation

```bash
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: http://localhost:8000/docs
- Enriched metadata: `GET /api/metadata/enriched?repo_url=...&schema=ConnOSS`

`schema` defaults to `ConnOSS`. Other values: `maSMP`, `CODEMETA`.

## Run tests

```bash
pytest
```

## Documentation (MkDocs)

Pages under `docs/` describe the current four-layer layout. Start with [Getting started](docs/getting-started.md) or [Architecture](docs/architecture.md). CLI usage is in [README_PYPI.md](README_PYPI.md).

```bash
mkdocs serve
```

Open http://127.0.0.1:8002/ (port 8002 avoids clashing with the API on 8000).
