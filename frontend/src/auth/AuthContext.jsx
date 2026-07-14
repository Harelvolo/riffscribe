import { createContext, useContext, useState } from 'react'
import { apiUrl } from '../api'

const STORAGE_KEY = 'gtabs_session'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  })

  const signIn = ({ session_token, profile }) => {
    const next = { sessionToken: session_token, profile }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSession(next)
  }

  const signOut = () => {
    if (session?.sessionToken) {
      fetch(apiUrl('/api/auth/logout'), {
        method: 'POST',
        headers: { 'X-Session-Token': session.sessionToken },
      }).catch(() => {})
    }
    localStorage.removeItem(STORAGE_KEY)
    setSession(null)
  }

  const updateProfile = (partialProfile) => {
    setSession((prev) => {
      if (!prev) return prev
      const next = { ...prev, profile: { ...prev.profile, ...partialProfile } }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }

  const authHeaders = session?.sessionToken ? { 'X-Session-Token': session.sessionToken } : {}

  return (
    <AuthContext.Provider value={{ session, signIn, signOut, updateProfile, authHeaders }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
