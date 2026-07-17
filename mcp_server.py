"""StoryForge MCP server (FastMCP).

Exposes StoryForge's research + scripting capabilities as MCP tools so any
MCP client (Claude Desktop, etc.) can call them.

Run:
    python mcp_server.py            # stdio transport (Claude Desktop)
    fastmcp run mcp_server.py       # via fastmcp CLI

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "storyforge": {
          "command": "python",
          "args": ["C:/Users/Spoidy/youtube-content-agent/mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

from fastmcp import FastMCP

from storyforge.core import (
    generate_video_script,
    get_realtime_info,
    research_and_script,
)

mcp = FastMCP(
    name="StoryForge",
    instructions=(
        "Tools for real-time topic research and short-form video scripting "
        "(YouTube Shorts / Instagram Reels). Use get_latest_info_mcp to "
        "research a topic, then get_video_script_mcp to turn the research "
        "into a script. Or use research_and_script_mcp to do both at once."
    ),
)


@mcp.tool
def get_latest_info_mcp(query: str, max_results: int = 5) -> dict:
    """Research a topic with real-time web search and return a factual brief.

    Args:
        query: The topic to research.
        max_results: How many web sources to pull (default 5).

    Returns:
        A dict with the research ``summary`` and its ``sources``.
    """
    result = get_realtime_info(query, max_results=max_results)
    return {
        "query": result.query,
        "summary": result.summary,
        "sources": result.sources,
    }


@mcp.tool
def get_video_script_mcp(
    info_text: str,
    topic: str = "",
    duration_seconds: int = 45,
    tone: str = "energetic and engaging",
) -> str:
    """Turn a research brief into a short-form video script.

    Args:
        info_text: The research brief / source material to script from.
        topic: Optional topic name for context.
        duration_seconds: Target video length in seconds (default 45).
        tone: Desired tone of the script.

    Returns:
        A formatted short-form video script with hook, beats, visuals, and CTA.
    """
    return generate_video_script(
        info_text,
        topic=topic or None,
        duration_seconds=duration_seconds,
        tone=tone,
    )


@mcp.tool
def research_and_script_mcp(
    query: str,
    duration_seconds: int = 45,
    tone: str = "energetic and engaging",
    max_results: int = 5,
) -> dict:
    """Full pipeline: research a topic and generate a video script in one call.

    Args:
        query: The topic to research and script.
        duration_seconds: Target video length in seconds (default 45).
        tone: Desired tone of the script.
        max_results: How many web sources to pull (default 5).

    Returns:
        A dict with ``summary``, ``script``, and ``sources``.
    """
    return research_and_script(
        query,
        duration_seconds=duration_seconds,
        tone=tone,
        max_results=max_results,
    )


if __name__ == "__main__":
    mcp.run()
