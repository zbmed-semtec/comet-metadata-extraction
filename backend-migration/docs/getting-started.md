# Getting Started

Run the backend locally and call the HTTP API. The routes live in Layer 4.

To install the package and run the `comet-rs` command (extract, single property, FAIRness), see [README_PYPI.md](README_PYPI.md).

## What you get

Given a repository URL, the backend:

1. Loads the requested LinkML schema and class
2. Selects extraction plugins that declare that schema's properties and match the repository host
3. Lets each plugin record candidates (source, value, confidence) on a `MetadataCollector`
4. Exports the highest-confidence value of each property as JSON-LD
5. Optionally returns per-property source, source reliability, and category

Supported hosts: GitHub, GitLab, Codeberg. Supported schemas: `ConnOSS` (class `Software`), `maSMP` (`SoftwareSourceCode`, `SoftwareApplication`), `CODEMETA` (`SoftwareSourceCode`).

## Prerequisites

- Python 3.10+
- A terminal in `backend-migration/`

## Run the server

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Schemas load from `schemas/` (override with `COMET_SCHEMAS_PATH`).

Then open:

- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### View this documentation

Port **8002** keeps MkDocs off the API port:

```bash
mkdocs serve
```

Open `http://127.0.0.1:8002/`. If that port is taken:

```bash
mkdocs serve -a 127.0.0.1:8003
```

## Call the API

Query parameters used below:

| Parameter | Default | Role |
|-----------|---------|------|
| `repo_url` | required | GitHub, GitLab, or Codeberg repository URL |
| `schema` | `ConnOSS` | `ConnOSS`, `maSMP`, or `CODEMETA` |
| `schema_class` | `Software` | LinkML class inside that schema |
| `access_token` | omitted | Token for private repositories and higher rate limits |

`schema_class` must exist on the chosen schema. `Software` matches ConnOSS. For maSMP pass `SoftwareSourceCode` or `SoftwareApplication`. For CodeMeta pass `SoftwareSourceCode`.

### 1) JSON-LD only

```bash
curl "http://localhost:8000/api/metadata?repo_url=https://github.com/owner/repo&schema=ConnOSS"
```

`results` is the JSON-LD document. There is no per-property source map.

### 2) JSON-LD plus enrichment

```bash
curl "http://localhost:8000/api/metadata/enriched?repo_url=https://github.com/owner/repo&schema=ConnOSS"
```

`enriched_metadata` adds, for each property that has a value:

- `source` — label of the winning candidate (`Platform API`, `CFF File`, …)
- `source_reliability` — confidence of that candidate
- `category` — schema slot category, or `optional` when the slot has none
- `confidence` and `evidence` when the winner came from the LLM plugin

For `schema=ConnOSS` the same response also includes a `fairness` report. Other schemas omit it. There is no separate `/api/fairness` route.

### 3) One property

```bash
curl "http://localhost:8000/api/metadata/property?repo_url=https://github.com/owner/repo&schema=ConnOSS&property=name"
```

`results` is a list of `{ value, source, source_reliability, confidence, evidence }`.

### 4) Stream progress

```bash
curl -N "http://localhost:8000/api/metadata/stream?repo_url=https://github.com/owner/repo&schema=ConnOSS"
```

Events:

- `progress` — phases `pipeline` and `jsonld_build`, each `started` then `completed`
- `result` — the enriched payload
- `error` — `{ "detail": "..." }`

## Optional LLM extraction

LLM plugins stay idle unless enabled. See `app/layer_3/plugins/llm/README.md`. When enabled they run after the platform plugins and only fill properties that still have no candidate.

## What to read next

- [Run comet-rs](README_PYPI.md) — CLI and library usage
- [Architecture](architecture.md)
- [Layer 1](layer-1.md) through [Layer 4](layer-4.md)
