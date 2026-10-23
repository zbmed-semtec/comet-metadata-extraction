# LLM Plugin

Optional LLM-assisted README extraction on top of the deterministic metadata pipeline.

## Enable

In `backend-migration/.env`:

```env
COMET_LLM_ENABLED=true
COMET_LLM_PROVIDER=ollama
COMET_LLM_MODEL=qwen2.5:7b
COMET_LLM_BASE_URL=http://127.0.0.1:11435
```

- When `COMET_LLM_ENABLED=false`, LLM extractors are not operational.
- When enabled with `provider=ollama`, bootstrap starts Ollama, pulls the model if needed, and warms it up.

Platform tokens (faster / private repos) are separate from the LLM plugin:

```bash
export GITHUB_TOKEN=...
export GITLAB_TOKEN=...
```

## Layout

| File | Role |
|---|---|
| `bootstrap.py` | Start/prepare Ollama when configured |
| `config.py` | Load `prompt_engineering.yaml` |
| `prompt.py` | Build per-property extraction prompts |
| `provider.py` | Call Ollama / vLLM |
| `retrieval.py` | Chunk README text and rank relevant sections |
| `heuristics.py` | Isolated SPDX license pattern match (no LLM) |
| `extraction.py` | `extract_property`, JSON parse, per-property extractor classes |
| `collection.py` | Re-exports extractor classes for platforms |
| `confidence.py` | Clamp confidence scores |

## Plugins

One extractor per property (wired for GitHub / GitLab / Codeberg):

- `name`, `description`, `alternateNames`, `applicationCategory`, `contact`
- `buildInstructions`, `installation`

## Debug script

From `backend-migration/`:

```bash
python -m app.layer_3.plugins.llm.scripts.llm_property_debug \
  --repo-url https://github.com/owner/repo \
  --properties name description alternateNames \
  --output-file llm_property_results.json
```