import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { assistantApi } from '../services/api'
import { useLocation, useNavigate } from 'react-router-dom'

interface AskResult {
  answer: string
  simulated: boolean
  model?: string
  provider?: string
  state?: any
}

export default function AskConciencia({ onClose, initialQuery }: { onClose: () => void; initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery || '')
  const navigate = useNavigate()
  const location = useLocation()

  const ask = useMutation<AskResult, any, string>({
    mutationFn: (q: string) =>
      assistantApi.ask(q, {
        route: location.pathname,
        entity_type: location.pathname.split('/')[1] || 'dashboard',
        entity_name: location.pathname.split('/')[1] || 'Mission Control',
      }).then(res => res.data),
  })

  const submit = () => {
    if (!query.trim()) return
    ask.mutate(query)
  }

  // Extraer acciones sugeridas del formato "ACCIONES:\nir /approvals"
  const actions = (ask.data?.answer || '').split('\n')
    .filter(l => l.trim().startsWith('ir ') || l.trim().startsWith('abrir ') || l.trim().startsWith('aprobar '))
    .map(l => l.trim())

  const runAction = (a: string) => {
    const target = a.replace(/^ir\s+/i, '').replace(/^abrir\s+/i, '').trim()
    if (target.startsWith('/')) navigate(target)
  }

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-96 bg-bg-900 border-l border-bg-700 z-50 flex flex-col shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-bg-700 bg-bg-950">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse inline-block"></span>
          <span className="text-sm font-bold text-primary-400 tracking-wider">CONCIENCIA</span>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-primary-300 text-xl" aria-label="Cerrar">✕</button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!ask.data && !ask.isPending && (
          <div className="text-xs text-gray-600 space-y-2">
            <p className="text-gray-500 font-semibold tracking-wider">CAPABILITIES</p>
            <p>🔍 <span className="text-primary-400">OBSERVE</span> — what is running? qué falló? cuánto gastamos?</p>
            <p>💡 <span className="text-primary-400">EXPLAIN</span> — why did this fail? por qué se eligió este modelo?</p>
            <p>⚡ <span className="text-primary-400">ACT</span> — retry, pause, run workflow, aprobar (siempre con policies)</p>
            <p className="pt-2 text-gray-700">Uso el mismo Control Plane que la UI: sin arquitectura paralela. Entiendo el contexto de la pantalla donde estás.</p>
          </div>
        )}

        {ask.isPending && (
          <div className="flex items-center gap-2 text-sm text-primary-400 animate-blink">
            <span className="w-2 h-2 rounded-full bg-primary-500 inline-block"></span> consultando control plane...
          </div>
        )}

        {ask.data && (
          <div className="bg-bg-950 border border-bg-700 rounded-lg p-3">
            <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{ask.data.answer}</p>
            <p className="text-[10px] text-gray-700 mt-2 font-mono">
              {ask.data.simulated ? 'simulated' : `${ask.data.provider} · ${ask.data.model}`}
            </p>
          </div>
        )}

        {actions.length > 0 && (
          <div className="space-y-2">
            {actions.map((a, i) => (
              <button
                key={i}
                onClick={() => runAction(a)}
                className="w-full text-left px-3 py-2 text-xs rounded-lg border border-primary-500/30 text-primary-400 hover:bg-primary-500/10 transition-colors"
              >
                ▸ {a}
              </button>
            ))}
          </div>
        )}

        {ask.isError && (
          <p className="text-xs text-alert-400">✗ {(ask.error as any)?.response?.data?.detail || 'Error consultando el control plane'}</p>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-bg-700">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') submit() }}
            placeholder="Ask about your system..."
            autoFocus
            className="flex-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
          />
          <button
            onClick={submit}
            disabled={!query.trim() || ask.isPending}
            className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
          >
            ⏎
          </button>
        </div>
        <p className="text-[10px] text-gray-700 mt-2">OBSERVE · EXPLAIN · ACT — siempre vía Control Plane</p>
      </div>
    </div>
  )
}
