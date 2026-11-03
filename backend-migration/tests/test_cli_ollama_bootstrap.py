from argparse import Namespace

import app.cli as cli


def test_extract_command_bootstraps_ollama_before_running_extraction(monkeypatch):
    calls = []

    monkeypatch.setattr(cli.settings, "llm_enabled", True)
    monkeypatch.setattr(cli.settings, "llm_provider", "ollama")
    monkeypatch.setattr(cli.settings, "llm_model", "qwen2.5:7b")
    monkeypatch.setattr(cli.settings, "llm_base_url", "http://127.0.0.1:11435")

    def fake_ensure_ollama_running(base_url):
        calls.append(("ensure", base_url))
        return True, "Ollama already running."

    def fake_check_provider_ready(provider, model, base_url, timeout=10):
        calls.append(("check", provider, model, base_url, timeout))
        return True, "Ollama ready. Model qwen2.5:7b found."

    def fake_activate_ollama_model(base_url, model, timeout=420):
        calls.append(("activate", base_url, model, timeout))
        return True, "Ollama model qwen2.5:7b activated."

    monkeypatch.setattr(cli, "ensure_ollama_running", fake_ensure_ollama_running)
    monkeypatch.setattr(cli, "check_provider_ready", fake_check_provider_ready)
    monkeypatch.setattr(cli, "activate_ollama_model", fake_activate_ollama_model)
    monkeypatch.setattr(cli, "pull_ollama_model", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pull should not run when model is ready")))
    monkeypatch.setattr(cli, "initialize", lambda: calls.append(("initialize",)))
    monkeypatch.setattr(
        cli,
        "run_extraction",
        lambda **kwargs: calls.append(("run_extraction", kwargs)) or ({"name": "dummy"}, {"enriched": True}),
    )
    monkeypatch.setattr(cli, "_print_json", lambda data: calls.append(("print", data)))

    args = Namespace(
        url="https://github.com/zbmed-semtec/comet-metadata-extraction",
        schema="masmp",
        token=None,
        with_enrichment=False,
        schema_class="SoftwareApplication",
    )

    cli._extract_command(args)

    assert calls[0] == ("ensure", "http://127.0.0.1:11435")
    assert calls[1] == ("check", "ollama", "qwen2.5:7b", "http://127.0.0.1:11435", 10)
    assert calls[2] == ("activate", "http://127.0.0.1:11435", "qwen2.5:7b", 420)
    assert calls[3] == ("initialize",)
    assert calls[4][0] == "run_extraction"
    assert calls[4][1]["repo_url"] == args.url
    assert calls[4][1]["schema_name"] == args.schema
    assert calls[4][1]["access_token"] == args.token
    assert calls[4][1]["with_enrichment"] is False
    assert calls[4][1]["schema_class"] == args.schema_class
    assert calls[5][0] == "print"