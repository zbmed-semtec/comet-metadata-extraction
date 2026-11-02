# Getting Started

This guide is for beginners. It shows you how to run the backend locally and how to call the API endpoints (which is what **Layer 4** exposes).

## What you get

Given a repository URL (GitHub or GitLab), the backend:

1. Detects the platform (GitHub/GitLab)
2. Extracts signals from repository files and platform APIs
3. Merges those signals into a single internal `SoftwareMetadata` object
4. Exports the result as **maSMP** or **CodeMeta** JSON-LD
5. Optionally returns per-property **source** and **source_reliability** (enrichment)

## Prerequisites

- Python 3.10+
- A way to run the backend (local terminal)

## Run the server (local)

From `backend-migration/`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### View this documentation locally

From `backend-migration/` (port **8002** so it does not clash with the API on **8000**):

```bash
mkdocs serve
```

Open `http://127.0.0.1:8002/`. If you see “Address already in use”, pick another port:

```bash
mkdocs serve -a 127.0.0.1:8003
```

## Call the API (copy/paste examples)

### 1) Extract JSON-LD only (no enrichment)

```bash
curl "http://localhost:8000/api/metadata?repo_url=https://github.com/owner/repo&schema=maSMP"
```

This endpoint returns:

- `results`: maSMP/CODEMETA JSON-LD only
- no per-property `source`/`source_reliability` map

### 2) Extract JSON-LD + enriched source/source_reliability

```bash
curl "http://localhost:8000/api/metadata/enriched?repo_url=https://github.com/owner/repo&schema=maSMP"
```

This endpoint returns:

- `results`: maSMP/CODEMETA JSON-LD
- `enriched_metadata`: for each property key, the UI-ready:
  - `source`
  - `source_reliability`
  - (maSMP only) `category`

### 3) Extract a single property

If you want only one field (for example `author`):

```bash
curl "http://localhost:8000/api/metadata/property?repo_url=https://github.com/owner/repo&schema=maSMP&property=author"
```

Response shape:

- `results`: a list of matches (because the same property can appear in multiple profiles)
  - each match includes `{ profile, value, source, source_reliability }`

### 4) Stream progress (SSE)

```bash
curl -N "http://localhost:8000/api/metadata/stream?repo_url=https://github.com/owner/repo&schema=maSMP"
```

You will receive events:

- `progress`: coarse phases `pipeline` and `jsonld_build`, each with `status` `started` or `completed`
- `result`: the same payload you get from `/api/metadata/enriched`
- `error`: an error message if extraction fails

## What to read next

- [Layer 1: Domain Models, Schemas, And Provenance](layer-1.md)
- [Layer 2: Application Use Cases](layer-2.md)
- [Layer 3: Pipelines, Adapters, And Extraction Steps](layer-3.md)
- [Layer 4: API](layer-4.md)

