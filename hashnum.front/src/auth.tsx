import { createContext, useContext, useEffect, useState } from 'react'
import axios, { AxiosError, AxiosRequestConfig } from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

declare module 'axios' {
  export interface AxiosRequestConfig {
    __isRetryRequest?: boolean
  }
}

export const API = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

type AuthCtx = {
  ready: boolean
  authed: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  ensure: () => Promise<void>
}

const Ctx = createContext<AuthCtx>(null!)

// ===== Refresh токена по 401 =====
let isRefreshing = false
let pending: Array<(ok: boolean) => void> = []
const onRefreshed = (ok: boolean) => {
  pending.forEach(fn => fn(ok))
  pending = []
}

API.interceptors.response.use(
  r => r,
  async (error: AxiosError) => {
    const res = error.response
    const original = error.config as AxiosRequestConfig & { __isRetryRequest?: boolean }

    if (res?.status === 401 && !original.__isRetryRequest) {
      original.__isRetryRequest = true

      if (isRefreshing) {
        // ждём исход refresh
        return new Promise((resolve, reject) => {
          pending.push(ok => (ok ? resolve(API(original)) : reject(error)))
        })
      }

      try {
        isRefreshing = true
        await API.post('/token')   // refresh по куке
        onRefreshed(true)
        return API(original)
      } catch {
        onRefreshed(false)
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// ===== Провайдер =====
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    // при старте пробуем обновить токен
    ;(async () => {
      try {
        await API.post('/token')
        setAuthed(true)
      } catch (e) {
        setAuthed(false)
      } finally {
        // ВАЖНО: чтобы не было «чёрного экрана», всегда ставим ready=true
        setReady(true)
      }
    })()
  }, [])

  async function login(username: string, password: string) {
    await API.post('/login', { username, password })
    setAuthed(true)
  }

  async function logout() {
    try { await API.post('/logout') } catch {}
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
