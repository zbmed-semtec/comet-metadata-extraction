from __future__ import annotations

import sys

from app.config.settings import settings
from app.layer_3.plugins.llm.provider import (
    activate_ollama_model,
    check_provider_ready,
    ensure_ollama_running,
    pull_ollama_model,
    resolve_model_config,
)


def bootstrap_ollama_if_configured(*, log_prefix: str, strict: bool) -> bool:
    """Start and warm up Ollama when the local LLM provider is configured."""
    if not settings.llm_enabled:
        return False

    _, provider, model, base_url = resolve_model_config()
    if provider != "ollama":
        return False

    ready, message = ensure_ollama_running(base_url)
    print(f"[{log_prefix}] {message}", file=sys.stderr)
    if not ready:
        if strict:
            raise RuntimeError(f"Ollama bootstrap failed: {message}")
        return False

    model_ready, model_message = check_provider_ready(provider, model, base_url)
    print(f"[{log_prefix}] {model_message}", file=sys.stderr)
    if not model_ready:
        pulled, pull_message = pull_ollama_model(base_url, model)
        print(f"[{log_prefix}] {pull_message}", file=sys.stderr)
        if not pulled:
            if strict:
                raise RuntimeError(f"Ollama model pull failed: {pull_message}")
            return False

    activated, activation_message = activate_ollama_model(base_url, model)
    print(f"[{log_prefix}] {activation_message}", file=sys.stderr)
    if not activated:
        if strict:
            raise RuntimeError(f"Ollama activation failed: {activation_message}")
        return False

    return True