"""
StoryForge Agent — FastAPI gateway.
Serves the React+Vite SPA at /ui/ and exposes the research/script pipeline
plus Firebase auth + history proxies (reusing the existing storyforge modules).
"""
from __future__ import annotations

import os
import json
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env from project root (same one the Streamlit app uses)
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Make the existing storyforge package importable
import sys
sys.path.insert(0, str(ROOT))

import storyforge.core as core
import storyforge.auth as auth
import storyforge.history as history  # noqa: F401  (used via proxies)

app = FastAPI(title="StoryForge Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class ForgeRequest(BaseModel):
    query: str
    duration: int = 45
    tone: str = "Energetic"
    sources: int = 5


class SignUpRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class SignInRequest(BaseModel):
    email: str
    password: str


class ResetRequest(BaseModel):
    email: str


class HistoryAddRequest(BaseModel):
    query: str
    summary: str
    script: str


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
@app.post("/api/forge")
async def forge(req: ForgeRequest):
    try:
        research = core.get_realtime_info(req.query, max_results=req.sources)
    except core.MissingKeyError as exc:
        raise HTTPException(500, str(exc))
    try:
        script = core.generate_video_script(
            research.summary,
            topic=req.query,
            duration_seconds=req.duration,
            tone=req.tone,
        )
    except core.StoryForgeError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Pipeline error: {exc}")
    return {
        "query": req.query,
        "summary": research.summary,
        "sources": research.sources,
        "script": script,
    }


# --------------------------------------------------------------------------- #
# Auth proxies (Firebase Identity Toolkit REST)
# --------------------------------------------------------------------------- #
@app.post("/api/auth/signup")
async def auth_signup(req: SignUpRequest):
    try:
        u = auth.sign_up(req.email, req.password, req.display_name)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))
    return {"id_token": u.id_token, "uid": u.uid,
            "email": u.email, "display_name": u.display_name,
            "refresh_token": u.refresh_token}


@app.post("/api/auth/signin")
async def auth_signin(req: SignInRequest):
    try:
        u = auth.sign_in(req.email, req.password)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))
    return {"id_token": u.id_token, "uid": u.uid,
            "email": u.email, "display_name": u.display_name,
            "refresh_token": u.refresh_token}


@app.post("/api/auth/reset")
async def auth_reset(req: ResetRequest):
    try:
        auth.send_password_reset(req.email)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@app.post("/api/auth/profile")
async def auth_profile(req: Request):
    body = await req.json()
    try:
        auth.update_profile(body["id_token"], body.get("display_name", ""))
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@app.post("/api/auth/delete")
async def auth_delete(req: Request):
    body = await req.json()
    try:
        if history.is_configured():
            history.clear_all(body["id_token"], body["uid"])
        auth.delete_account(body["id_token"])
    except (auth.AuthError, history.HistoryError) as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


# --------------------------------------------------------------------------- #
# History proxies (Firestore REST)
# --------------------------------------------------------------------------- #
@app.get("/api/history/{uid}")
async def history_list(uid: str, id_token: str = ""):
    try:
        items = history.list_entries(id_token, uid)
    except history.HistoryError as exc:
        raise HTTPException(400, str(exc))
    return {"items": items}


@app.post("/api/history/{uid}")
async def history_add(uid: str, req: HistoryAddRequest, id_token: str = ""):
    try:
        history.add_entry(id_token, uid, query=req.query,
                          summary=req.summary, script=req.script)
    except history.HistoryError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@app.delete("/api/history/{uid}/{entry_id}")
async def history_del(uid: str, entry_id: str, id_token: str = ""):
    try:
        history.delete_entry(id_token, uid, entry_id)
    except history.HistoryError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@app.get("/api/health")
async def health():
    try:
        # Probe config: MissingKeyError is raised when keys are absent.
        core.get_realtime_info("__health_probe__", max_results=1)
        configured = True
    except core.MissingKeyError:
        configured = False
    except Exception:
        configured = True
    return {"ok": True, "configured": configured}


# --------------------------------------------------------------------------- #
# Serve the built SPA at /ui/  (after `npm run build` -> frontend/dist)
# --------------------------------------------------------------------------- #
DIST = ROOT / "frontend" / "dist"


def _spa_fallback(path: str):
    index = DIST / "index.html"
    return FileResponse(index) if index.exists() else JSONResponse(
        {"error": "SPA not built. Run `npm run build` in frontend/."}, 503
    )


if DIST.exists():
    app.mount("/ui/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/ui/{full_path:path}")
    async def spa(full_path: str):
        # try real file, else SPA fallback
        candidate = DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return _spa_fallback(full_path)

    @app.get("/ui")
    async def ui_root():
        return _spa_fallback("")
else:
    @app.get("/ui")
    async def ui_missing():
        return JSONResponse({"error": "frontend/dist not found. Build the SPA first."}, 503)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
