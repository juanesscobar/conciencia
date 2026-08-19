import { useQuery } from '@tanstack/react-query'
import { auditApi } from '../services/api'
import { useState } from 'react'
import { LoadingState, ErrorState, EmptyState } from '../components/StateViews'

interface AuditEvent {
  id: string
  timestamp: string
  actor: string
  actor_type: string
  project_id?: string | null
  task_id?: string | null
  event_type: string
  payload?: any
  correlation_id?: string | null
}

export default function Audit() {
  const [filter, setFilter] = useState('')
  const { data: events, isLoading, isError, refetch } = useQuery<AuditEvent[]>({
    queryKey: ['audit'],
    queryFn: () => auditApi.getAll({ limit: 100 }).then(res => res.data),
    refetchInterval: 20000,
  })

  if (isLoading) return <LoadingState label="Fetching audit log..." />
  if (isError) return <ErrorState message="No se pudo consultar el audit log." onRetry={() => refetch()} />

  const filtered = (events || []).filter(e =>
    !filter || e.event_type.toLowerCase().includes(filter.toLowerCase()) || (e.actor || '').toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// AUDIT</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ append-only · accountability trail</p>
        </div>
        <input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="filtrar por tipo o actor..."
          className="px-3 py-2 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50 w-56"
        />
      </div>

      <div className="hack-card overflow-hidden">
        {filtered.length > 0 ? (
          <table className="min-w-full divide-y divide-bg-800 text-xs">
            <thead className="bg-bg-800">
              <tr>
                <th className="px-4 py-3 text-left text-primary-400 font-medium tracking-wider">Time</th>
                <th className="px-4 py-3 text-left text-primary-400 font-medium tracking-wider">Event</th>
                <th className="px-4 py-3 text-left text-primary-400 font-medium tracking-wider">Actor</th>
                <th className="px-4 py-3 text-left text-primary-400 font-medium tracking-wider">Type</th>
                <th className="px-4 py-3 text-left text-primary-400 font-medium tracking-wider">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bg-800">
              {filtered.map((e) => (
                <tr key={e.id} className="hover:bg-bg-800/50">
                  <td className="px-4 py-2.5 text-gray-500 font-mono whitespace-nowrap">{new Date(e.timestamp).toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-gray-200 font-mono">{e.event_type}</td>
                  <td className="px-4 py-2.5 text-gray-400">{e.actor_type}:{e.actor}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-2 py-0.5 text-[10px] rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/40">
                      {e.actor_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 font-mono max-w-xs truncate">
                    {e.payload ? JSON.stringify(e.payload) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-6">
            <EmptyState
              title={filter ? 'Sin resultados para el filtro' : 'Audit log vacío'}
              message="Los eventos importantes (aprobaciones, deploys, cambios) se registran acá de forma inmutable."
            />
          </div>
        )}
      </div>
      <p className="text-xs text-gray-700 mt-3">
        🔒 Append-only: los eventos de auditoría no se pueden modificar ni borrar desde la aplicación.
      </p>
    </div>
  )
}
