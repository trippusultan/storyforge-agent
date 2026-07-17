import { useState, useEffect, useCallback } from 'react'
import { useAuth } from './auth.js'
import { api } from './api.js'
import SpotlightText from './components/SpotlightText.tsx'
import ShinyPill from './components/ShinyPill.tsx'
import ElectricBorder from './components/ElectricBorder.tsx'

const TONES = ['Energetic', 'Calm', 'Dramatic', 'Funny', 'Inspirational']

// ---------- OriginKit (real) ShinyPill used for CTAs ----------
function ShinyButton({ children, onClick, disabled, type = 'button' }) {
  return (
    <button
      className={`btn primary ${disabled ? 'disabled' : ''}`}
      onClick={onClick}
      disabled={disabled}
      type={type}
      style={{ opacity: disabled ? 0.6 : 1, border: 'none', background: 'transparent', padding: 0 }}
    >
      <ShinyPill text={typeof children === 'string' ? children : 'Forge'} speed={2} />
    </button>
  )
}

export default function App() {
  const auth = useAuth()
  const { user } = auth

  const [history, setHistory] = useState([])
  const [doc, setDoc] = useState(null) // { query, summary, sources, script }
  const [query, setQuery] = useState('')
  const [duration, setDuration] = useState(45)
  const [tone, setTone] = useState('Energetic')
  const [sources, setSources] = useState(5)
  const [llm, setLlm] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('storyforge.llm') || 'null') || {
        provider: 'default',
        model: '',
        api_key: '',
        base_url: '',
      }
    } catch {
      return { provider: 'default', model: '', api_key: '', base_url: '' }
    }
  })
  const [showModel, setShowModel] = useState(false)
  const [busy, setBusy] = useState(false)
  const [pipeError, setPipeError] = useState('')
  const [acctOpen, setAcctOpen] = useState(false)
  const [tab, setTab] = useState('signin')
  const [showReset, setShowReset] = useState(false)
  const [resetEmail, setResetEmail] = useState('')
  const [resetMsg, setResetMsg] = useState('')

  useEffect(() => {
    localStorage.setItem('storyforge.llm', JSON.stringify(llm))
  }, [llm])

  const loadHistory = useCallback(async () => {
    if (!user) return
    try {
      const { items } = await api.listHistory(user.uid, user.id_token)
      setHistory(items)
    } catch {
      /* ignore */
    }
  }, [user])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const runForge = useCallback(
    async (q) => {
      if (!q.trim()) return
      setBusy(true)
      setPipeError('')
      try {
        const res = await api.forge({
          query: q.trim(),
          duration,
          tone,
          sources,
          llm: llm.provider === 'default' ? null : llm,
        })
        setDoc(res)
        if (user) {
          await api.addHistory(user.uid, user.id_token, {
            query: res.query,
            summary: res.summary,
            script: res.script,
          })
          loadHistory()
        }
      } catch (e) {
        setPipeError(e.message)
      } finally {
        setBusy(false)
      }
    },
    [duration, tone, sources, llm, user, loadHistory]
  )

  const onDelete = async (id) => {
    if (!user) return
    try {
      await api.deleteHistory(user.uid, id, user.id_token)
      if (doc && history.find((h) => h.id === id)?.query === doc.query)
        setDoc(null)
      loadHistory()
    } catch {
      /* ignore */
    }
  }

  const onPick = (item) => {
    setDoc({
      query: item.query,
      summary: item.summary,
      sources: [],
      script: item.script,
    })
  }

  // ---------------- Auth gate ----------------
  if (!user) {
    return (
      <div className="auth-wrap">
        <div className="auth-card">
          <SpotlightText
            text="StoryForge Agent"
            brightColor="var(--clay)"
            dimColor="rgba(237, 230, 221, 0.22)"
            maskSize={160}
            intensity={12}
          />
          <p className="sub">
            Sign in to research any topic and forge a ready-to-record short-form
            video script — your work is saved to your account.
          </p>

          {showReset ? (
            <>
              <div className="field">
                <label>Email</label>
                <input
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="you@email.com"
                />
              </div>
              <ShinyButton
                onClick={async () => {
                  const ok = await auth.reset(resetEmail)
                  setResetMsg(
                    ok
                      ? 'Password reset email sent. Check your inbox.'
                      : auth.error
                  )
                }}
                disabled={auth.busy}
              >
                Send reset link
              </ShinyButton>
              {resetMsg && <div className="error">{resetMsg}</div>}
              <button
                className="ghost"
                style={{ marginTop: '0.8rem' }}
                onClick={() => setShowReset(false)}
              >
                Back to sign in
              </button>
            </>
          ) : (
            <>
              <div className="tabs">
                <button
                  className={tab === 'signin' ? 'on' : ''}
                  onClick={() => setTab('signin')}
                >
                  Sign in
                </button>
                <button
                  className={tab === 'signup' ? 'on' : ''}
                  onClick={() => setTab('signup')}
                >
                  Create account
                </button>
              </div>

              <AuthForm
                tab={tab}
                auth={auth}
                onDone={() => {}}
              />
              <button
                className="ghost"
                style={{ marginTop: '0.9rem' }}
                onClick={() => {
                  setShowReset(true)
                  setResetEmail('')
                  setResetMsg('')
                }}
              >
                Forgot password?
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  const initial = (
    (user.display_name || user.email || '?')[0] || '?'
  ).toUpperCase()

  // ---------------- Authenticated app ----------------
  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <span className="dot" />
          StoryForge <span className="accent">Agent</span>
        </div>
        <button
          className="btn-new"
          onClick={() => {
            setDoc(null)
            setQuery('')
          }}
        >
          + New research
        </button>
        <button
          className="acct-row"
          onClick={() => setAcctOpen(true)}
          style={{ marginTop: '0.4rem' }}
        >
          <span className="avatar">{initial}</span>
          <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden' }}>
            {user.display_name || user.email}
          </span>
        </button>

        <div className="side-label">Recent research</div>
        {history.length === 0 && (
          <div style={{ color: 'var(--bone-soft)', fontSize: '0.82rem' }}>
            No research yet.
          </div>
        )}
        {history.map((h) => (
          <div
            key={h.id}
            className={`conv ${doc && doc.query === h.query ? 'active' : ''}`}
            onClick={() => onPick(h)}
          >
            <span className="title">{h.query}</span>
            <button
              className="del"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(h.id)
              }}
              title="Delete"
            >
              ×
            </button>
          </div>
        ))}
      </aside>

      {/* Main */}
      <main className="main">
        <div className="scroll">
          {!doc ? (
            <div className="empty">
              <SpotlightText
                text="StoryForge Agent"
                brightColor="var(--bone)"
                dimColor="rgba(237, 230, 221, 0.18)"
                maskSize={180}
                intensity={10}
              />
              <p>
                Ask any topic — get a real-time research brief and a
                ready-to-record short-form video script.
              </p>
            </div>
          ) : (
            <div className="canvas fade-in">
              <h1 className="doc-title">{doc.query}</h1>
              <div className="doc-meta">
                <span>⏱ {duration}s</span>
                <span>🎭 {tone}</span>
                <span>🌐 {doc.sources?.length || 0} sources</span>
              </div>
              <div className="doc-actions">
                <button
                  className="btn"
                  onClick={() => navigator.clipboard.writeText(doc.summary)}
                >
                  Copy brief
                </button>
                <button
                  className="btn"
                  onClick={() => navigator.clipboard.writeText(doc.script)}
                >
                  Copy script
                </button>
                <a
                  className="btn"
                  href={`data:text/markdown;charset=utf-8,${encodeURIComponent(
                    `# ${doc.query}\n\n## Research Brief\n\n${doc.summary}\n\n## Video Script\n\n${doc.script}`
                  )}`}
                  download={`storyforge_${doc.query
                    .slice(0, 40)
                    .replace(/\s+/g, '_')}.md`}
                >
                  Download (.md)
                </a>
              </div>

              <ElectricBorder className="doc-sec" glowColor="var(--clay)" borderRadius={14}>
                <h2>Research Brief</h2>
                <div
                  className="body"
                  style={{ whiteSpace: 'pre-wrap' }}
                >
                  {doc.summary}
                </div>
                {doc.sources?.length > 0 && (
                  <>
                    <h3 style={{ marginTop: '1rem', fontSize: '1rem' }}>
                      Sources
                    </h3>
                    <ul className="sources">
                      {doc.sources.map((s, i) => (
                        <li key={i}>
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {s.title || s.url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </ElectricBorder>

              <ElectricBorder className="doc-sec" glowColor="var(--clay)" borderRadius={14}>
                <h2>Video Script</h2>
                <div className="body" style={{ whiteSpace: 'pre-wrap' }}>
                  {doc.script}
                </div>
              </ElectricBorder>
            </div>
          )}
        </div>

        {/* Options + composer */}
        <div className="options">
          <label>
            Length: {duration}s
            <br />
            <input
              type="range"
              min="15"
              max="90"
              step="5"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
            />
          </label>
          <label>
            Sources: {sources}
            <br />
            <input
              type="range"
              min="3"
              max="10"
              value={sources}
              onChange={(e) => setSources(Number(e.target.value))}
            />
          </label>
          <div>
            Tone
            <div className="tone-seg">
              {TONES.map((t) => (
                <button
                  key={t}
                  className={tone === t ? 'on' : ''}
                  onClick={() => setTone(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <button
            className={`btn model-toggle ${showModel ? 'on' : ''}`}
            onClick={() => setShowModel((s) => !s)}
            title="Choose any LLM provider"
          >
            🧠 Model: {llm.provider === 'default' ? 'Server default' : llm.provider}
          </button>
        </div>
        {showModel && (
          <div className="model-panel">
            <label>
              Provider
              <select
                value={llm.provider}
                onChange={(e) =>
                  setLlm({ ...llm, provider: e.target.value })
                }
              >
                <option value="default">Server default (Gemini)</option>
                <option value="gemini">Gemini (own key)</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="ollama">Ollama (local)</option>
                <option value="openai-compatible">OpenAI-compatible</option>
              </select>
            </label>
            {llm.provider !== 'default' && llm.provider !== 'ollama' && (
              <label>
                API key
                <input
                  type="password"
                  value={llm.api_key}
                  onChange={(e) => setLlm({ ...llm, api_key: e.target.value })}
                  placeholder={
                    llm.provider === 'anthropic'
                      ? 'sk-ant-...'
                      : llm.provider === 'openai'
                      ? 'sk-...'
                      : 'AIza...'
                  }
                />
              </label>
            )}
            <label>
              Model
              <input
                value={llm.model}
                onChange={(e) => setLlm({ ...llm, model: e.target.value })}
                placeholder={
                  llm.provider === 'openai'
                    ? 'gpt-4o-mini'
                    : llm.provider === 'anthropic'
                    ? 'claude-3-5-sonnet-latest'
                    : llm.provider === 'ollama'
                    ? 'llama3.1'
                    : llm.provider === 'openai-compatible'
                    ? 'openrouter/...'
                    : 'gemini-2.0-flash'
                }
              />
            </label>
            {(llm.provider === 'openai-compatible' || llm.provider === 'ollama') && (
              <label>
                Base URL
                <input
                  value={llm.base_url}
                  onChange={(e) => setLlm({ ...llm, base_url: e.target.value })}
                  placeholder={
                    llm.provider === 'ollama'
                      ? 'http://localhost:11434'
                      : 'https://openrouter.ai/api/v1'
                  }
                />
              </label>
            )}
            <div className="model-note">
              Keys are stored only in this browser (localStorage) and sent
              directly to your chosen provider.
            </div>
          </div>
        )}
        <div className="composer-bar">
          <div className="composer">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') runForge(query)
              }}
              placeholder="Research any topic — e.g. The James Webb telescope's latest discoveries"
            />
            <ShinyButton onClick={() => runForge(query)} disabled={busy}>
              {busy ? <span className="spinner" /> : '⚡ Forge'}
            </ShinyButton>
          </div>
          {pipeError && (
            <div className="error" style={{ marginTop: '0.5rem' }}>
              {pipeError}
            </div>
          )}
        </div>
      </main>

      {acctOpen && (
        <AccountModal
          auth={auth}
          onClose={() => setAcctOpen(false)}
        />
      )}
    </div>
  )
}

// ---------------- Auth form ----------------
function AuthForm({ tab, auth }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const submit = async () => {
    if (tab === 'signin') await auth.signin(email, password)
    else await auth.signup(email, password, name)
  }
  return (
    <>
      {tab === 'signup' && (
        <div className="field">
          <label>Display name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="optional"
          />
        </div>
      )}
      <div className="field">
        <label>Email</label>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@email.com"
        />
      </div>
      <div className="field">
        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />
      </div>
      <ShinyButton onClick={submit} disabled={auth.busy}>
        {auth.busy ? (
          <span className="spinner" />
        ) : tab === 'signin' ? (
          'Sign in'
        ) : (
          'Create account'
        )}
      </ShinyButton>
      {auth.error && <div className="error">{auth.error}</div>}
    </>
  )
}

// ---------------- Account modal ----------------
function AccountModal({ auth, onClose }) {
  const { user } = auth
  const [name, setName] = useState(user.display_name || '')
  const [confirmDel, setConfirmDel] = useState(false)
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Account</h3>
        <div style={{ color: 'var(--bone-soft)', fontSize: '0.85rem' }}>
          {user.email}
        </div>
        <div className="field" style={{ marginTop: '1rem' }}>
          <label>Display name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <ShinyButton
          onClick={async () => {
            await auth.updateName(name)
            onClose()
          }}
        >
          Save name
        </ShinyButton>

        <hr style={{ border: 'none', borderTop: '1px solid var(--hair)', margin: '1.4rem 0' }} />
        <div style={{ fontWeight: 600, color: '#e8917a' }}>Danger zone</div>
        <div style={{ fontSize: '0.82rem', color: 'var(--bone-soft)' }}>
          Permanently delete your account and all saved history.
        </div>
        {!confirmDel ? (
          <button
            className="btn"
            style={{ marginTop: '0.8rem', borderColor: '#e8917a', color: '#e8917a' }}
            onClick={() => setConfirmDel(true)}
          >
            Delete account
          </button>
        ) : (
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.8rem' }}>
            <ShinyButton
              onClick={async () => {
                await auth.remove()
                onClose()
              }}
            >
              Yes, delete
            </ShinyButton>
            <button className="btn" onClick={() => setConfirmDel(false)}>
              Cancel
            </button>
          </div>
        )}
        <button className="ghost" style={{ marginTop: '1rem' }} onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  )
}
