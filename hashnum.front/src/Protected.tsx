import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './auth'

export default function Protected() {
  const { ready, authed } = useAuth()
  if (!ready) return null 
  return authed ? <Outlet /> : <Navigate to="/login" replace />
}
