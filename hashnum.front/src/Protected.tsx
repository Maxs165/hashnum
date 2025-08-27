import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './auth'

export default function Protected() {
  const { ready, authed } = useAuth()
  const loc = useLocation()

  if (!ready) {
    return (
      <div className="container">
        <div className="card">Загрузка…</div>
      </div>
    )
  }

  if (!authed) {
    return <Navigate to="/login" state={{ from: loc }} replace />
  }

  return <Outlet />
}
