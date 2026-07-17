"""StoryForge Agent - core package.

Real-time research + short-form video script generation for YouTube Shorts
and Instagram Reels. Powered by Tavily (real-time web search) and Google
Gemini (summarization + scripting).
"""

from .core import (
    get_realtime_info,
    generate_video_script,
    research_and_script,
    StoryForgeError,
    MissingKeyError,
)

__all__ = [
    "get_realtime_info",
    "generate_video_script",
    "research_and_script",
    "StoryForgeError",
    "MissingKeyError",
]

__version__ = "1.0.0"
