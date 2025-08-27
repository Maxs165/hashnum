import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { API } from './api' 

type AuthCtx = {
  ready: boolean
  authed: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  ensure: () => Promise<void>
}

const Ctx = createContext<AuthCtx | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false)
  const [authed, setAuthed] = useState(false)

  async function ensure() {
    try {
      await API.post('/token')        
      setAuthed(true)
    } catch {
      setAuthed(false)
    } finally {
      setReady(true)
    }
  }

  async function login(username: string, password: string) {
    await API.post('/token', { username, password }) 
    setAuthed(true)
  }

  async function logout() {
    try { await API.post('/logout') } finally { setAuthed(false) }
  }

  useEffect(() => { void ensure() }, [])

  const value = useMemo(() => ({ ready, authed, login, logout, ensure }), [ready, authed])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
