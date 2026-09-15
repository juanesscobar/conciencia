import { useState, FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

/**
 * Login del Control Plane — lenguaje visual del rediseño (2026-09-13):
 * azul profundo + violeta + cyan · Geist (títulos) + JetBrains Mono (UI).
 * La lógica de autenticación es la misma que antes (login/register + redirect).
 */
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
    <div
      className="relative flex min-h-screen items-center justify-center overflow-hidden"
      style={{
        background:
          'radial-gradient(900px 420px at 80% -10%, rgba(124,108,255,0.16), transparent 62%), radial-gradient(700px 380px at 5% 110%, rgba(102,217,232,0.10), transparent 60%), var(--cd-bg-deep)',
        color: 'var(--cd-text-primary)',
        fontFamily: 'var(--cd-font-mono)',
      }}
    >
      <div
        className="relative w-full max-w-md overflow-hidden border"
        style={{
          background: 'var(--cd-surface)',
          borderColor: 'var(--cd-border-subtle)',
          borderRadius: 'var(--cd-radius)',
        }}
      >
        {/* barra superior (terminal) */}
        <div
          className="flex items-center gap-2 border-b px-3 py-2.5"
          style={{ background: 'var(--cd-surface-raised)', borderColor: 'var(--cd-border-subtle)' }}
        >
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: 'var(--cd-danger)' }} />
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: 'var(--cd-warning)' }} />
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: 'var(--cd-success)' }} />
          <span className="ml-2 text-[11px]" style={{ color: 'var(--cd-text-muted)' }}>
            auth://conciencia-platform
          </span>
          <span
            className="ml-auto rounded-full border px-1.5 py-[1px] text-[10px]"
            style={{ borderColor: 'var(--cd-border-subtle)', color: 'var(--cd-text-muted)' }}
          >
            control plane
          </span>
        </div>

        <div className="p-6">
          {/* identidad */}
          <div className="mb-6">
            <p
              className="text-[11px] uppercase tracking-[0.14em]"
              style={{ color: 'var(--cd-text-muted)' }}
            >
              {isRegister ? 'registro de operador' : 'acceso al control plane'}
            </p>
            <h1
              className="mt-2 text-2xl font-semibold"
              style={{ fontFamily: 'var(--cd-font-sans)', color: 'var(--cd-text-primary)' }}
            >
              conciencia<span style={{ color: 'var(--cd-brand-violet)' }}>.</span>
            </h1>
            <p className="mt-1 text-[12.5px]" style={{ color: 'var(--cd-text-secondary)' }}>
              Control para el trabajo autónomo.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {isRegister && (
              <Field
                id="email"
                label="email"
                type="email"
                value={email}
                onChange={setEmail}
                placeholder="you@example.com"
                autoComplete="email"
              />
            )}

            <Field
              id="username"
              label="username"
              type="text"
              value={username}
              onChange={setUsername}
              placeholder="operator"
              autoComplete="username"
            />

            <Field
              id="password"
              label="password"
              type="password"
              value={password}
              onChange={setPassword}
              placeholder="••••••••"
              autoComplete="current-password"
            />

            {error && (
              <div
                role="alert"
                className="border px-3 py-2 text-[12.5px]"
                style={{
                  background: 'rgba(237,113,130,0.08)',
                  borderColor: 'rgba(237,113,130,0.35)',
                  borderRadius: 'var(--cd-radius)',
                  color: 'var(--cd-danger)',
                }}
              >
                <span aria-hidden="true">✗ </span>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="cd-focus w-full border px-4 py-2.5 text-[13px] font-semibold uppercase tracking-[0.08em] transition-colors duration-150 disabled:opacity-50"
              style={{
                background: 'var(--cd-brand-violet)',
                borderColor: 'var(--cd-brand-violet)',
                borderRadius: 'var(--cd-radius)',
                color: 'var(--cd-bg-deep)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--cd-brand-violet-hover)'
                e.currentTarget.style.borderColor = 'var(--cd-brand-violet-hover)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--cd-brand-violet)'
                e.currentTarget.style.borderColor = 'var(--cd-brand-violet)'
              }}
            >
              {loading ? 'autenticando…' : isRegister ? 'crear operador' : 'entrar'}
            </button>
          </form>

          <div className="mt-5 text-center">
            <button
              type="button"
              onClick={() => setIsRegister(!isRegister)}
              className="cd-focus text-[12px]"
              style={{ color: 'var(--cd-text-muted)' }}
            >
              {isRegister ? '< volver al login' : '// sin cuenta? registrar operador'}
            </button>
          </div>
        </div>

        <div
          className="border-t px-6 py-3 text-center"
          style={{ borderColor: 'var(--cd-border-subtle)' }}
        >
          <p className="text-[11px]" style={{ color: 'var(--cd-text-muted)' }}>
            Conciencia Platform · agent orchestration engine
          </p>
        </div>
      </div>
    </div>
  )
}

function Field({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
}: {
  id: string
  label: string
  type: string
  value: string
  onChange: (v: string) => void
  placeholder: string
  autoComplete: string
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-[11px] uppercase tracking-[0.12em]"
        style={{ color: 'var(--cd-text-muted)' }}
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required
        className="cd-focus w-full border px-3 py-2 text-[13.5px] outline-none transition-colors duration-150"
        style={{
          background: 'var(--cd-bg)',
          borderColor: 'var(--cd-border-subtle)',
          borderRadius: 'var(--cd-radius)',
          color: 'var(--cd-text-primary)',
          caretColor: 'var(--cd-signal-cyan)',
        }}
      />
    </div>
  )
}
