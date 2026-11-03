import app.layer_3.plugins.llm.provider as provider


def test_ensure_ollama_running_starts_process_when_endpoint_is_down(monkeypatch):
    calls = {}

    def fake_get(endpoint, timeout):
        calls.setdefault("requests", []).append((endpoint, timeout))

        class DummyResponse:
            def raise_for_status(self):
                raise RuntimeError("unreachable")

        return DummyResponse()

    def fake_which(name):
        calls["which"] = name
        return "/usr/bin/ollama"

    class DummyPopen:
        def __init__(self, args, env=None, stdout=None, stderr=None, start_new_session=None):
            calls["popen"] = {
                "args": args,
                "env": env,
                "stdout": stdout,
                "stderr": stderr,
                "start_new_session": start_new_session,
            }

    monkeypatch.setattr(provider.requests, "get", fake_get)
    monkeypatch.setattr(provider.shutil, "which", fake_which)
    monkeypatch.setattr(provider.subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(provider.time, "sleep", lambda _: None)
    monkeypatch.setattr(provider.time, "monotonic", iter([0, 1, 2, 3, 11]).__next__)

    ready, message = provider.ensure_ollama_running("http://localhost:11435", timeout=1)

    assert ready is False
    assert "did not respond" in message
    assert calls["which"] == "ollama"
    assert calls["popen"]["args"] == ["/usr/bin/ollama", "serve"]
    assert calls["popen"]["env"]["OLLAMA_HOST"] == "localhost:11435"
    assert calls["popen"]["start_new_session"] is True


def test_activate_ollama_model_posts_warmup_request(monkeypatch):
    calls = {}

    def fake_post(endpoint, json, timeout):
        calls["post"] = {"endpoint": endpoint, "json": json, "timeout": timeout}

        class DummyResponse:
            def raise_for_status(self):
                return None

        return DummyResponse()

    monkeypatch.setattr(provider.requests, "post", fake_post)

    ready, message = provider.activate_ollama_model("http://localhost:11435", "qwen2.5:7b", timeout=9)

    assert ready is True
    assert "activated" in message
    assert calls["post"]["endpoint"] == "http://localhost:11435/api/generate"
    assert calls["post"]["json"]["model"] == "qwen2.5:7b"
    assert calls["post"]["json"]["prompt"] == ""
    assert calls["post"]["json"]["keep_alive"] == "10m"
    assert calls["post"]["timeout"] == 9
