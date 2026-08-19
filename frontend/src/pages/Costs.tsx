import { useQuery } from '@tanstack/react-query'
import { costsApi } from '../services/api'
import { LoadingState, ErrorState, EmptyState } from '../components/StateViews'

interface CostSummary {
  total_usd: number
  today_usd: number
  week_usd: number
  total_tokens: number
  records: number
  by_provider: { provider: string; cost_usd: number; calls: number }[]
  by_model: { model: string; cost_usd: number; calls: number }[]
}

interface CostRecord {
  id: string
  timestamp: string
  provider: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost_usd: number
  metadata: any
}

function usd(v: number): string {
  return `$${v.toFixed(4)}`
}

export default function Costs() {
  const { data: summary, isLoading, isError, refetch } = useQuery<CostSummary>({
    queryKey: ['costs-summary'],
    queryFn: () => costsApi.summary().then(res => res.data),
    refetchInterval: 30000,
  })

  const { data: records } = useQuery<CostRecord[]>({
    queryKey: ['costs-records'],
    queryFn: () => costsApi.records(50).then(res => res.data),
    refetchInterval: 30000,
  })

  if (isLoading) return <LoadingState label="Fetching cost telemetry..." />
  if (isError) return <ErrorState message="No se pudo consultar costos." onRetry={() => refetch()} />

  const s = summary || { total_usd: 0, today_usd: 0, week_usd: 0, total_tokens: 0, records: 0, by_provider: [], by_model: [] }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// COSTS</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ llm harness · cost records</p>
        </div>
        <span className="text-xs text-gray-500 font-mono">{s.records} records</span>
      </div>

      {/* Resumen */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <CostCard label="TOTAL_USD" value={usd(s.total_usd)} />
        <CostCard label="TODAY" value={usd(s.today_usd)} accent />
        <CostCard label="LAST_7D" value={usd(s.week_usd)} />
        <CostCard label="TOTAL_TOKENS" value={s.total_tokens.toLocaleString()} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Por proveedor */}
        <div className="hack-card p-5">
          <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// BY_PROVIDER</h2>
          {s.by_provider.length > 0 ? (
            <div className="space-y-3">
              {s.by_provider.map((p) => {
                const max = Math.max(...s.by_provider.map(x => x.cost_usd), 0.0001)
                return (
                  <div key={p.provider}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-300">{p.provider}</span>
                      <span className="text-gray-500 font-mono">{usd(p.cost_usd)} · {p.calls} calls</span>
                    </div>
                    <div className="w-full bg-bg-800 rounded-full h-1.5 border border-bg-700">
                      <div className="h-1.5 rounded-full bg-primary-500" style={{ width: `${(p.cost_usd / max) * 100}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-xs text-gray-600">Sin uso de LLM registrado todavía. Los costos aparecen al ejecutar agentes.</p>
          )}
        </div>

        {/* Por modelo */}
        <div className="hack-card p-5">
          <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// BY_MODEL</h2>
          {s.by_model.length > 0 ? (
            <div className="space-y-2">
              {s.by_model.map((m) => (
                <div key={m.model} className="flex justify-between text-xs bg-bg-950/60 border border-bg-800 rounded-lg px-3 py-2">
                  <span className="text-gray-300 font-mono">{m.model}</span>
                  <span className="text-gray-500">{usd(m.cost_usd)} · {m.calls} calls</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-600">Sin datos por modelo.</p>
          )}
        </div>
      </div>

      {/* Records recientes */}
      <div className="hack-card p-5">
        <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// RECENT_RECORDS</h2>
        {records && records.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-bg-800 text-xs">
              <thead className="bg-bg-800">
                <tr>
                  <th className="px-4 py-2 text-left text-primary-400 font-medium">Time</th>
                  <th className="px-4 py-2 text-left text-primary-400 font-medium">Provider</th>
                  <th className="px-4 py-2 text-left text-primary-400 font-medium">Model</th>
                  <th className="px-4 py-2 text-right text-primary-400 font-medium">Tokens</th>
                  <th className="px-4 py-2 text-right text-primary-400 font-medium">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-bg-800">
                {records.map((r) => (
                  <tr key={r.id} className="hover:bg-bg-800/50">
                    <td className="px-4 py-2 text-gray-500 font-mono">{new Date(r.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-2 text-gray-300">{r.provider}</td>
                    <td className="px-4 py-2 text-gray-400 font-mono">{r.model}</td>
                    <td className="px-4 py-2 text-right text-gray-400 font-mono">{r.total_tokens.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right text-primary-400 font-mono">{usd(r.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Sin registros de costo" message="Ejecutá un agente (Agents → run) y los costos del harness se persisten acá." />
        )}
      </div>
    </div>
  )
}

function CostCard({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`hack-card p-4 ${accent ? 'border-primary-500/40' : ''}`}>
      <p className="text-[10px] font-medium tracking-wider text-gray-600">{label}</p>
      <p className={`text-xl font-bold font-mono mt-1 ${accent ? 'text-primary-400' : 'text-gray-200'}`}>{value}</p>
    </div>
  )
}
