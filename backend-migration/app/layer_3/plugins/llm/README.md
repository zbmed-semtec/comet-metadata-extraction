# LLM Plugin

Optional LLM-assisted README extraction on top of the deterministic metadata pipeline.

## Enable

In `backend-migration/.env`:

```env
README_LLM_ENABLED=true
README_LLM_PROVIDER=ollama
README_LLM_MODEL=qwen2.5:7b
README_LLM_BASE_URL=http://127.0.0.1:11435
```

- When `README_LLM_ENABLED=false`, LLM extractors no-op.
- When enabled with `provider=ollama`, bootstrap starts Ollama, pulls the model if needed, and warms it up.
- For `vllm`, start the service yourself before extraction.

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
| `scripts/llm_property_debug.py` | Standalone per-property debug runner |

## Plugins

One extractor per property (wired for GitHub / GitLab / Codeberg):

- `name`, `description`, `alternateNames`, `applicationCategory`, `contact`
- `buildInstructions`, `installation`
- `license` uses the SPDX heuristic first; LLM only if no pattern matches (via `extract_property`, not a dedicated plugin)

## Debug script

From `backend-migration/`:

```bash
python -m app.layer_3.plugins.llm.scripts.llm_property_debug \
  --repo-url https://github.com/owner/repo \
  --properties name description alternateNames \
  --output-file llm_property_results.json
```

Or with a local README:

```bash
python app/layer_3/plugins/llm/scripts/llm_property_debug.py \
  --readme-file /path/to/README.md \
  --output-file llm_property_results.json
```
