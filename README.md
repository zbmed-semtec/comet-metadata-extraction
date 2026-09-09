[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18837374.svg)](https://doi.org/10.5281/zenodo.18837374)
![Status](https://img.shields.io/badge/repo_status-Active-green)

<p align="center">
  <img src="docs/img/background.gif" width="100%">
</p>

# Code Metadata Extraction Toolkit for Research Software (CoMET-RS)

This project is designed to automate the extraction of metadata from GitHub, GitLab and Codeberg repositories to generate a **machine-actionable** metadata file in JSON-LD that can be included in the repository or used by metadata aggregators and curators. CoMET-RS consists of two main components:

1. A metadata extraction engine, which is responsible for loading schema definitions and coordinates ExtractionPlugins.
2. A collection of plugins that perform metadata extraction. Each plugin has one or more target properties it can extract from its target Platform.

Basing CoMET-RS on both a clean and plugin based architecture enables a high degree of extensibility, making it possible to add completely new schemas and supported platforms, as well as accessing the extraction engine through multiple channels (command line & API).

# Introduction

CoMET can be installed and used in different configurations.

## API

To use CoMET as a web API, you can either install it using [Docker](#docker) or perform a [manual installation](#manual).

## CLI & Library

To use CoMET as a `cli` tool, you can either perform a [manual installation](#manual) or a [Pip installation](#pip).

**Requirements:** Python 3.10 or higher for the backend/CLI; Node.js 20.20.0 for the frontend (only needed for manual frontend setup).

# Installation

Here you find instructions for performing the different types of installations possible for CoMET.

## Docker

The Docker installation will start the backend API (port `8000`) and the frontend (port `3000`).

```bash
git clone git@github.com:zbmed-semtec/comet-metadata-extraction.git
cd comet-metadata-extraction/
docker compose up --build
```

Once the containers are running, these URLs are being used.

- **Legacy Frontend UI:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **API docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

To stop the running containers, run:

```bash
docker compose down
```

This shuts down and removes the containers but keeps the built images.

## Pip

The command line interface (CLI) for CoMET (`comet-rs`) can be installed by running

```bash
pip install comet-rs
```

The minimum required `python` version is 3.10. See [CLI Usage](#cli-usage) below for available commands.

## Manual

Assuming you already created a virtual environment or plan to use the standard python environment, this installs the backend API and the `comet-rs` CLI:

```bash
git clone git@github.com:zbmed-semtec/comet-metadata-extraction.git
cd comet-metadata-extraction/backend-migration/
pip install -r requirements.txt
pip install -e .
```

To also run the *discontinued* frontend manually (separate from Docker):

```bash
nvm install 20.20.0
nvm use 20.20.0
npm install -g npm@10.8.2

cd ../frontend-migration
npm install
npm run dev
```

The frontend dev server runs at [http://localhost:3000](http://localhost:3000) and expects the backend at `http://localhost:8000` (set via the `API_BASE_URL` environment variable if different).

---

# CLI Usage

After installing via [Pip](#pip) or [Manual](#manual) installation, the `comet-rs` command is available.

```bash
comet-rs --help
```

```text
usage: comet-rs [-h] {extract,extract_property} ...

Extract metadata (and per-property sources) from code repositories, for any
supported schema.
```

## Extract full metadata

```bash
comet-rs extract <url> <schema> [--schema-class SCHEMA_CLASS] [--token TOKEN] [--with-enrichment]
```

- `url`: Repository URL (GitHub or GitLab)
- `schema`: Schema to use, e.g. `ConnOSS`, `maSMP`, `CODEMETA`
- `--schema-class`: defaults to `Software`
- `--token`: GitHub/GitLab personal access token (optional, increases rate limits and allows access to private repos)
- `--with-enrichment`: include source, confidence, and category metadata for each extracted property

Example:

```bash
comet-rs extract https://github.com/zbmed-semtec/comet-metadata-extraction connoss --with-enrichment
```

## Extract a single property

```bash
comet-rs extract_property <url> <property> [--schema SCHEMA] [--schema-class SCHEMA_CLASS] [--token TOKEN]
```

- `--schema`: defaults to `connoss` if not specified

Example:

```bash
comet-rs extract_property https://github.com/owner/repo license
```

## Authentication tokens

Instead of `--token`, you can set an environment variable so it's picked up automatically:

```bash
export GITHUB_TOKEN=your_token_here
export GITLAB_TOKEN=your_token_here
```

CoMET selects `GITLAB_TOKEN` automatically when the repository URL contains `gitlab`, otherwise it uses `GITHUB_TOKEN`.

---

# API Usage

The backend exposes the following endpoints (all under the `/api` prefix unless noted):

|Method|Path|Description|
|---|---|---|
|`GET`|`/`|Root/status endpoint|
|`GET`|`/api/health`|Health check|
|`GET`|`/api/metadata`|Extract full metadata for a repository|
|`GET`|`/api/metadata/enriched`|Extract metadata with enrichment (source, confidence, category)|
|`GET`|`/api/metadata/stream`|Stream metadata extraction results|
|`GET`|`/api/metadata/property`|Extract a single metadata property|
|`GET`|`/api/platforms`|List supported repository platforms|
|`GET`|`/docs`|Interactive Swagger UI|
|`GET`|`/redoc`|ReDoc documentation|
|`GET`|`/openapi.json`|OpenAPI schema|

> **Note:** A FAIRness assessment endpoint (`/api/fairness`) exists in the codebase but is currently **disabled** and not registered. It is not usable in this version.

---

# Configuration

CoMET's backend/CLI behavior can be adjusted via environment variables (all optional, with defaults):

|Variable|Default|Description|
|---|---|---|
|`COMET_SCHEMAS_PATH`|internal empty schema folder|Path to the directory containing schema YAML files (`codemeta.yaml`, `connoss.yaml`, `maSMP.yaml`). **Must be set explicitly for manual installs** — see [Manual](#manual).|
|`API_TITLE`|`Metadata Extractor API`|Title shown in Swagger/OpenAPI docs|
|`API_VERSION`|`1.0.0`|Version shown in Swagger/OpenAPI docs|
|`API_DESCRIPTION`|`Extract metadata from code repositories (GitHub)`|Description shown in Swagger/OpenAPI docs|
|`CORS_ORIGINS`|`["*"]`|Allowed CORS origins|
|`CORS_ALLOW_CREDENTIALS`|`true`|Whether CORS allows credentials|
|`CORS_ALLOW_METHODS`|`["*"]`|Allowed CORS methods|
|`CORS_ALLOW_HEADERS`|`["*"]`|Allowed CORS headers|
|`LLM_API_KEY`|none|API key for LLM-based enrichment (optional)|
|`LLM_MODEL`|`llama-3.1-70b-versatile`|LLM model used for enrichment|
|`LLM_PROVIDER`|`groq`|LLM provider used for enrichment|
|`LOG_LEVEL`|`INFO`|Logging verbosity|
|`GITHUB_TOKEN`|none|GitHub token used by the CLI/API for authenticated requests|
|`GITLAB_TOKEN`|none|GitLab token used by the CLI/API for authenticated requests|

You can set these in a `.env` file at `backend-migration/` (auto-loaded) or export them in your shell.

⚠️ **Security note:** The default CORS configuration (`*` origins/methods/headers with credentials allowed) is permissive and intended for development only. If you deploy CoMET's API publicly, restrict `CORS_ORIGINS` to known frontend domains.

---

# License

CoMET is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See [`LICENSE`](LICENSE) for the full text.
