import React, { useState } from 'react'
import { useAuth } from './auth'

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    try {
      await login(username, password)
    } catch {
      setErr('Ошибка входа. Проверь логин/пароль.')
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
          <button className="btn" type="submit">Войти</button>
        </form>
        {err && <div style={{ marginTop: 12, color: '#f87171' }}>{err}</div>}
      </div>
    </div>
  )
}
