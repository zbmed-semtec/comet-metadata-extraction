from __future__ import annotations

import os
import shutil
import sys
import subprocess
import time
from urllib.parse import urlparse

import requests

from app.config.settings import settings
from app.layer_3.plugins.llm.config import SYSTEM_PROMPTS


def check_provider_ready(provider: str, model: str, base_url: str, timeout: int = 10) -> tuple[bool, str]:
    """Verify that a supported local provider is reachable and hosts a model."""
    provider = provider.lower().strip()

    if provider == "ollama":
        endpoint = base_url.rstrip("/") + "/api/tags"
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()
            names = [item.get("name", "") for item in response.json().get("models", [])]
            if model in names:
                return True, f"Ollama ready. Model {model} found."
            return False, f"Model {model} not found. Available: {names}"
        except Exception as exc:
            return False, f"Cannot reach Ollama: {exc}"

    if provider == "vllm":
        endpoint = base_url.rstrip("/") + "/v1/models"
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()
            names = [item.get("id", "") for item in response.json().get("data", [])]
            if model in names:
                return True, f"vLLM ready. Model {model} found."
            return False, f"Model {model} not found. Available: {names}"
        except Exception as exc:
            return False, f"Cannot reach vLLM: {exc}"

    return False, f"Unsupported provider: {provider}"


def _ollama_host_from_base_url(base_url: str) -> str:
    """Convert a base URL into the host format Ollama expects."""
    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434
    return f"{hostname}:{port}"


def ensure_ollama_running(base_url: str, timeout: int = 10) -> tuple[bool, str]:
    """Start `ollama serve` if needed and wait briefly for it to accept requests."""
    endpoint = base_url.rstrip("/") + "/api/tags"

    try:
        response = requests.get(endpoint, timeout=2)
        response.raise_for_status()
        return True, "Ollama already running."
    except Exception:
        pass

    ollama_binary = shutil.which("ollama")
    if not ollama_binary:
        return False, "Ollama binary not found in PATH."

    env = os.environ.copy()
    env["OLLAMA_HOST"] = _ollama_host_from_base_url(base_url)

    try:
        subprocess.Popen(
            [ollama_binary, "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return False, f"Failed to start Ollama: {exc}"

    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(endpoint, timeout=2)
            response.raise_for_status()
            return True, "Ollama started successfully."
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.5)

    return False, f"Started Ollama but it did not respond within {timeout}s: {last_error}"


def activate_ollama_model(base_url: str, model: str, timeout: int = 420) -> tuple[bool, str]:
    """Warm up an Ollama model once the server is reachable."""
    endpoint = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": "",
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "top_p": 0.7, "num_predict": 1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        return True, f"Ollama model {model} activated."
    except Exception as exc:
        return False, f"Failed to activate Ollama model {model}: {exc}"


def pull_ollama_model(base_url: str, model: str, timeout: int = 300) -> tuple[bool, str]:
    """Pull an Ollama model via the `ollama` CLI and wait until it's available.

    Returns (True, message) if the model is available after pulling, otherwise (False, message).
    """
    ollama_binary = shutil.which("ollama")
    if not ollama_binary:
        return False, "Ollama binary not found in PATH."

    env = os.environ.copy()
    env["OLLAMA_HOST"] = _ollama_host_from_base_url(base_url)

    try:
        # Run `ollama pull <model>` and wait for it to complete (with timeout).
        proc = subprocess.run([ollama_binary, "pull", model], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "ollama pull failed").strip()
            return False, f"ollama pull failed: {err}"
    except Exception as exc:
        return False, f"Failed to run ollama pull: {exc}"

    # After pulling, poll the provider API until the model appears.
    deadline = time.monotonic() + min(30, timeout)
    last_msg = ""
    while time.monotonic() < deadline:
        ready, msg = check_provider_ready("ollama", model, base_url, timeout=2)
        if ready:
            return True, f"Pulled model {model} and is now available."
        last_msg = msg
        time.sleep(0.5)

    return False, f"Model pull did not result in available model within timeout: {last_msg}"


def run_llm(prompt: str, provider: str, model: str, base_url: str, timeout: int = 420) -> str:
    """Submit an extraction prompt to Ollama or vLLM."""
    provider = provider.lower().strip()
    print(f"[enrichment] Using LLM with {provider}:{model}", file=sys.stderr)

    if provider == "ollama":
        endpoint = base_url.rstrip("/") + "/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "top_p": 0.7, "num_predict": 700},
        }
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", "")

    if provider == "vllm":
        endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": str(SYSTEM_PROMPTS.get("json_only", "Return valid JSON only.")).strip()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "top_p": 0.7,
            "max_tokens": 2000,
        }
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    raise RuntimeError(f"Unsupported provider: {provider}")


def resolve_model_config() -> tuple[str, str, str, str]:
    """Read the active LLM provider, model, and endpoint from settings."""
    active_model = str(getattr(settings, "llm_provider", "ollama")).strip().lower()
    provider = str(getattr(settings, "llm_provider", "ollama")).strip().lower()
    model_name = str(getattr(settings, "llm_model", "qwen2.5:7b")).strip()
    base_url = str(getattr(settings, "llm_base_url", "http://127.0.0.1:11435")).strip()
    description = f"{provider}:{model_name}" if model_name else provider
    return active_model, provider, model_name, base_url or description
