import { useState, useEffect, useCallback } from 'react'
import { api } from './api.js'

const KEY = 'storyforge.user'

export function useAuth() {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (user) localStorage.setItem(KEY, JSON.stringify(user))
    else localStorage.removeItem(KEY)
  }, [user])

  const signin = useCallback(async (email, password) => {
    setBusy(true)
    setError('')
    try {
      const u = await api.signin(email, password)
      setUser(u)
      return true
    } catch (e) {
      setError(e.message)
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  const signup = useCallback(async (email, password, name) => {
    setBusy(true)
    setError('')
    try {
      const u = await api.signup(email, password, name)
      setUser(u)
      return true
    } catch (e) {
      setError(e.message)
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  const reset = useCallback(async (email) => {
    setBusy(true)
    setError('')
    try {
      await api.reset(email)
      return true
    } catch (e) {
      setError(e.message)
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  const updateName = useCallback(
    async (name) => {
      if (!user) return
      await api.updateProfile(user.id_token, name)
      setUser({ ...user, display_name: name })
    },
    [user]
  )

  const remove = useCallback(async () => {
    if (!user) return
    await api.deleteAccount(user.id_token, user.uid)
    setUser(null)
  }, [user])

  const signout = useCallback(() => setUser(null), [])

  return { user, busy, error, setError, signin, signup, reset, updateName, remove, signout }
}
