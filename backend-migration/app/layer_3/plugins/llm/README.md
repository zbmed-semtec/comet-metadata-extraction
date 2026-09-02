# LLM Plugin

This plugin adds optional LLM-assisted extraction on top of the normal metadata pipeline.

## Requirements

- Python dependencies installed from the backend-migration environment.
- A running local LLM provider.
- Ollama is the supported auto-start path in this codebase.
- If you use `provider=vllm`, start that service yourself before running extraction.

## Terminal Tokens

The LLM plugin itself does not currently read an API token.

Better to export the access token to read the repository much faster and helps at attempting less number of trails to get to the repository.

```bash
export GITHUB_TOKEN=your_github_token
export GITLAB_TOKEN=your_gitlab_token
```

You can also pass the token per command with `--token`, but exporting it is convenient for repeated runs.

Token creation links:

- GitHub personal access tokens: https://docs.github.com/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- GitLab personal access tokens: https://docs.gitlab.com/user/profile/personal_access_tokens/
- Codeberg personal access tokens: https://docs.codeberg.org/advanced/access-token/

## `.env` File

The application reads `backend-migration/.env` on startup. For this plugin, keep the following entries there:

```env
COMET_SCHEMAS_PATH=/absolute/path/to/backend-migration/schemas/
README_LLM_ENABLED=false
README_LLM_PROVIDER=ollama
README_LLM_MODEL=qwen2.5:7b
README_LLM_BASE_URL=http://127.0.0.1:11435
```

Notes:

- `COMET_SCHEMAS_PATH` must point to the local schemas directory.
- `README_LLM_ENABLED` is the master switch for the LLM path.
- `README_LLM_PROVIDER` currently works with `ollama` or `vllm`.
- `README_LLM_MODEL` must match a model available from the selected provider.
- `README_LLM_BASE_URL` accepts either a full URL or a host and port such as `127.0.0.1:11435`.
- `OLLAMA_HOST` is also accepted for compatibility, but `README_LLM_BASE_URL` is the preferred setting here.

## How Enable / Disable Works

- When `README_LLM_ENABLED=false`, the LLM steps are skipped and the extraction code returns without calling the provider.
- When `README_LLM_ENABLED=true` and the provider is `ollama`, the bootstrap step will try to start Ollama, confirm the model exists, pull it if needed, and warm it up.
- When `README_LLM_ENABLED=true` and the provider is not `ollama`, the bootstrap step is skipped and the provider must already be running.
- The extraction code checks the same flag again, so disabling it fully turns off the LLM-assisted path.

## Quick Start

1. Install the backend dependencies.
2. Export `GITHUB_TOKEN` or `GITLAB_TOKEN` if you need private repository access.
3. Set the LLM values in `backend-migration/.env`.
4. Set `README_LLM_ENABLED=true` to turn the LLM plugin on.
5. Set it back to `false` to disable the LLM plugin again.

## Folder Structure

The plugin repository layout (files in this folder) and their primary responsibilities:

- `__init__.py`: plugin package entry.
- `bootstrap.py`: start/prepare the LLM provider (pull or warm models for `ollama`).
- `config.py`: configuration helpers and `.env` mapping for the plugin.
- `provider.py`: provider abstraction and clients (Ollama / vLLM integrations).
- `retrieval.py`: code to fetch repository files, blobs, or external documents for processing.
- `prompt.py`: prompt templates and prompt-building helpers used to query the model.
- `extraction.py`: orchestration that runs prompts against the model and parses results.
- `collection.py`: gathers and transforms extracted metadata into the pipeline shape.
- `confidence.py`: scoring/heuristics for evaluating extraction certainty and filtering results.
- `heuristics.py`: rule-based post-processing to normalize or correct extracted values.
- `__pycache__/`: Python bytecode cache (auto-generated).

## Workflow (line of work)

A concise, linear view of what the LLM plugin does during a run:

1. Bootstrap: when enabled, `bootstrap.py` ensures the configured provider/model is available (auto-starts Ollama when configured).
2. Retrieval: `retrieval.py` collects repository files, README contents, or other target documents to analyze.
3. Prompting: `prompt.py` crafts model prompts using templates and the retrieved content.
4. Provider call: `provider.py` sends the prompts to the selected LLM (Ollama, vLLM) and returns raw responses.
5. Extraction: `extraction.py` interprets model outputs, extracts structured metadata, and applies initial parsing.
6. Confidence & heuristics: `confidence.py` and `heuristics.py` score and refine results, removing low-confidence or inconsistent entries.
7. Collection: `collection.py` assembles the final metadata objects and hands them back to the main pipeline for storage or further processing.

This flow is designed so the LLM augments — not replaces — deterministic heuristics, and all LLM-derived values are validated and scored before being merged into the main metadata pipeline.
