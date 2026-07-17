"""Deterministic tests for the multi-LLM dispatcher (no network / no real keys)."""
import storyforge.llm as llm


def _fake_openai(monkeypatch, text="openai-output"):
    class Msg:
        content = text

    class Choice:
        message = Msg()

    class Resp:
        choices = [Choice()]

    class Client:
        def __init__(self, *a, **k):
            pass

        class chat:
            class completions:
                @staticmethod
                def create(*a, **k):
                    return Resp()

    monkeypatch.setattr(llm, "_openai_client", lambda cfg, compatible=False: Client())


def test_openai_provider_used(monkeypatch):
    _fake_openai(monkeypatch)
    out = llm.generate("hi", llm.LLMConfig.from_dict({"provider": "openai", "model": "gpt-4o-mini"}))
    assert out == "openai-output"


def test_openai_compatible_uses_base_url(monkeypatch):
    captured = {}

    class Client:
        def __init__(self, api_key, base_url=None):
            captured["base_url"] = base_url

        class chat:
            class completions:
                @staticmethod
                def create(*a, **k):
                    class M:
                        content = "compat"

                    class Message:
                        message = M()

                    class R:
                        choices = [Message()]

                    return R()

    monkeypatch.setattr(llm, "_openai_client", lambda cfg, compatible=False: Client(cfg.api_key or "x", cfg.base_url))
    out = llm.generate(
        "hi",
        llm.LLMConfig.from_dict(
            {"provider": "openai-compatible", "model": "x", "base_url": "https://example/v1"}
        ),
    )
    assert out == "compat"
    assert captured["base_url"] == "https://example/v1"


def test_anthropic_provider(monkeypatch):
    import anthropic as _a

    class Block:
        type = "text"
        text = "claude-output"

    class Resp:
        content = [Block()]

    class Client:
        def __init__(self, *a, **k):
            pass

        class messages:
            @staticmethod
            def create(*a, **k):
                return Resp()

    # _generate_anthropic does `import anthropic` then anthropic.Anthropic(...)
    monkeypatch.setattr(_a, "Anthropic", lambda *a, **k: Client())
    out = llm.generate(
        "hi",
        llm.LLMConfig.from_dict(
            {"provider": "anthropic", "model": "claude-3-5-sonnet-latest", "api_key": "test-key"}
        ),
    )
    assert out == "claude-output"


def test_default_provider_falls_to_gemini(monkeypatch):
    # default with no server GEMINI_API_KEY should raise a clear error (not crash)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    try:
        llm.generate("hi", llm.LLMConfig.from_dict({"provider": "default"}))
        assert False, "expected error when no key"
    except RuntimeError as e:
        assert "Gemini" in str(e)


def test_strip_think_removes_reasoning_blocks():
    out = llm._strip_think("<think>reasoning here</think>\nReal answer.")
    assert out == "Real answer."
