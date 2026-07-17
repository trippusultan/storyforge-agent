// Thin fetch wrapper around the API gateway.
// On Firebase Hosting, set VITE_API_BASE to the deployed backend URL
// (e.g. https://storyforge-api.onrender.com). Locally it defaults to "/api".
const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

async function req(method, path, body, idToken) {
  const headers = { 'Content-Type': 'application/json' }
  if (idToken) headers['Authorization'] = `Bearer ${idToken}`
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (netErr) {
    throw new Error('Network error — is the server running?')
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const d = await res.json()
      if (d && d.detail) msg = d.detail
    } catch (_) {
      // non-JSON error body; keep the status-based message
    }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  forge: (payload) => req('POST', '/forge', payload),
  signup: (email, password, displayName) =>
    req('POST', '/auth/signup', { email, password, display_name: displayName }),
  signin: (email, password) => req('POST', '/auth/signin', { email, password }),
  reset: (email) => req('POST', '/auth/reset', { email }),
  updateProfile: (idToken, displayName) =>
    req('POST', '/auth/profile', { id_token: idToken, display_name: displayName }),
  deleteAccount: (idToken, uid) =>
    req('POST', '/auth/delete', { id_token: idToken, uid }),
  listHistory: (uid, idToken) =>
    req('GET', `/history/${uid}?id_token=${encodeURIComponent(idToken)}`),
  addHistory: (uid, idToken, entry) =>
    req('POST', `/history/${uid}?id_token=${encodeURIComponent(idToken)}`, entry),
  deleteHistory: (uid, entryId, idToken) =>
    req(
      'DELETE',
      `/history/${uid}/${entryId}?id_token=${encodeURIComponent(idToken)}`
    ),
}
