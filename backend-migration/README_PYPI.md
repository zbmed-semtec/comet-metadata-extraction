# CoMET-RS — Code Metadata Extraction Toolkit for Research Software

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18837374.svg)](https://doi.org/10.5281/zenodo.18837374)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**CoMET-RS** extracts **FAIR** (Findable, Accessible, Interoperable, Reusable), **machine-actionable** metadata from GitHub, GitLab, and Codeberg repositories, and outputs it as JSON-LD conforming to a schema of your choice (`ConnOSS`, `maSMP`, or `CODEMETA`).

It ships as both a **command-line tool** (`comet-rs`) and a **Python library** (`comet_rs`).

- **Source code & full documentation:** https://github.com/zbmed-semtec/comet-metadata-extraction
- **Issue tracker:** https://github.com/zbmed-semtec/comet-metadata-extraction/issues
- **License:** GPL-3.0

## Installation

Requires Python 3.10 or higher.

```bash
pip install comet-rs
```

## CLI usage

After installation, the `comet-rs` command is available on your `PATH`.

```bash
comet-rs --help
```

```
usage: comet-rs [-h] {extract,extract_property,fairness} ...

Extract metadata (and per-property sources) from code repositories, for any
supported schema.
```

### Extract full metadata

```bash
comet-rs extract <url> <schema> [--schema-class SCHEMA_CLASS] [--token TOKEN] [--with-enrichment]
```

- `url` — Repository URL (GitHub, GitLab, or Codeberg).
- `schema` — Schema to use: `connoss`, `maSMP`, or `CODEMETA` (case-insensitive).
- `--schema-class` — Schema class to use (default: `software`).
- `--token` — Personal access token for the platform. If omitted, CoMET-RS looks for `GITHUB_TOKEN`, `GITLAB_TOKEN`, or `CODEBERG_TOKEN` in the environment, based on the repository URL. A token increases API rate limits and allows access to private repositories.
- `--with-enrichment` — Include per-property enrichment metadata (source, confidence, category) alongside the extracted JSON-LD.

Example:

```bash
comet-rs extract https://github.com/zbmed-semtec/comet-metadata-extraction connoss --with-enrichment
```

Output (written to stdout as JSON):

```json
{
  "schema": "connoss",
  "code_url": "https://github.com/zbmed-semtec/comet-metadata-extraction",
  "results": { "...": "JSON-LD metadata document..." },
  "enriched_metadata": { "...": "per-property source/confidence/category..." }
}
```

### Extract a single property

```bash
comet-rs extract_property <url> <property> [--schema SCHEMA] [--schema-class SCHEMA_CLASS] [--token TOKEN]
```

- `url` — Repository URL.
- `property` — Property name, e.g. `name`, `identifier`, `codemeta:referencePublication`, or `codemeta_referencePublication`.
- `--schema` — Schema to use (default: `connoss`).
- `--schema-class` — Schema class to use (default: `software`).
- `--token` — See above.

Example:

```bash
comet-rs extract_property https://github.com/zbmed-semtec/comet-metadata-extraction license
```

Output:

```json
{
  "property_name": "license",
  "property_value": ["GPL-3.0"],
  "source": "github_api",
  "confidence": 0.95
}
```

### FAIRness assessment

```bash
comet-rs fairness <url> [--token TOKEN]
```

Runs a FAIRness assessment of the repository against the `ConnOSS` schema.

Example:

```bash
comet-rs fairness https://github.com/zbmed-semtec/comet-metadata-extraction
```

> **Note:** the FAIRness assessment feature is under active revision upstream and may change or be temporarily limited in future releases.

## Authentication

CoMET-RS works without authentication, but unauthenticated requests are subject to strict API rate limits on GitHub/GitLab/Codeberg, and cannot access private repositories. Provide a token via `--token`, or set one of the following environment variables (selected automatically based on the repository URL):

```bash
export GITHUB_TOKEN=your_github_token
export GITLAB_TOKEN=your_gitlab_token
export CODEBERG_TOKEN=your_codeberg_token
```

## Python API

CoMET-RS can also be used as a library:

```python
import comet_rs

# Full extraction
result = comet_rs.extract_metadata(
    repo_url="https://github.com/zbmed-semtec/comet-metadata-extraction",
    schema_name="connoss",       # or "maSMP" / "CODEMETA"
    schema_class="Software",
    token=None,                  # or rely on GITHUB_TOKEN / GITLAB_TOKEN / CODEBERG_TOKEN
    with_enrichment=True,
)

# Single property
extracted_at, matches = comet_rs.extract_property(
    repo_url="https://github.com/zbmed-semtec/comet-metadata-extraction",
    property_name="author",
    schema_name="connoss",       # or "maSMP" / "CODEMETA"
    schema_class="Software",
    token=None,                  # or rely on GITHUB_TOKEN / GITLAB_TOKEN / CODEBERG_TOKEN
)
for match in matches:
    print(extracted_at, match["profile"], match["value"], match["source"], match["confidence"])
```

## Supported schemas

- **ConnOSS**
- **maSMP**
- **CODEMETA**

## Supported platforms

- GitHub
- GitLab
- Codeberg

## Other ways to run CoMET

CoMET-RS is also available as a web API (via Docker or manual installation) and previously shipped a web frontend (now discontinued/in migration). See the full project documentation on GitHub for Docker Compose instructions, the FastAPI/Swagger backend, and architecture details:
https://github.com/zbmed-semtec/comet-metadata-extraction

## Citation

If you use CoMET-RS in your research, please cite it using the metadata in `CITATION.cff` on the GitHub repository:
https://github.com/zbmed-semtec/comet-metadata-extraction/blob/main/CITATION.cff

## License

CoMET-RS is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](https://github.com/zbmed-semtec/comet-metadata-extraction/blob/main/LICENSE) file for details.