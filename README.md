# 🎬 StoryForge Agent

A **YouTube Content Creation** tool: go from a simple topic query to a polished
short-form video script in seconds. StoryForge pairs **real-time web search**
(Tavily) with a **large language model** to research any topic and generate
ready-to-record scripts optimized for **YouTube Shorts** and **Instagram Reels**.

Built following the *YouTube Content Creation StoryForge Agent* project:
https://www.krishnaik.in/project/youtube-content-creation-storyforge-agent

---

## Features

- 🎨 **Editorial-matte dark UI (React)** — warm ink canvas, Fraunces display
  serif + Inter body, a single clay/terracotta accent, hairline borders. Premium,
  no neon, no jank. Real **OriginKit** components: `spotlighttext` (hero),
  `shiny-pill` (Forge CTA), `electricborder` (crackling card frames).
- 🔐 **Firebase email/password authentication** — each user signs in (or creates
  an account) via the Identity Toolkit REST API; their work is private to them.
  Includes password reset, display-name editing, and account deletion.
- 🕘 **Per-user search history** — every Forge is saved to the user's Firestore
  collection and listed in the **Recent research** rail; click to reload, delete
  to remove.
- 🧠 **Bring-your-own-LLM** — use the server's Gemini key, or supply your own
  OpenAI / Anthropic / Ollama / OpenAI-compatible (OpenRouter, Groq, …) key in
  the in-app **Model** picker. Keys stay in your browser (localStorage).
- 🔎 **Real-time research** — Tavily fetches and ranks the latest web sources.
- 🎬 **Instant scripting** — a timestamped, hook-driven short-form script with
  `[VISUAL:]` cues, ready for Shorts & Reels.
- ⬇️ **Download** the research brief + script as Markdown.

---

## What's inside

| Piece | File | Role |
|-------|------|------|
| **React SPA** | `frontend/` | Vite + React UI (sidebar + document canvas + composer) |
| **FastAPI gateway** | `backend/main.py` | Serves the SPA at `/ui/` and the REST API at `/api/*` |
| **Core logic** | `storyforge/core.py` | `get_realtime_info()` + `generate_video_script()` |
| **LLM dispatcher** | `storyforge/llm.py` | Multi-LLM routing (gemini/openai/anthropic/ollama/compatible) |
| **Firebase auth** | `storyforge/auth.py` | Email/password sign-up, sign-in, refresh (REST) |
| **Search history** | `storyforge/history.py` | Per-user Firestore persistence (REST) |
| **Tests** | `tests/` | Pipeline + auth + LLM dispatcher verified with mocked APIs |
| **OriginKit source** | `originkit_components/` | Fetched real TSX (framer stack) for reference |

### Architecture

```
End User (Browser)
     │ topic query
     ▼
React SPA (frontend/)  ──fetch──►  FastAPI gateway (backend/main.py)
                                        │
                                        ├─► Core Logic (storyforge.core)
                                        │      get_realtime_info(query)
                                        │      generate_video_script(info_text)
                                        │
                                        ├─► LLM dispatch (storyforge.llm)
                                        │      gemini | openai | anthropic | ollama | compatible
                                        │
       Firebase Auth (storyforge/auth) ─┤  per-user identity
       Firestore history (storyforge/history) ─┤  per-user saved research
                                        │
              Search ──► Tavily API (real-time search)
              Summarize & Script ──► chosen LLM
                                        ▲
                                     .env  (GEMINI_API_KEY, TAVILY_API_KEY, FIREBASE_API_KEY, ...)
```

---

## Quick start

### 1. Backend

```bash
python -m venv .venv
# Windows (bash/MSYS): source .venv/Scripts/activate
# macOS/Linux:         source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure keys

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# Required for research + scripting
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Firebase — project display name "StoryForge Agent" (project id storyforge-94449)
# Firebase Console -> Project settings -> Your apps -> Web app -> SDK config.
# The web API key is NOT a secret; access is governed by Firestore security rules.
FIREBASE_API_KEY=your_firebase_web_api_key_here
FIREBASE_PROJECT_ID=your_firebase_project_id_here

# Optional
GEMINI_MODEL=gemini-2.0-flash
GEMINI_FALLBACK_MODELS=gemini-2.5-flash
TAVILY_MAX_RESULTS=5
```

**Firebase setup (one-time):** create a Firebase project, add a **Web app**,
enable **Authentication → Sign-in method → Email/Password**, and create a
**Firestore** database. Deploy the bundled `firestore.rules` (so each user can
only read/write their own `users/{uid}` subtree):

```bash
firebase deploy --only firestore:rules --project <your-project-id>
```

> Without the Firebase keys the app still runs but shows an auth-error and skips
> history. All other features work once `GEMINI_API_KEY`/`TAVILY_API_KEY` are set.

### 3. Frontend (build the SPA)

```bash
cd frontend
npm install
VITE_BASE=/ui/ npm run build
```

### 4. Run

```bash
# From the project root, with the venv active:
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/ui/ — sign in (or create an account), enter a topic,
tweak length/tone, pick a **Model** (server default or bring your own key), and
hit **⚡ Forge**.

---

## Tests

```bash
pip install pytest
pytest -q
```

External APIs are mocked, so tests run offline with no keys required (28 tests).

---

## Tech stack

- [React](https://react.dev) + [Vite](https://vitejs.dev) — web UI
- [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org) — gateway + REST API
- [Tavily](https://tavily.com) — real-time web search
- Google Gemini / OpenAI / Anthropic / Ollama — summarization & scripting (bring-your-own-key)
- [Firebase](https://firebase.google.com) — Auth + Firestore (email/password)
- [OriginKit](https://originkit.dev) — `spotlighttext`, `shiny-pill`, `electricborder` (real TSX, adapted to React)

---

## License

MIT
