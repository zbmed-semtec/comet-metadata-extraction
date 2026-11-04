# CoMET-RS Backend Documentation

CoMET-RS extracts metadata from research software repositories and returns it as JSON-LD. The backend reads GitHub, GitLab, and Codeberg, then exports ConnOSS, maSMP, or CodeMeta.

It collects values from platform APIs, repository files (`CITATION.cff`, README, license, BibTeX), and external services. Optional LLM plugins can fill gaps from the README. Each candidate is stored with its source and a confidence score. The exported value is the candidate with the highest confidence.

## Purpose

Repository metadata is spread across the platform API, citation files, the README, and outside indexes. CoMET-RS gathers those signals into one JSON-LD document, and can attach the winning source and confidence for each property.

These pages describe the current four-layer layout and how a request moves through it.

## Quick start

To install CoMET-RS and run the `comet-rs` command, see [README_PYPI.md](README_PYPI.md).

1. Run the API ([Getting started](getting-started.md)).
2. Open Swagger at `http://localhost:8000/docs`.
3. Call:
   - `GET /api/metadata` for JSON-LD only
   - `GET /api/metadata/enriched` for JSON-LD plus source and confidence
   - `GET /api/metadata/stream` for the same enriched result with progress events
   - `GET /api/metadata/property` for one property

The default schema is `ConnOSS` with schema class `Software`.

## How to read these docs

| Page | Contents |
|------|----------|
| [Getting started](getting-started.md) | Install, run the API, example calls |
| [Run comet-rs](README_PYPI.md) | CLI and Python library usage (`README_PYPI.md`) |
| [Architecture](architecture.md) | Four layers and one request through the code |
| [Layer 1](layer-1.md) | Schema contracts and `MetadataCollector` |
| [Layer 2](layer-2.md) | Use case, plugin contracts, plugin manager |
| [Layer 3](layer-3.md) | Plugins, composer, JSON-LD, LinkML, FAIR |
| [Layer 4](layer-4.md) | HTTP API |

Start with [Getting started](getting-started.md) to run the server, or [Architecture](architecture.md) for the layout.
