# CoMET-RS Backend Documentation

CoMET-RS is a metadata extraction toolkit for research software. It helps transform information from software repositories into structured, machine-actionable metadata that can support Software Management Plans, FAIR assessment, and long-term research software stewardship.

The backend is responsible for collecting repository information, interpreting project files, enriching metadata from external sources, and exposing the result through an API and command-line interface. It currently supports repository-based extraction from platforms such as GitHub and GitLab, with output formats aligned with maSMP and CodeMeta-style metadata.

## Purpose

Research software often contains important metadata spread across README files, citation files, repository settings, licenses, release archives, and external scholarly sources. CoMET-RS brings these signals together into a consistent representation so they can be inspected, reused, and evaluated more easily.

This documentation explains how the backend is organized, how metadata moves through the extraction pipeline, and how developers can extend the system with new platforms, schemas, or enrichment steps.

## Quick start (beginner-friendly)

If you only want to use the backend as a service:

1. Run the FastAPI server (see [Getting started](getting-started.md))
2. Open Swagger at `http://localhost:8000/docs`
3. Call:
   - `GET /api/metadata/enriched` for UI-friendly results (values + `source`/`source_reliability`)
   - `GET /api/metadata/stream` if you want progress events (SSE)
   - `GET /api/fairness` if you want FAIRness scores

## How to read these docs

| Page | Contents |
|------|----------|
| [Getting started](getting-started.md) | Install, run API and MkDocs, example `curl` calls |
| [Architecture](architecture.md) | Four layers and one HTTP request through the code |
| [Layer 1](layer-1.md) | `SoftwareMetadata`, schemas, provenance |
| [Layer 2](layer-2.md) | `ExtractMetadataUseCase` |
| [Layer 3](layer-3.md) | Pipelines, steps, merge, composer |
| [Layer 4](layer-4.md) | `/api` endpoints and responses |

Each layer page describes the **current** code layout and behavior. Start with [Getting started](getting-started.md) if you want to run the server first, or [Architecture](architecture.md) if you want the big picture.

    