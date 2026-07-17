"""Deterministic tests for the Gemini model-fallback chain (no network/quota)."""
import importlib

import storyforge.core as core


def _install_fake_gemini(behaviors):
    """Patch core._gemini_client to return a fake client whose
    models.generate_content raises/succeeds per `behaviors` (list of call # -> exc/str)."""
    calls = {"n": 0}

    class FakeResp:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents):
            i = calls["n"]
            calls["n"] += 1
            b = behaviors[i] if i < len(behaviors) else behaviors[-1]
            if isinstance(b, Exception):
                raise b
            return FakeResp(b)

    class FakeClient:
        models = FakeModels()

    import storyforge.core as c

    c._gemini_client = lambda: FakeClient()
    return calls


def test_fallback_to_second_model_on_429(monkeypatch):
    # primary 429s (quota), fallback succeeds
    import google.genai

    _install_fake_gemini(
        [
            RuntimeError("429 RESOURCE_EXHAUSTED for gemini-2.5-flash"),
            "Fallback summary text",
        ]
    )
    out = core._gemini_generate("ignored prompt")
    assert out == "Fallback summary text"


def test_all_models_exhausted_raises_quota_error(monkeypatch):
    _install_fake_gemini(
        [
            RuntimeError("429 RESOURCE_EXHAUSTED model a"),
            RuntimeError("429 RESOURCE_EXHAUSTED model b"),
        ]
    )
    try:
        core._gemini_generate("x")
        assert False, "expected QuotaExhaustedError"
    except core.QuotaExhaustedError:
        pass


def test_deprecated_404_model_is_skipped(monkeypatch):
    # gemini-2.5-flash-lite returns 404 (deprecated for new users) -> next model used
    _install_fake_gemini(
        [
            RuntimeError("404 NOT_FOUND models/gemini-2.5-flash-lite"),
            "Summary via working model",
        ]
    )
    out = core._gemini_generate("x")
    assert out == "Summary via working model"


def test_real_error_not_silently_falled_through(monkeypatch):
    # A genuine (non-quota) error should propagate immediately, not be swallowed.
    _install_fake_gemini([RuntimeError("500 INTERNAL some bug")])
    try:
        core._gemini_generate("x")
        assert False, "expected StoryForgeError"
    except core.StoryForgeError as e:
        assert "some bug" in str(e)
