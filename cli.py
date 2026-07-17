"""StoryForge CLI - quick end-to-end run without the Streamlit UI.

Usage:
    python cli.py "your topic here"
    python cli.py "your topic here" --seconds 30 --tone "dramatic and cinematic"

Requires GEMINI_API_KEY and TAVILY_API_KEY in your environment or .env file.
"""

from __future__ import annotations

import argparse
import sys

from storyforge.core import StoryForgeError, research_and_script


def main() -> int:
    parser = argparse.ArgumentParser(description="StoryForge Agent CLI")
    parser.add_argument("query", help="Topic to research and script")
    parser.add_argument("--seconds", type=int, default=45, help="Script length")
    parser.add_argument(
        "--tone", default="energetic and engaging", help="Script tone"
    )
    parser.add_argument("--sources", type=int, default=5, help="Web sources")
    args = parser.parse_args()

    try:
        out = research_and_script(
            args.query,
            duration_seconds=args.seconds,
            tone=args.tone,
            max_results=args.sources,
        )
    except StoryForgeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("=" * 70)
    print(f"TOPIC: {out['query']}")
    print("=" * 70)
    print("\n--- RESEARCH BRIEF ---\n")
    print(out["summary"])
    print("\n--- VIDEO SCRIPT ---\n")
    print(out["script"])
    if out["sources"]:
        print("\n--- SOURCES ---")
        for s in out["sources"]:
            print(f"  • {s.get('title', '')} — {s.get('url', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
