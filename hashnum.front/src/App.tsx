import React from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AuthProvider } from './auth'
import Protected from './Protected'
import Login from './pages/Login'
import Dashboard from './pages'  

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    element: <Protected />,
    children: [{ path: '/', element: <Dashboard /> }],
  },
])

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}

