"""Tests for StoryForge core logic.

External APIs (Tavily, Gemini) are mocked so the pipeline logic is verified
without network access or real keys.

Run:
    pytest -q
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Ensure the package is importable when running from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storyforge.core as core  # noqa: E402
from storyforge.core import (  # noqa: E402
    MissingKeyError,
    StoryForgeError,
    generate_video_script,
    get_realtime_info,
    research_and_script,
)


@pytest.fixture
def fake_keys(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")


@pytest.fixture
def mock_tavily(monkeypatch):
    client = MagicMock()
    client.search.return_value = {
        "answer": "Quick answer about the topic.",
        "results": [
            {
                "title": "Result One",
                "content": "Fresh fact number one.",
                "url": "https://example.com/1",
            },
            {
                "title": "Result Two",
                "content": "Fresh fact number two.",
                "url": "https://example.com/2",
            },
        ],
    }
    monkeypatch.setattr(core, "_tavily_client", lambda: client)
    return client


@pytest.fixture
def mock_gemini(monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        text="This is the generated text output."
    )
    monkeypatch.setattr(core, "_gemini_client", lambda: client)
    return client


def test_get_realtime_info_happy_path(fake_keys, mock_tavily, mock_gemini):
    result = get_realtime_info("space telescopes")
    assert result.query == "space telescopes"
    assert result.summary == "This is the generated text output."
    assert len(result.sources) == 2
    assert result.source_urls == ["https://example.com/1", "https://example.com/2"]
    mock_tavily.search.assert_called_once()
    mock_gemini.models.generate_content.assert_called_once()


def test_get_realtime_info_empty_query_raises():
    with pytest.raises(StoryForgeError):
        get_realtime_info("   ")


def test_generate_video_script_happy_path(fake_keys, mock_gemini):
    script = generate_video_script("A research brief.", topic="AI news")
    assert script == "This is the generated text output."
    mock_gemini.models.generate_content.assert_called_once()
    # duration + tone should be embedded in the prompt.
    prompt = mock_gemini.models.generate_content.call_args.kwargs["contents"]
    assert "seconds long" in prompt
    assert "AI news" in prompt


def test_generate_video_script_empty_raises():
    with pytest.raises(StoryForgeError):
        generate_video_script("")


def test_generate_video_script_empty_response_raises(fake_keys, monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="")
    monkeypatch.setattr(core, "_gemini_client", lambda: client)
    with pytest.raises(StoryForgeError):
        generate_video_script("brief")


def test_research_and_script_full_pipeline(fake_keys, mock_tavily, mock_gemini):
    out = research_and_script("quantum computing", duration_seconds=30)
    assert set(out) == {"query", "summary", "script", "sources"}
    assert out["query"] == "quantum computing"
    assert out["summary"] == "This is the generated text output."
    assert out["script"] == "This is the generated text output."
    # research (1) + script (1) Gemini calls.
    assert mock_gemini.models.generate_content.call_count == 2


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Real client construction path should fail fast without keys.
    with pytest.raises(MissingKeyError):
        core.get_realtime_info("anything")
