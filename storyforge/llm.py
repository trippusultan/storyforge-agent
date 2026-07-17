"""Provider-agnostic LLM generation for StoryForge.

Users can bring ANY model via their own key — not just the server's Gemini key:
  - "gemini"    : Google Gemini (uses server GEMINI_API_KEY by default)
  - "openai"    : OpenAI (gpt-4o-mini, gpt-4o, ...) — user supplies OPENAI_API_KEY
  - "anthropic" : Claude (claude-3-5-sonnet, ...) — user supplies ANTHROPIC_API_KEY
  - "ollama"    : local Ollama at http://localhost:11434 — no key needed
  - "openai-compatible" : any OpenAI-style endpoint (OpenRouter, Together, Groq,
                          local vLLM, etc.) via base_url + api_key

The ForgeRequest carries an optional `llm` config block. When absent or provider
is "default", the server falls back to its own Gemini key.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv()

# Server-side Gemini fallback chain (used when the user picks "default").
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_FALLBACK_MODELS = [
    m for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash").split(",") if m
]


@dataclass
class LLMConfig:
    """User-supplied model choice for a single Forge call."""

    provider: str = "default"  # default | gemini | openai | anthropic | ollama | openai-compatible
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None

    @classmethod
    def from_dict(cls, d: dict | None) -> "LLMConfig":
        if not d:
            return cls()
        return cls(
            provider=(d.get("provider") or "default").lower(),
            model=d.get("model") or None,
            api_key=d.get("api_key") or None,
            base_url=d.get("base_url") or None,
        )


def _strip_think(text: str) -> str:
    """Remove DeepSeek/llama 'thinking' blocks if a model emits them."""
    if "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
    return text.strip()


def generate(prompt: str, cfg: LLMConfig | None = None) -> str:
    """Generate text with the chosen provider. Returns cleaned text."""
    cfg = cfg or LLMConfig()
    provider = cfg.provider

    if provider in ("default", "gemini", "google"):
        return _generate_gemini(prompt, cfg)
    if provider == "openai":
        return _generate_openai(prompt, cfg)
    if provider == "anthropic":
        return _generate_anthropic(prompt, cfg)
    if provider == "ollama":
        return _generate_ollama(prompt, cfg)
    if provider == "openai-compatible":
        return _generate_openai_compatible(prompt, cfg)
    raise ValueError(f"Unknown LLM provider: {provider}")


# --------------------------------------------------------------------------- #
# Gemini (server key + fallback chain reused from core)
# --------------------------------------------------------------------------- #
def _generate_gemini(prompt: str, cfg: LLMConfig) -> str:
    from google import genai

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "No Gemini API key configured on the server. Add GEMINI_API_KEY to .env "
            "or choose a different provider in the Model settings."
        )
    client = genai.Client(api_key=key)
    model = cfg.model or GEMINI_MODEL
    models = [model, *GEMINI_FALLBACK_MODELS]
    last_exc: Exception | None = None
    for m in models:
        try:
            resp = client.models.generate_content(model=m, contents=prompt)
            return _strip_think(resp.text or "")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if (
                "429" in msg
                or "RESOURCE_EXHAUSTED" in msg
                or "quota" in msg.lower()
                or "404" in msg
                or "NOT_FOUND" in msg
            ):
                last_exc = exc
                continue
            raise RuntimeError(f"Gemini generation failed: {exc}") from exc
    raise RuntimeError(
        "All Gemini models are out of free-tier quota right now. Try again later, "
        "or pick a different provider (OpenAI/Anthropic/Ollama) in Model settings."
    )


# --------------------------------------------------------------------------- #
# OpenAI + compatible
# --------------------------------------------------------------------------- #
def _openai_client(cfg: LLMConfig, *, compatible: bool = False):
    from openai import OpenAI

    if compatible or cfg.provider == "openai-compatible":
        api_key = cfg.api_key or os.getenv("OPENAI_API_KEY") or "sk-noauth"
        return OpenAI(api_key=api_key, base_url=cfg.base_url or None)
    api_key = cfg.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OpenAI API key missing. Enter it in Model settings or set OPENAI_API_KEY."
        )
    return OpenAI(api_key=api_key, base_url=cfg.base_url or None)


def _generate_openai(prompt: str, cfg: LLMConfig) -> str:
    client = _openai_client(cfg, compatible=False)
    model = cfg.model or "gpt-4o-mini"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return _strip_think(resp.choices[0].message.content or "")


def _generate_openai_compatible(prompt: str, cfg: LLMConfig) -> str:
    if not cfg.base_url:
        raise RuntimeError("OpenAI-compatible provider requires a Base URL.")
    client = _openai_client(cfg, compatible=True)
    model = cfg.model or "local-model"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return _strip_think(resp.choices[0].message.content or "")


# --------------------------------------------------------------------------- #
# Anthropic
# --------------------------------------------------------------------------- #
def _generate_anthropic(prompt: str, cfg: LLMConfig) -> str:
    import anthropic

    api_key = cfg.api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Anthropic API key missing. Enter it in Model settings or set ANTHROPIC_API_KEY."
        )
    client = anthropic.Anthropic(api_key=api_key)
    model = cfg.model or "claude-3-5-sonnet-latest"
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    return _strip_think(text)


# --------------------------------------------------------------------------- #
# Ollama (local, no key)
# --------------------------------------------------------------------------- #
def _generate_ollama(prompt: str, cfg: LLMConfig) -> str:
    import requests

    base = (cfg.base_url or "http://localhost:11434").rstrip("/")
    model = cfg.model or "llama3.1"
    try:
        resp = requests.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return _strip_think(resp.json().get("response", ""))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Ollama request failed ({model} at {base}): {exc}. "
            "Is Ollama running? Try `ollama pull llama3.1`."
        ) from exc
