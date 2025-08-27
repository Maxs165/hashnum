import { createContext, useContext, useEffect, useState } from 'react'
import { API } from './api'

type AuthCtx = {
  ready: boolean
  authed: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  ensure: () => Promise<void>
}

const Ctx = createContext<AuthCtx>(null!)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    (async () => {
      try {
        await API.post('/token')       
        setAuthed(true)
      } catch {
        setAuthed(false)
      } finally {
        setReady(true)
      }
    })()
  }, [])

  async function login(username: string, password: string) {
    await API.post('/token', { username, password })
    setAuthed(true)
  }

  async function logout() {
    await API.post('/logout')
    setAuthed(false)
  }

  async function ensure() {
    try {
      await API.post('/token')
      setAuthed(true)
    } catch {
      setAuthed(false)
    }
  }

  return (
    <Ctx.Provider value={{ ready, authed, login, logout, ensure }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAuth() {
  return useContext(Ctx)
}
