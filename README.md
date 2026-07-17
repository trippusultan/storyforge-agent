1|# 🎬 StoryForge Agent
2|
3|A **YouTube Content Creation** tool: go from a simple topic query to a polished
4|short-form video script in seconds. StoryForge pairs **real-time web search**
5|(Tavily) with a **large language model** (Google Gemini) to research any topic
6|and generate ready-to-record scripts optimized for **YouTube Shorts** and
7|**Instagram Reels**.
8|
9|Built following the *YouTube Content Creation StoryForge Agent* project:
10|https://www.krishnaik.in/project/youtube-content-creation-storyforge-agent
11|
12|---
13|
## Features

- 🎨 **Editorial-matte dark UI** — warm ink canvas, Fraunces display serif +
  Inter body, a single clay/terracotta accent, hairline borders. Premium, no
  neon, no jank.
- 🔐 **Firebase email/password authentication** — each user signs in (or creates
  an account) via the Identity Toolkit REST API; their work is private to them.
  Includes password reset, display-name editing, and account deletion.
- 🕘 **Per-user search history** — every Forge is saved to the user's Firestore
  collection and listed in the **Recent searches** rail; click to reload, delete
  to remove.
21|- 🔎 **Real-time research** — Tavily fetches and ranks the latest web sources.
22|- 🎬 **Instant scripting** — Google Gemini writes a timestamped, hook-driven
23|  short-form script with `[VISUAL:]` cues, ready for Shorts & Reels.
24|- ⬇️ **Download** the research brief + script as Markdown.
25|- 🤖 **MCP server** — the same research/script tools are exposed for AI agents
26|  (Claude Desktop, etc.).
27|
28|---
29|
30|## What's inside
31|
32|| Piece | File | Role |
33||-------|------|------|
34|| **Streamlit web app** | `app.py` | Premium dark-themed dashboard with auth gate + history |
35|| **Core logic** | `storyforge/core.py` | `get_realtime_info()` + `generate_video_script()` |
36|| **Firebase auth** | `storyforge/auth.py` | Email/password sign-up, sign-in, refresh (REST) |
37|| **Search history** | `storyforge/history.py` | Per-user Firestore persistence (REST) |
38|| **MCP server** | `mcp_server.py` | FastMCP tools for AI agents |
39|| **CLI** | `cli.py` | Quick end-to-end run without the UI |
40|| **Tests** | `tests/` | Pipeline + auth verified with mocked APIs |
41|
42|### Architecture
43|
44|```
45|End User (Browser)
46|      │ topic query
47|      ▼
48|Streamlit App (app.py)  ──►  Core Logic (storyforge.core)
49|                                 │   get_realtime_info(query)
50|                                 │   generate_video_script(info_text)
51|      AI Agents (MCP clients) ─┤ tool calls
52|      MCP Server (mcp_server) ─┘
53|                                 │
54|                Search ──► Tavily API (real-time search)
55|      Summarize & Script ──► Google Gemini (gemini-2.5-flash)
56|                                 ▲
57|                              .env  (GEMINI_API_KEY, TAVILY_API_KEY, FIREBASE_API_KEY, ...)
58|```
59|
60|---
61|
62|## Quick start
63|
63|### 1. Install
64|
64|```bash
65|python -m venv .venv
66|# Windows (bash/MSYS): source .venv/Scripts/activate
67|# macOS/Linux:         source .venv/bin/activate
68|pip install -r requirements.txt
69|```
70|
71|### 2. Configure keys
72|
72|```bash
73|cp .env.example .env
74|```
75|
76|Then edit `.env`:
77|
78|```env
79|# Required for research + scripting
80|GEMINI_API_KEY=your_gemini_api_key_here
81|TAVILY_API_KEY=your_tavily_api_key_here
82|
83|# Firebase — project display name "StoryForge Agent" (project id storyforge-94449)
84|# Firebase Console -> Project settings -> Your apps -> Web app -> SDK config.
85|# The web API key is NOT a secret; access is governed by Firestore security rules.
86|FIREBASE_API_KEY=your_firebase_web_api_key_here
87|FIREBASE_PROJECT_ID=your_firebase_project_id_here
88|
89|# Optional
90|GEMINI_MODEL=gemini-2.5-flash
91|TAVILY_MAX_RESULTS=5
92|```
93|
94|**Firebase setup (one-time):** create a Firebase project, add a **Web app**,
95|enable **Authentication → Sign-in method → Email/Password**, and create a
95|**Firestore** database. Deploy the bundled `firestore.rules` (so each user can
96|only read/write their own `users/{uid}` subtree):
97|
98|```bash
96|firebase deploy --only firestore:rules --project <your-project-id>
99|```
100|
101|> Without the Firebase keys the app still runs but shows an auth-error and skips
101|> history. All other features work once `GEMINI_API_KEY`/`TAVILY_API_KEY` are set.
102|
103|### 3. Run the web app
104|
104|```bash
105|streamlit run app.py
105|```
106|
106|Sign in (or create an account), enter a topic, tweak length/tone in the sidebar,
107|and hit **✨ Forge**. Your searches appear in the **History** sidebar.
108|
109|---
110|
111|## CLI usage
112|
113|```bash
114|python cli.py "The James Webb telescope's latest discoveries"
115|python cli.py "AI coding tools in 2025" --seconds 30 --tone "dramatic and cinematic"
116|```
117|
118|---
119|
120|## MCP server (Claude Desktop & other AI agents)
121|
122|The MCP server exposes three tools:
123|
124|- `get_latest_info_mcp(query, max_results)` — research a topic
125|- `get_video_script_mcp(info_text, topic, duration_seconds, tone)` — script it
126|- `research_and_script_mcp(query, ...)` — full pipeline in one call
127|
128|Run it:
129|
130|```bash
131|python mcp_server.py
132|```
133|
134|Add to Claude Desktop (`claude_desktop_config.json`):
134|
135|```json
136|{
137|  "mcpServers": {
138|    "storyforge": {
139|      "command": "python",
140|      "args": ["./mcp_server.py"]
141|    }
142|  }
143|}
143|```
144|
145|---
146|
147|## Tests
147|
148|```bash
149|pip install pytest
149|pytest -q
150|```
150|
151|External APIs are mocked, so tests run offline with no keys required.
151|
152|---
152|
153|## Tech stack
154|
154|- [Streamlit](https://streamlit.io) — web dashboard
154|- [Tavily](https://tavily.com) — real-time web search
154|- [Google Gemini](https://ai.google.dev) (`gemini-2.5-flash`) — summarization & scripting
155|- [Firebase](https://firebase.google.com) — Auth + Firestore (email/password)
155|- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
156|
157|---
157|
158|## License
158|
159|MIT
160|
