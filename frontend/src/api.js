// Thin fetch wrapper around the FastAPI gateway.
const BASE = '/api'

async function req(method, path, body, idToken) {
  const headers = { 'Content-Type': 'application/json' }
  if (idToken) headers['Authorization'] = `Bearer ${idToken}`
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let msg = 'Request failed'
    try {
      const d = await res.json()
      msg = d.detail || msg
    } catch (_) {}
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
