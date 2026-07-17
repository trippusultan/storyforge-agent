"""StoryForge Agent - Streamlit web app (editorial-matte dark overhaul).

Premium dark dashboard for real-time research + short-form video scripting,
with Firebase email/password auth and per-user history.

Aesthetic: editorial matte — warm ink canvas, bone text, a single clay/
terracotta accent, Fraunces display serif + Inter body, hairline borders,
generous whitespace. Base palette lives in `.streamlit/config.toml`; the CSS
block below only expresses what config.toml cannot (fonts, hairlines, cards,
account menu, transitions).

Run:
    streamlit run app.py
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import replace

import streamlit as st
import streamlit.components.v1 as components

from storyforge import auth, history
from storyforge.core import (
    MissingKeyError,
    StoryForgeError,
    generate_video_script,
    get_realtime_info,
)

st.set_page_config(
    page_title="StoryForge Agent",
    page_icon=":material/movie:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Global editorial-matte styling
# --------------------------------------------------------------------------- #
GLOBAL_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

<style>
    :root{
        --ink:#14110F; --panel:#1E1A17; --panel-2:#191512;
        --bone:#EDE6DD; --bone-soft:#B7AEA2; --hair:#332d28;
        --clay:#C2613F; --clay-soft:rgba(194,97,63,0.14);
    }
    html, body, [data-testid="stAppViewContainer"]{
        font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
        background:var(--ink);
    }
    /* Headings use the Fraunces display serif */
    h1,h2,h3,.forge-wordmark{
        font-family:'Fraunces',Georgia,serif !important;
        font-weight:600; letter-spacing:-0.01em; color:var(--bone);
    }
    /* Wordmark */
    .forge-wordmark{ font-size:1.35rem; font-weight:700; display:inline-flex;
        align-items:center; gap:0.5rem; }
    .forge-wordmark .dot{ width:9px;height:9px;border-radius:50%;
        background:var(--clay); box-shadow:0 0 0 4px var(--clay-soft); }
    .forge-accent{ color:var(--clay); }
    .subtle{ color:var(--bone-soft); font-size:0.92rem; line-height:1.5; }

    /* Hairline cards */
    .hair-card{ background:var(--panel); border:1px solid var(--hair);
        border-radius:16px; padding:1.4rem 1.5rem; }
    .hair-divider{ height:1px; background:var(--hair); border:0; margin:1.1rem 0; }

    /* Auth shell */
    .auth-shell{ max-width:440px; margin:6vh auto 0; }
    .auth-card{ background:var(--panel); border:1px solid var(--hair);
        border-radius:20px; padding:2.2rem 2rem 1.8rem; }
    .auth-tag{ color:var(--clay); font-weight:600; letter-spacing:0.08em;
        text-transform:uppercase; font-size:0.72rem; }

    /* Pill / badge */
    .pill{ display:inline-block; padding:0.18rem 0.6rem; border-radius:999px;
        font-size:0.7rem; font-weight:700; letter-spacing:0.05em;
        text-transform:uppercase; }
    .pill-research{ background:rgba(143,168,192,0.14); color:#A9C0D8;
        border:1px solid rgba(143,168,192,0.28); }
    .pill-script{ background:var(--clay-soft); color:#E0A085;
        border:1px solid rgba(194,97,63,0.34); }

    /* Source links */
    .src a{ color:#A9C0D8; text-decoration:none; }
    .src a:hover{ text-decoration:underline; }

    /* Top nav */
    .topbar{ display:flex; align-items:center; justify-content:space-between;
        padding:0.6rem 0 1rem; border-bottom:1px solid var(--hair);
        margin-bottom:1.4rem; }
    .acct-chip{ display:inline-flex; align-items:center; gap:0.55rem;
        padding:0.3rem 0.7rem 0.3rem 0.35rem; border:1px solid var(--hair);
        border-radius:999px; background:var(--panel); }
    .acct-avatar{ width:28px;height:28px;border-radius:50%;
        background:var(--clay); color:#fff; display:flex;align-items:center;
        justify-content:center; font-weight:700; font-size:0.8rem; }
    .acct-name{ font-size:0.85rem; color:var(--bone); max-width:150px;
        overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

    /* History rail */
    .hist-item{ display:flex; align-items:center; gap:0.5rem;
        padding:0.55rem 0.6rem; border:1px solid var(--hair); border-radius:12px;
        margin-bottom:0.5rem; background:var(--panel-2); }
    .hist-item:hover{ border-color:rgba(194,97,63,0.45); }
    .hist-title{ flex:1; font-size:0.86rem; color:var(--bone);
        overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

    /* Smooth micro-interactions */
    button, [data-testid]{ transition:border-color .18s ease, background .18s ease; }
    ::selection{ background:var(--clay-soft); }
    /* Fade-in for result cards */
    @keyframes sf-fade{ from{opacity:0; transform:translateY(8px);} to{opacity:1; transform:none;} }
    .sf-fade{ animation:sf-fade .4s ease both; }
    /* Hide the default Streamlit hamburger/footer for a cleaner canvas */
    [data-testid="stToolbar"]{ display:none; }
    footer{ visibility:hidden; }
    .stAppViewContainer .main .block-container{ padding-top:1.2rem; }

    /* ===== Sidebar + document canvas layout ===== */
    section[data-testid="stSidebar"]{
        background:var(--panel-2);
        border-right:1px solid var(--hair);
    }
    .side-brand{ display:flex; align-items:center; gap:0.5rem;
        margin:0.2rem 0 0.9rem; }
    .side-new{ display:flex; align-items:center; gap:0.5rem; width:100%;
        padding:0.5rem 0.7rem; border:1px solid var(--hair); border-radius:12px;
        background:var(--panel); color:var(--bone); font-weight:600; font-size:0.88rem;
        transition:border-color .18s ease; }
    .side-new:hover{ border-color:rgba(194,97,63,0.5); }
    .side-label{ font-size:0.7rem; letter-spacing:0.1em; text-transform:uppercase;
        color:var(--bone-soft); margin:1rem 0 0.4rem; }
    .conv-item{ display:flex; align-items:center; gap:0.5rem; padding:0.5rem 0.6rem;
        border-radius:10px; cursor:pointer; color:var(--bone-soft); font-size:0.86rem;
        border:1px solid transparent; }
    .conv-item:hover{ background:var(--panel); color:var(--bone); }
    .conv-item.active{ background:var(--panel); color:var(--bone); border-color:var(--hair); }
    .conv-title{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .conv-del{ opacity:0; color:var(--bone-soft); font-size:1rem; line-height:1; background:none; border:none; cursor:pointer; }
    .conv-item:hover .conv-del{ opacity:1; }

    .doc-canvas{ max-width:760px; margin:0 auto; padding:1.5rem 1rem 2.5rem; }
    .doc-title{ font-size:2rem; margin:0.2rem 0 1.1rem; line-height:1.15; }
    .doc-meta{ color:var(--bone-soft); font-size:0.8rem; margin-bottom:1.6rem;
        display:flex; gap:0.8rem; align-items:center; }
    .doc-actions{ display:flex; gap:0.6rem; margin:1.2rem 0 2rem; flex-wrap:wrap; }
    .doc-sec{ margin:2rem 0 0; }
    .doc-sec h2{ font-size:1.3rem; margin-bottom:0.7rem; }

    .composer-bar{ max-width:760px; margin:0 auto; padding:0 1rem 1.4rem; }
    .empty-state{ text-align:center; padding:9vh 1rem 0; }
    .empty-state h1{ font-size:2.3rem; margin-bottom:0.4rem; }
    .empty-state p{ color:var(--bone-soft); }
    .chip-row{ display:flex; gap:0.5rem; justify-content:center; flex-wrap:wrap; margin-top:1.4rem; }
    .sug-chip{ padding:0.5rem 0.9rem; border:1px solid var(--hair); border-radius:999px;
        background:var(--panel); color:var(--bone); font-size:0.85rem; cursor:pointer;
        transition:border-color .18s ease; }
    .sug-chip:hover{ border-color:rgba(194,97,63,0.5); }

    /* ===== OriginKit-style pure-CSS effects (ported) ===== */
    /* shiny-pill: soft bone sheen sweep on the primary CTA */
    .shiny-pill{ position:relative; overflow:hidden; }
    .shiny-pill::after{ content:""; position:absolute; top:0; left:-150%;
        width:60%; height:100%; transform:skewX(-20deg);
        background:linear-gradient(90deg, transparent, rgba(255,245,235,0.28), transparent);
        animation:sf-sheen 3.2s ease-in-out infinite; }
    @keyframes sf-sheen{ 0%{left:-150%;} 55%{left:160%;} 100%{left:160%;} }
    /* electricborder: terracotta hover border glow on cards */
    .electric-card{ position:relative; border:1px solid var(--hair); border-radius:16px;
        background:var(--panel); transition:border-color .25s ease, box-shadow .25s ease; }
    .electric-card:hover{ border-color:rgba(194,97,63,0.7);
        box-shadow:0 0 0 1px rgba(194,97,63,0.35), 0 0 22px -6px rgba(194,97,63,0.55); }
    /* apply shiny-pill sheen to the Forge CTA inside the composer bar */
    .composer-bar button[data-testid="stBaseButton-primary"]{ position:relative; overflow:hidden; }
    .composer-bar button[data-testid="stBaseButton-primary"]::after{ content:"";
        position:absolute; top:0; left:-150%; width:60%; height:100%; transform:skewX(-20deg);
        background:linear-gradient(90deg, transparent, rgba(255,245,235,0.30), transparent);
        animation:sf-sheen 3.2s ease-in-out infinite; }
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
def _init_state():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("summary", "")
    st.session_state.setdefault("sources", [])
    st.session_state.setdefault("script", "")
    st.session_state.setdefault("last_query", "")
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("history_loaded", False)
    st.session_state.setdefault("prefill", "")
    st.session_state.setdefault("confirm_delete", False)


_init_state()


def _fmt_ts(ts: int) -> str:
    try:
        return _dt.datetime.fromtimestamp(ts).strftime("%b %d, %H:%M")
    except Exception:
        return ""


def _sign_out():
    for k in ("user", "summary", "sources", "script", "last_query",
              "history", "history_loaded", "confirm_delete"):
        st.session_state[k] = None if k == "user" else (
            [] if k in ("sources", "history") else
            (False if k in ("history_loaded", "confirm_delete") else "")
        )


def _load_history():
    user = st.session_state.user
    if not user or not history.is_configured():
        return
    try:
        st.session_state.history = history.list_entries(user.id_token, user.uid)
    except history.HistoryError:
        st.session_state.history = []
    st.session_state.history_loaded = True


def _refresh_user():
    """Rebuild the stored user from Firebase so the schema is always current."""
    user = st.session_state.user
    if not user:
        return
    try:
        info = auth.get_account_info(user.id_token)
        acct = info.get("users", [{}])[0]
        st.session_state.user = replace(
            user,
            email=acct.get("email", user.email),
            display_name=acct.get("displayName", ""),
        )
    except auth.AuthError:
        pass


# --- Premium polish helpers ----------------------------------------------- #
def _copy_button(label: str, text: str, key: str):
    """Clipboard copy via a tiny injected component (no external deps)."""
    js = f"""
    <script>
    function sfCopy_{key}() {{
      navigator.clipboard.writeText({json.dumps(text)}).then(function(){{
        var b=document.getElementById('sfbtn_{key}');
        if(b){{b.innerText='✓ Copied'; setTimeout(function(){{b.innerText={json.dumps(label)};}},1400);}}
      }});
    }}
    </script>
    <button id="sfbtn_{key}" onclick="sfCopy_{key}()" class="sf-copy">{label}</button>
    <style>
      .sf-copy{{background:rgba(194,97,63,0.18);color:#E8B49C;border:1px solid rgba(194,97,63,0.6);
        border-radius:10px;padding:0.35rem 0.8rem;font-size:0.8rem;font-weight:600;cursor:pointer;
        font-family:'Inter',sans-serif;transition:background .18s ease;}}
      .sf-copy:hover{{background:rgba(194,97,63,0.3);}}
    </style>
    """
    components.html(js, height=38)


_TONES = [
    "energetic and engaging", "calm and educational",
    "dramatic and cinematic", "funny and casual", "inspirational and bold",
]


def _tone_segmented() -> str:
    """Custom segmented Tone control (premium, no native select)."""
    cols = st.columns(len(_TONES))
    current = st.session_state.get("tone_idx", 0)
    chosen = current
    for i, t in enumerate(_TONES):
        label = t.split()[0].capitalize()
        active = i == current
        with cols[i]:
            if st.button(label, key=f"tone_{i}",
                         type="primary" if active else "secondary",
                         use_container_width=True):
                chosen = i
                st.session_state.tone_idx = i
    return _TONES[chosen]

def render_auth_gate():
    st.markdown(
        '<div class="auth-shell"><div class="auth-card">'
        '<div class="auth-tag">YouTube Content Studio</div>'
        '<div class="forge-wordmark" style="margin:0.5rem 0 0.2rem">'
        '<span class="dot"></span>StoryForge <span class="forge-accent">Agent</span></div>'
        '<p class="subtle" style="margin-top:0.4rem">Sign in to research any topic and '
        'forge a ready-to-record short-form video script &mdash; your work is saved to your account.</p>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    with st.container():
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            if not auth.is_configured():
                st.error("Firebase is not configured. Set FIREBASE_API_KEY and "
                          "FIREBASE_PROJECT_ID in your .env file.")
                return

            tab_in, tab_up = st.tabs(["Sign in", "Create account"])

            with tab_in:
                email = st.text_input("Email", key="in_email",
                                      placeholder="you@email.com")
                pw = st.text_input("Password", type="password", key="in_pw")
                if st.button("Sign in", icon=":material/login:",
                             width="stretch", type="primary"):
                    try:
                        st.session_state.user = auth.sign_in(email.strip(), pw)
                        st.session_state.history_loaded = False
                        st.rerun()
                    except auth.AuthError as exc:
                        st.error(str(exc))
                if st.button("Forgot password?", icon=":material/mail:",
                             key="forgot_pw"):
                    if not email.strip():
                        st.warning("Enter your email above first.")
                    else:
                        try:
                            auth.send_password_reset(email.strip())
                            st.success("Password-reset email sent. Check your inbox "
                                        "(and spam folder).")
                        except auth.AuthError as exc:
                            st.error(str(exc))

            with tab_up:
                email2 = st.text_input("Email", key="up_email",
                                       placeholder="you@email.com")
                pw2 = st.text_input("Password (min 6 chars)", type="password",
                                     key="up_pw")
                if st.button("Create account", icon=":material/person_add:",
                             width="stretch", type="primary"):
                    try:
                        st.session_state.user = auth.sign_up(email2.strip(), pw2)
                        st.session_state.history_loaded = False
                        st.rerun()
                    except auth.AuthError as exc:
                        st.error(str(exc))


# =========================================================================== #
# ACCOUNT SETTINGS DIALOG
# =========================================================================== #
def render_account_dialog():
    user = st.session_state.user
    with st.dialog("Account", width="small"):
        st.markdown(f"#### :material/account_circle: {user.email}")
        with st.form("profile_form", border=False):
            new_name = st.text_input("Display name",
                                     value=getattr(user, "display_name", "") or "",
                                     placeholder="optional")
            if st.form_submit_button("Save name", icon=":material/check:",
                                     width="stretch", type="primary"):
                try:
                    auth.update_profile(user.id_token, display_name=new_name.strip())
                    user.display_name = new_name.strip()
                    st.session_state.user = user
                    st.rerun()
                except auth.AuthError as exc:
                    st.error(str(exc))

        st.divider()
        st.markdown("**Danger zone**")
        st.caption("Permanently delete your account and all saved history.")
        if st.button("Delete account", icon=":material/delete_forever:",
                     type="primary", width="stretch"):
            st.session_state.confirm_delete = True
            st.rerun()

    if st.session_state.get("confirm_delete"):
        with st.dialog("Delete account?", width="small"):
            st.warning("This cannot be undone.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, delete", icon=":material/delete_forever:",
                             type="primary", width="stretch"):
                    try:
                        if history.is_configured():
                            history.clear_all(user.id_token, user.uid)
                        auth.delete_account(user.id_token)
                        _sign_out()
                        st.rerun()
                    except (auth.AuthError, history.HistoryError) as exc:
                        st.error(str(exc))
                        st.session_state.confirm_delete = False
            with c2:
                if st.button("Cancel", width="stretch"):
                    st.session_state.confirm_delete = False
                    st.rerun()


# =========================================================================== #
# MAIN APP
# =========================================================================== #
def render_app():
    _refresh_user()
    user = st.session_state.user
    if not st.session_state.history_loaded:
        _load_history()

    display = getattr(user, "display_name", "") or user.email
    initial = (getattr(user, "display_name", "") or user.email or "?")[0].upper()

    # ---------- LEFT SIDEBAR: brand + history + account ----------
    with st.sidebar:
        st.markdown(
            '<div class="side-brand"><span class="dot"></span>'
            '<span class="forge-wordmark">StoryForge <span class="forge-accent">Agent</span></span></div>',
            unsafe_allow_html=True,
        )
        if st.button(":material/add: New research", key="new_chat",
                     use_container_width=True):
            for k in ("summary", "script", "sources", "last_query"):
                st.session_state[k] = "" if k != "sources" else []
            st.rerun()
        # Account row
        chip = st.popover(f"{initial}", icon=":material/account_circle:",
                          help="Account & settings", use_container_width=True)
        with chip:
            st.markdown(f"**{display}**")
            st.caption(user.email)
            st.divider()
            if st.button("Account settings", icon=":material/manage_accounts:",
                         width="stretch", key="acct_settings"):
                st.session_state.open_account = True
                st.rerun()
            if st.button("Sign out", icon=":material/logout:", width="stretch"):
                _sign_out()
                st.rerun()

        st.markdown('<div class="side-label">Recent research</div>',
                    unsafe_allow_html=True)
        if not history.is_configured():
            st.caption("History disabled.")
        elif not st.session_state.history:
            st.caption("No research yet.")
        else:
            for item in st.session_state.history:
                label = item["query"][:34] + ("…" if len(item["query"]) > 34 else "")
                cols = st.columns([5, 1])
                with cols[0]:
                    if st.button(f":material/description: {label}",
                                 key=f"hist_{item['id']}",
                                 help=f"{item['query']}  ·  {_fmt_ts(item['ts'])}",
                                 use_container_width=True):
                        st.session_state.summary = item["summary"]
                        st.session_state.script = item["script"]
                        st.session_state.last_query = item["query"]
                        st.session_state.sources = []
                        st.rerun()
                with cols[1]:
                    if st.button(":material/close:", key=f"del_{item['id']}",
                                 help="Delete", use_container_width=True):
                        try:
                            history.delete_entry(user.id_token, user.uid, item["id"])
                        except history.HistoryError:
                            pass
                        _load_history()
                        st.rerun()

    if st.session_state.get("open_account"):
        st.session_state.open_account = False
        render_account_dialog()

    # ---------- MAIN: document canvas ----------
    has_doc = bool(st.session_state.get("script") or st.session_state.get("summary"))

    if not has_doc:
        # Empty state with suggestion chips
        st.markdown(
            '<div class="empty-state"><h1>StoryForge <span class="forge-accent">Agent</span></h1>'
            '<p>Ask any topic &mdash; get a real-time research brief and a ready-to-record '
            'short-form video script.</p></div>',
            unsafe_allow_html=True,
        )

    # Controls (collapsed-ish: a compact popover + inline sliders hidden until needed)
    with st.expander("Script options", expanded=False):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            duration = st.slider("Script length (seconds)", 15, 90, 45, step=5)
        with c2:
            st.markdown('<span class="subtle" style="font-size:0.78rem;'
                        'display:block;margin-bottom:0.35rem">Tone</span>',
                        unsafe_allow_html=True)
            tone = _tone_segmented()
        with c3:
            max_results = st.slider("Web sources", 3, 10, 5)

    # Document render
    if has_doc:
        st.markdown(f'<div class="doc-canvas">'
                    f'<h1 class="doc-title">{st.session_state.last_query or "Your research"}</h1>'
                    f'<div class="doc-meta"><span>:material/schedule: {duration}s</span>'
                    f'<span>:material/mood: {tone}</span>'
                    f'<span>:material/public: {len(st.session_state.sources)} sources</span></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="doc-actions">', unsafe_allow_html=True)
        _copy_button("Copy brief", st.session_state.summary or "", "brief_top")
        _copy_button("Copy script", st.session_state.script or "", "script_top")
        safe = (st.session_state.last_query or "script")[:40].replace(" ", "_")
        st.download_button("Download (.md)", icon=":material/download:",
                           data=(f"# {st.session_state.last_query}\n\n"
                                 f"## Research Brief\n\n{st.session_state.summary}\n\n"
                                 f"## Video Script\n\n{st.session_state.script}\n"),
                           file_name=f"storyforge_{safe}.md", mime="text/markdown")
        st.markdown('</div>', unsafe_allow_html=True)

        # Research Brief section
        st.markdown('<div class="doc-sec sf-fade electric-card" style="padding:1.2rem 1.4rem">'
                    '<h2>:material/auto_stories: Research Brief</h2>',
                    unsafe_allow_html=True)
        st.markdown(st.session_state.summary or "_No summary yet._")
        if st.session_state.sources:
            st.markdown("**Sources**")
            for s in st.session_state.sources:
                title = s.get("title") or s.get("url") or "source"
                url = s.get("url", "")
                if url:
                    st.markdown(f'<div class="src">&bull; <a href="{url}" '
                                f'target="_blank">{title}</a></div>',
                                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Video Script section
        st.markdown('<div class="doc-sec sf-fade electric-card" style="padding:1.2rem 1.4rem">'
                    '<h2>:material/movie_edit: Video Script</h2>',
                    unsafe_allow_html=True)
        if st.session_state.script:
            st.markdown(st.session_state.script)
        else:
            st.markdown("_Run a query to generate a script._")
        st.markdown('</div></div>', unsafe_allow_html=True)

    # ---------- BOTTOM: composer bar ----------
    st.markdown('<div class="composer-bar">', unsafe_allow_html=True)
    with st.form("composer", border=True):
        q = st.text_input(
            "Topic",
            value=st.session_state.prefill,
            placeholder="Research any topic — e.g. The James Webb telescope's latest discoveries",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Forge", icon=":material/auto_awesome:",
                                          type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if not q.strip():
            st.warning("Enter a topic to research.")
        else:
            st.session_state.prefill = ""
            with st.status("Forging your story...", expanded=True) as status:
                status.write(":material/search: Researching in real time with Tavily...")
                research = get_realtime_info(q.strip(), max_results=max_results)
                st.session_state.summary = research.summary
                st.session_state.sources = research.sources
                st.session_state.last_query = q.strip()
                status.write(":material/edit: Writing your short-form script with Gemini...")
                script = generate_video_script(
                    research.summary, topic=q.strip(),
                    duration_seconds=duration, tone=tone
                )
                st.session_state.script = script
                status.update(label="Done!", state="complete", expanded=False)
            if history.is_configured():
                try:
                    history.add_entry(user.id_token, user.uid, query=q.strip(),
                                      summary=st.session_state.summary,
                                      script=st.session_state.script)
                    _load_history()
                except history.HistoryError:
                    pass
            st.rerun()


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
if st.session_state.user is None:
    render_auth_gate()
else:
    render_app()

