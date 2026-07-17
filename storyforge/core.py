"""StoryForge core logic.

Two primitives mirror the architecture diagram's Core Logic block:

    get_realtime_info(query)        -> Tavily real-time search + Gemini summary
    generate_video_script(info)     -> Gemini short-form video script

research_and_script(query) chains them end-to-end.

Everything here is provider code with no Streamlit / MCP coupling, so it can
be imported by the Streamlit app, the MCP server, tests, or a plain script.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

# Load .env once at import time (GEMINI_API_KEY, TAVILY_API_KEY).
load_dotenv()

import storyforge.llm as llm

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Fallback chain: when the primary model is out of quota (429) or deprecated
# (404), try the next available model instead of failing the whole request.
GEMINI_FALLBACK_MODELS = [
    m for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.0-flash,gemini-2.0-flash-lite").split(",") if m
]
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))


class StoryForgeError(RuntimeError):
    """Base error for StoryForge failures."""


class MissingKeyError(StoryForgeError):
    """Raised when a required API key is not configured."""


class QuotaExhaustedError(StoryForgeError):
    """Raised when every Gemini model in the fallback chain is rate-limited."""


@dataclass
class ResearchResult:
    """Structured output of a real-time research pass."""

    query: str
    summary: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    raw_answer: str | None = None

    @property
    def source_urls(self) -> list[str]:
        return [s.get("url", "") for s in self.sources if s.get("url")]


# --------------------------------------------------------------------------- #
# Lazy client construction (so importing the module never crashes without keys)
# --------------------------------------------------------------------------- #
def _require_key(name: str) -> str:
    key = os.getenv(name)
    if not key:
        raise MissingKeyError(
            f"{name} is not set. Add it to your .env file or environment. "
            f"See .env.example."
        )
    return key


def _tavily_client():
    from tavily import TavilyClient

    return TavilyClient(api_key=_require_key("TAVILY_API_KEY"))


def _gemini_client():
    from google import genai

    return genai.Client(api_key=_require_key("GEMINI_API_KEY"))


def _gemini_generate(prompt: str, *, model: str | None = None) -> str:
    """Generate content, falling back through the model chain on 429/quota errors.

    A free-tier Gemini key has a small per-model daily limit (e.g. 20 requests
    for gemini-2.5-flash). When that model is exhausted we transparently retry
    the next model in the chain instead of failing the whole request.
    """
    gemini = _gemini_client()
    models = [model or GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]
    last_exc: Exception | None = None
    for m in models:
        try:
            resp = gemini.models.generate_content(model=m, contents=prompt)
            return (resp.text or "").strip()
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            # Skip to the next model on quota (429) or deprecated/unavailable
            # (404) errors. Anything else is a genuine failure.
            if (
                "429" in msg
                or "RESOURCE_EXHAUSTED" in msg
                or "quota" in msg.lower()
                or "404" in msg
                or "NOT_FOUND" in msg
            ):
                last_exc = exc
                continue
            raise StoryForgeError(f"Gemini generation failed: {exc}") from exc
    raise QuotaExhaustedError(
        "All Gemini models are out of free-tier quota right now. "
        "Try again later, or add a paid Gemini key / raise your quota."
    )


# --------------------------------------------------------------------------- #
# Primitive 1: real-time research
# --------------------------------------------------------------------------- #
def get_realtime_info(query: str, *, max_results: int | None = None, llm_config: dict | None = None) -> ResearchResult:
    """Fetch the latest information about ``query`` and summarize it.

    1. Tavily performs a real-time web search (advanced depth, includes an
       LLM-generated answer + ranked source snippets).
    2. An LLM (user-chosen provider, default server Gemini) condenses the
       findings into a tight, factual research brief suitable for scripting.

    ``llm_config`` is an optional dict (provider/model/api_key/base_url) so a
    user can bring their own model instead of the server's Gemini key.
    """
    query = (query or "").strip()
    if not query:
        raise StoryForgeError("query must be a non-empty string")

    n = max_results or TAVILY_MAX_RESULTS

    tavily = _tavily_client()
    try:
        search = tavily.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            max_results=n,
        )
    except Exception as exc:  # network / auth / quota
        raise StoryForgeError(f"Tavily search failed: {exc}") from exc

    results = search.get("results", []) or []
    tavily_answer = search.get("answer") or ""

    # Build a compact context block for the summarizer.
    context_lines = []
    if tavily_answer:
        context_lines.append(f"Quick answer: {tavily_answer}\n")
    for i, r in enumerate(results, 1):
        title = r.get("title", "").strip()
        content = (r.get("content", "") or "").strip()
        url = r.get("url", "").strip()
        context_lines.append(f"[{i}] {title}\n{content}\nSource: {url}\n")
    context = "\n".join(context_lines) or "No results found."

    prompt = (
        "You are a research analyst. Using ONLY the search findings below, "
        "write a concise, factual research brief about the topic. Focus on the "
        "most recent, interesting, and verifiable facts. Use short paragraphs "
        "and bullet points where helpful. Do not invent details.\n\n"
        f"TOPIC: {query}\n\n"
        f"SEARCH FINDINGS:\n{context}\n\n"
        "RESEARCH BRIEF:"
    )

    try:
        summary = llm.generate(prompt, llm.LLMConfig.from_dict(llm_config))
    except RuntimeError as exc:  # noqa: BLE001  (QuotaExhaustedError propagates)
        raise StoryForgeError(f"Summarization failed: {exc}") from exc

    if not summary:
        # Fall back to Tavily's own answer rather than returning nothing.
        summary = tavily_answer or "No summary could be generated."

    return ResearchResult(
        query=query,
        summary=summary,
        sources=[
            {"title": r.get("title", ""), "url": r.get("url", "")} for r in results
        ],
        raw_answer=tavily_answer or None,
    )


# --------------------------------------------------------------------------- #
# Primitive 2: script generation
# --------------------------------------------------------------------------- #
def generate_video_script(
    info_text: str,
    *,
    topic: str | None = None,
    duration_seconds: int = 45,
    tone: str = "energetic and engaging",
    llm_config: dict | None = None,
) -> str:
    """Turn a research brief into a short-form video script.

    Optimized for YouTube Shorts / Instagram Reels: a scroll-stopping hook,
    punchy body beats, and a call-to-action, with on-screen visual cues.
    """
    info_text = (info_text or "").strip()
    if not info_text:
        raise StoryForgeError("info_text must be a non-empty string")

    topic_line = f"TOPIC: {topic}\n" if topic else ""

    prompt = (
        "You are an expert short-form video scriptwriter for YouTube Shorts "
        "and Instagram Reels. Write a script for a vertical video that is "
        f"about {duration_seconds} seconds long. Tone: {tone}.\n\n"
        "Structure the script EXACTLY like this:\n"
        "1. HOOK (0-3s): one scroll-stopping line.\n"
        "2. BODY: 3-5 punchy beats delivering the key facts. Each beat on its "
        "own line, prefixed with a timestamp range.\n"
        "3. CTA: a short call-to-action (follow / comment / etc).\n\n"
        "For each spoken beat, add a bracketed VISUAL cue describing what is "
        "on screen, like [VISUAL: ...]. Keep narration tight and punchy — this "
        "is spoken out loud, not read.\n\n"
        f"{topic_line}"
        f"RESEARCH BRIEF:\n{info_text}\n\n"
        "SCRIPT:"
    )

    try:
        script = llm.generate(prompt, llm.LLMConfig.from_dict(llm_config))
    except RuntimeError as exc:  # noqa: BLE001  (QuotaExhaustedError propagates)
        raise StoryForgeError(f"Script generation failed: {exc}") from exc

    if not script:
        raise StoryForgeError("The model returned an empty script.")
    return script


# --------------------------------------------------------------------------- #
# Convenience: full pipeline
# --------------------------------------------------------------------------- #
def research_and_script(
    query: str,
    *,
    duration_seconds: int = 45,
    tone: str = "energetic and engaging",
    max_results: int | None = None,
    llm_config: dict | None = None,
) -> dict[str, Any]:
    """Run the full pipeline: research a topic, then script it.

    Returns a dict with ``summary``, ``script``, and ``sources``.
    """
    research = get_realtime_info(query, max_results=max_results, llm_config=llm_config)
    script = generate_video_script(
        research.summary,
        topic=query,
        duration_seconds=duration_seconds,
        tone=tone,
        llm_config=llm_config,
    )
    return {
        "query": query,
        "summary": research.summary,
        "script": script,
        "sources": research.sources,
    }
