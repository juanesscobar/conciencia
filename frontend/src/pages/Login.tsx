import { useState, FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = (location.state as any)?.from?.pathname || '/'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        await register(email, username, password)
      } else {
        await login(username, password)
      }
      navigate(from, { replace: true })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg-950 scanlines flex items-center justify-center relative overflow-hidden">
      {/* Líneas decorativas estilo grid hacker */}
      <div className="absolute inset-0 opacity-20" style={{
        backgroundImage: 'linear-gradient(rgba(0,255,65,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,65,0.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }}></div>

      <div className="relative max-w-md w-full bg-bg-900 border border-bg-700 rounded-xl shadow-neon p-8">
        <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700 rounded-t-lg -mt-8 -mx-8 mb-8">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-alert-500 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-yellow-500 inline-block"></span>
            <span className="w-3 h-3 rounded-full bg-green-500 inline-block"></span>
            <span className="ml-3 text-xs text-gray-600">auth://conciencia-platform</span>
          </div>
        </div>

        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary-400 tracking-widest">◉ CONCIENCIA PLATFORM</h1>
          <p className="text-gray-600 mt-2 text-sm">&gt; software_factory_governance.sh</p>
          <p className="text-primary-500/70 mt-1 text-xs">$ {isRegister ? 'register --new-operator' : 'login --operator'}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="hack-input"
                placeholder="you@example.com"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="hack-input"
              placeholder="operator"
              required
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="hack-input"
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="bg-alert-500/10 border border-alert-500/40 text-alert-400 px-4 py-2 rounded-lg text-sm">
              <span className="text-alert-500">✗</span> {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all"
          >
            {loading ? 'AUTHENTICATING...' : isRegister ? '[ REGISTER ]' : '[ LOGIN ]'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-xs text-gray-600 hover:text-primary-400 transition-colors"
          >
            {isRegister ? '< back to login' : '// no account? register operator'}
          </button>
        </div>

        <div className="mt-6 pt-4 border-t border-bg-800 text-center">
          <p className="text-xs text-gray-700 font-mono">Conciencia Platform v2.0 - agent orchestration engine</p>
        </div>
      </div>
    </div>
  )
}
