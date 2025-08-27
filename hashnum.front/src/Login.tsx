import React, { useState } from 'react'
import { useAuth } from './auth'
import { useNavigate, useLocation } from 'react-router-dom'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setErr(null)
    setBusy(true)
    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch {
      setErr('Ошибка входа. Проверь логин/пароль.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h2>Login</h2>
        <form onSubmit={onSubmit} className="row" style={{ marginTop: 12 }}>
          <input
            className="input"
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
          />
          <input
            className="input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
          <button className="btn" type="submit" disabled={busy || !username || !password}>
            {busy ? 'Входим…' : 'Войти'}
          </button>
        </form>
        {err && <div style={{ marginTop: 12, color: '#f87171' }}>{err}</div>}
      </div>
    </div>
  )
}
