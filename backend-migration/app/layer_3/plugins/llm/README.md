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
