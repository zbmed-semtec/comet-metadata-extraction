[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18837374.svg)](https://doi.org/10.5281/zenodo.18837374) 
![Status](https://img.shields.io/badge/repo_status-Active-green)

<p align="center">
  <img src="docs/img/background.gif" width="100%">
</p>

# Code Metadata Extraction Toolkit for Research Software (CoMET-RS)

This project is designed to automate the extraction of metadata from GitHub and GitLab repositories to generate a **machine-actionable** metadata file in JSON-LD that can be included in the repository or use by metadata aggregators and curators. It consists of two main components:

1. **Backend** - A FastAPI-based service built with **Clean Architecture** principles that extracts metadata from GitHub, GitLab, and external sources (OpenAlex, Wayback Machine). The backend follows a layered architecture with clear separation of concerns: domain logic, use cases, adapters, and API endpoints.
2. **Frontend** - A modern **Nuxt 3** application with Vue 3 and TypeScript, providing an intuitive user interface to interact with the metadata extraction service. Features include platform selection, repository input, and comprehensive metadata visualization.

---

## Setting Up and Running the Project

### 1. Running Backend Service

Follow the instructions in the [Backend README](./backend-migration/README.md) to install and run the backend server.

### 2. Running Frontend Application

Follow the steps in the [Frontend README](./frontend-migration/README.md) to set up and start the frontend application.

---

## Running the Project with Docker

To simplify deployment, you can use **Docker** and **Docker Compose** to run the entire project (Nuxt frontend + FastAPI backend).

### 1. Install Docker

Ensure you have Docker installed on your system. You can download and install it from [Docker’s official website](https://www.docker.com/get-started).

### 2. Build and Run the Containers

From the project root, build and start both services:

```sh
docker compose up --build
```

This will:

- Build and start the **backend** (FastAPI) and **frontend** (Nuxt) containers.
- Set up networking so the frontend can call the backend API.

### 3. Access the Application

Once the containers are running:

- **Frontend UI:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8001](http://localhost:8001)
- **API docs (Swagger):** [http://localhost:8001/docs](http://localhost:8001/docs)

### 4. Stopping the Containers

To stop the running containers:

```sh
docker compose down
```

This shuts down and removes the containers but keeps the built images.

---

## Python Package

The backend is also available as a Python package (`comet-rs`) that can be used as a CLI tool or imported as a library in your Python code.

### Installation

```bash
pip install comet-rs
```

Python 3.10+ is required.

### CLI Usage

Extract full metadata from a repository:

```bash
comet-rs extract https://github.com/owner/repo maSMP --with-enrichment
```

Extract a single property with source and confidence:

```bash
comet-rs extract_property https://github.com/owner/repo author
```

### Python API Usage

```python
import os
from app.layer_4.services.metadata_service import run_extraction

# Extract full metadata
jsonld_document, enriched = run_extraction(
    repo_url="https://github.com/owner/repo",
    schema="maSMP",                              # or "CODEMETA"
    access_token=os.getenv("GITHUB_TOKEN"),
    with_enrichment=True,
)

# jsonld_document: maSMP/CODEMETA JSON-LD (dict)
# enriched: per-property source/confidence/category
```

### Authentication

For heavier use or private repositories, set environment variables:

```bash
export GITHUB_TOKEN=ghp_...      # for GitHub repositories
export GITLAB_TOKEN=glpat_...    # for GitLab repositories
```

For more details, see the [PyPI README](./backend-migration/README_PYPI.md).

---

## Contributing

If you want to contribute to this project, feel free to fork the repository, create a new branch, and submit a pull request with your changes.

## License

This project is licensed under the MIT License.
