import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function DeepSeekSettings() {
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const { data: status } = useQuery({
    queryKey: ['deepseek-status'],
    queryFn: () => api.get('/api/v1/settings/deepseek').then(res => res.data),
  })

  const saveKey = useMutation({
    mutationFn: (key: string) => api.put('/api/v1/settings/deepseek', { api_key: key }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deepseek-status'] })
      setApiKey('')
      setSuccess('API key guardada. Los agentes ahora usan DeepSeek real.')
      setTimeout(() => setSuccess(''), 4000)
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Error al guardar la key')
      setTimeout(() => setError(''), 4000)
    },
  })

  const removeKey = useMutation({
    mutationFn: () => api.delete('/api/v1/settings/deepseek'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deepseek-status'] })
      setSuccess('API key eliminada. Los agentes vuelven a modo simulado.')
      setTimeout(() => setSuccess(''), 4000)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) return
    setError('')
    saveKey.mutate(apiKey.trim())
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'ceo'

  return (
    <div className="hack-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
        <span className="text-xs text-gray-500">// llm_config — deepseek</span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
          status?.configured
            ? 'bg-primary-500/10 text-primary-400 border-primary-500/40'
            : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/40'
        }`}>
          {status?.configured ? '● CONFIGURADO' : '○ SIN KEY'}
        </span>
      </div>

      <div className="p-4">
        <p className="text-xs text-gray-500 mb-3">
          {status?.configured
            ? `DeepSeek activo — los agentes ejecutan con IA real (key guardada ${status?.updated_at ? new Date(status.updated_at).toLocaleDateString() : ''}).`
            : 'Conectá tu API key de DeepSeek para que los agentes ejecuten tareas con IA real. Sin key, corren en modo simulado.'}
        </p>

        {isAdmin ? (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                className="hack-input text-sm flex-1"
                placeholder="sk-..."
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="px-3 py-2 border border-bg-700 rounded-lg text-gray-500 hover:text-gray-300 text-xs"
                title={showKey ? 'Ocultar' : 'Mostrar'}
              >
                {showKey ? '🙈' : '👁'}
              </button>
            </div>

            {error && (
              <div className="bg-alert-500/10 border border-alert-500/40 text-alert-400 px-3 py-2 rounded text-xs">
                ✗ {error}
              </div>
            )}
            {success && (
              <div className="bg-primary-500/10 border border-primary-500/40 text-primary-400 px-3 py-2 rounded text-xs">
                ✓ {success}
              </div>
            )}

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saveKey.isPending || !apiKey.trim()}
                className="flex-1 px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 text-xs transition-all"
              >
                {saveKey.isPending ? 'GUARDANDO...' : '[ GUARDAR KEY ]'}
              </button>
              {status?.configured && (
                <button
                  type="button"
                  onClick={() => removeKey.mutate()}
                  disabled={removeKey.isPending}
                  className="px-4 py-2 border border-alert-500/40 text-alert-400 rounded-lg hover:bg-alert-500/10 text-xs disabled:opacity-50"
                >
                  [ QUITAR ]
                </button>
              )}
            </div>
            <p className="text-[10px] text-gray-700">
              Obtené tu key en <span className="text-primary-500">https://platform.deepseek.com</span> — solo admin puede cambiar esto.
            </p>
          </form>
        ) : (
          <p className="text-xs text-yellow-400">
            ⚠ Necesitás rol admin para configurar la API key.
          </p>
        )}
      </div>
    </div>
  )
}
