import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { policiesApi } from '../services/api'
import { useState } from 'react'
import { LoadingState, ErrorState, EmptyState } from '../components/StateViews'

interface AgentGov {
  id: string
  name: string
  role: string
  autonomy_level: string
  status: string
  runtime: string
  provider: string
  policies: number
}

interface Policy {
  id: string
  agent_id: string | null
  agent_name?: string
  action: string
  effect: string
  note?: string
  enabled: boolean
  created_at: string
}

const effectColors: Record<string, string> = {
  allow: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  approval: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  deny: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
}

const autonomyColors: Record<string, string> = {
  full: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  preview: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  approval: 'bg-orange-500/10 text-orange-400 border border-orange-500/40',
}

export default function Governance() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ agent_id: '', action: '', effect: 'approval', note: '' })
  const [msg, setMsg] = useState('')

  const { data: agents, isLoading, isError, refetch } = useQuery<AgentGov[]>({
    queryKey: ['policies-agents'],
    queryFn: () => policiesApi.agents().then(res => res.data),
  })

  const { data: policies } = useQuery<Policy[]>({
    queryKey: ['policies'],
    queryFn: () => policiesApi.getAll().then(res => res.data),
    refetchInterval: 15000,
  })

  const createPolicy = useMutation({
    mutationFn: () => policiesApi.create({
      agent_id: form.agent_id || null,
      action: form.action.trim(),
      effect: form.effect,
      note: form.note.trim() || undefined,
    }),
    onSuccess: () => {
      setForm({ agent_id: '', action: '', effect: 'approval', note: '' })
      setMsg('Policy creada')
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['policies-agents'] })
      setTimeout(() => setMsg(''), 4000)
    },
    onError: (e: any) => { setMsg(e.response?.data?.detail || 'Error'); setTimeout(() => setMsg(''), 5000) },
  })

  const deletePolicy = useMutation({
    mutationFn: (id: string) => policiesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      queryClient.invalidateQueries({ queryKey: ['policies-agents'] })
    },
  })

  if (isLoading) return <LoadingState label="Loading governance hierarchy..." />
  if (isError) return <ErrorState message="No se pudo cargar governance." onRetry={() => refetch()} />

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// GOVERNANCE</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ policies · identity · autonomy hierarchy</p>
        </div>
        <span className="text-xs text-gray-500 font-mono">{(policies || []).length} policies activas</span>
      </div>

      {/* Jerarquía de governance: agentes + autonomía */}
      <div className="hack-card p-5 mb-6">
        <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// AGENT_HIERARCHY</h2>
        {agents && agents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {agents.map((a) => (
              <div key={a.id} className="bg-bg-950/60 border border-bg-800 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-200">{a.name}</span>
                  <span className={`px-2 py-0.5 text-[10px] rounded-full ${autonomyColors[a.autonomy_level] || autonomyColors.approval}`}>
                    {a.autonomy_level.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  {a.role} · {a.runtime} · {a.provider}
                </p>
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-[10px] ${a.status === 'working' ? 'text-primary-400' : 'text-gray-600'}`}>
                    ● {a.status}
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono">{a.policies} policies</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-600">Sin agentes registrados.</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policies */}
        <div className="lg:col-span-2 hack-card p-5">
          <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// POLICIES</h2>
          {policies && policies.length > 0 ? (
            <div className="space-y-2">
              {policies.map((p) => (
                <div key={p.id} className="flex items-center justify-between bg-bg-950/60 border border-bg-800 rounded-lg px-3 py-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-[10px] rounded-full ${effectColors[p.effect] || ''}`}>
                        {p.effect.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-200 font-mono">{p.action}</span>
                      <span className="text-xs text-gray-600">→ {p.agent_name || '?'}</span>
                    </div>
                    {p.note && <p className="text-xs text-gray-600 mt-1 truncate">{p.note}</p>}
                  </div>
                  <button
                    onClick={() => { if (confirm('¿Eliminar policy?')) deletePolicy.mutate(p.id) }}
                    className="text-xs px-2 py-1 rounded border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 ml-3"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No policies yet"
              message="Creá reglas allow / approval / deny por agente y acción."
            />
          )}
        </div>

        {/* Nueva policy */}
        <div className="hack-card p-5">
          <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// NEW_POLICY</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Agente</label>
              <select
                value={form.agent_id}
                onChange={e => setForm({ ...form, agent_id: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none"
              >
                <option value="">🌐 global (todos)</option>
                {(agents || []).map(a => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Acción</label>
              <input
                value={form.action}
                onChange={e => setForm({ ...form, action: e.target.value })}
                placeholder="send_email, delete, deploy, modify_crm..."
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Efecto</label>
              <select
                value={form.effect}
                onChange={e => setForm({ ...form, effect: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none"
              >
                <option value="allow">✓ allow</option>
                <option value="approval">⚠ approval (human gate)</option>
                <option value="deny">✕ deny</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Nota</label>
              <input
                value={form.note}
                onChange={e => setForm({ ...form, note: e.target.value })}
                placeholder="opcional"
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none"
              />
            </div>
            <button
              onClick={() => createPolicy.mutate()}
              disabled={!form.action.trim() || createPolicy.isPending}
              className="w-full px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
            >
              + Crear policy
            </button>
            {msg && <p className="text-xs text-gray-400">{msg}</p>}
          </div>
          <p className="text-xs text-gray-600 mt-4">
            🔒 Las policies son la capa de control: las acciones sensibles deben pasar por
            <span className="text-yellow-400"> approval</span> y quedar auditadas.
          </p>
        </div>
      </div>
    </div>
  )
}
