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

let isRefreshing = false
let pending: Array<(ok: boolean) => void> = []

function onRefreshed(ok: boolean) {
  pending.forEach(fn => fn(ok))
  pending = []
}

export async function ensureToken() {
  return API.post('/token').catch(() => {})
}

API.interceptors.response.use(
  r => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig | undefined
    const status = error.response?.status
    const isTokenCall = typeof original?.url === 'string' && original.url.endsWith('/token')
    if (isTokenCall) return Promise.reject(error)

    if (status === 401 && original && !original.__isRetryRequest) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pending.push(ok => (ok ? resolve(API(original)) : reject(error)))
        })
      }

      original.__isRetryRequest = true
      isRefreshing = true
      try {
        await API.post('/token')         
        onRefreshed(true)
        return API(original)               
      } catch (e) {
        onRefreshed(false)
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)
