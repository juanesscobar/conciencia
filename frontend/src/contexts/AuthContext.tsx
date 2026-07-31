import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../services/api'

interface User {
  id: string
  email: string
  username: string
  display_name: string | null
  role: string
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

function getStoredToken(): string | null {
  return localStorage.getItem('mc_token')
}

function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem('mc_token', token)
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    localStorage.removeItem('mc_token')
    delete api.defaults.headers.common['Authorization']
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(getStoredToken)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = getStoredToken()
    if (stored) {
      api.defaults.headers.common['Authorization'] = `Bearer ${stored}`
      api.get('/api/v1/auth/me')
        .then(res => setUser(res.data))
        .catch(() => {
          setStoredToken(null)
          setToken(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    const res = await api.post('/api/v1/auth/login', { username, password })
    const newToken = res.data.access_token
    setStoredToken(newToken)
    setToken(newToken)
    const meRes = await api.get('/api/v1/auth/me')
    setUser(meRes.data)
  }

  const register = async (email: string, username: string, password: string) => {
    const res = await api.post('/api/v1/auth/register', { email, username, password })
    const newToken = res.data.access_token
    setStoredToken(newToken)
    setToken(newToken)
    const meRes = await api.get('/api/v1/auth/me')
    setUser(meRes.data)
  }

  const logout = () => {
    setStoredToken(null)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isAuthenticated: !!token }}>
      {!loading && children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
