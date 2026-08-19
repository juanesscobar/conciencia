import { useQuery } from '@tanstack/react-query'
import { tracesApi } from '../services/api'
import { LoadingState, ErrorState, EmptyState } from '../components/StateViews'

interface TraceItem {
  ts: string
  kind: string
  actor: string
  status: string
  summary: string
  error?: string | null
}

const kindStyles: Record<string, string> = {
  execution: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  workflow: 'bg-neon-500/10 text-neon-400 border border-neon-500/40',
  audit: 'bg-purple-500/10 text-purple-400 border border-purple-500/40',
}

const statusColor = (status: string) => {
  const s = status.toLowerCase()
  if (s.includes('fail') || s === 'error' || s === 'failed') return 'text-alert-400'
  if (s === 'completed' || s === 'recorded' || s === 'approved') return 'text-primary-400'
  if (s === 'running' || s === 'pending') return 'text-yellow-400'
  return 'text-gray-500'
}

export default function Traces() {
  const { data: items, isLoading, isError, refetch } = useQuery<TraceItem[]>({
    queryKey: ['traces'],
    queryFn: () => tracesApi.getAll(80).then(res => res.data),
    refetchInterval: 15000,
  })

  if (isLoading) return <LoadingState label="Fetching execution traces..." />
  if (isError) return <ErrorState message="No se pudo consultar traces." onRetry={() => refetch()} />

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// TRACES</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ execution · decision · action trace (sin chain-of-thought)</p>
        </div>
        <span className="text-xs text-gray-500 font-mono">{(items || []).length} eventos</span>
      </div>

      {items && items.length > 0 ? (
        <div className="hack-card p-5">
          <div className="relative border-l border-bg-700 ml-3 space-y-5">
            {items.map((t, i) => (
              <div key={`${t.ts}-${i}`} className="ml-6">
                <span className={`absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-bg-700 border-2 border-primary-500/60 inline-block`} style={{ marginLeft: -26 }} />
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-gray-600 font-mono">{new Date(t.ts).toLocaleString()}</span>
                  <span className={`px-2 py-0.5 text-[10px] rounded-full ${kindStyles[t.kind] || 'border border-bg-600 text-gray-500'}`}>
                    {t.kind.toUpperCase()}
                  </span>
                  <span className={`text-xs font-mono ${statusColor(t.status)}`}>● {t.status}</span>
                  <span className="text-xs text-gray-600 font-mono">{t.actor}</span>
                </div>
                <p className="text-sm text-gray-300 mt-1 break-words">{t.summary}</p>
                {t.error && <p className="text-xs text-alert-400 font-mono mt-1">✗ {t.error}</p>}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          title="Sin traces todavía"
          message="Las ejecuciones de agentes, workflow runs y eventos de auditoría aparecen acá como timeline unificado."
        />
      )}
      <p className="text-xs text-gray-700 mt-4">
        🔒 Los traces muestran acciones, tools y outcomes — nunca el razonamiento privado del modelo.
      </p>
    </div>
  )
}
