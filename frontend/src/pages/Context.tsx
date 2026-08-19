import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contextPacksApi, decisionsApi } from '../services/api'
import { useState } from 'react'
import { LoadingState, ErrorState, EmptyState } from '../components/StateViews'

interface ContextPack {
  id: string
  title: string
  project_id?: string | null
  source: string
  target?: string | null
  content: any
  created_at: string
}

interface Decision {
  id: string
  number: number
  ref: string
  title: string
  decision: string
  reason?: string
  rejected?: string[]
  impact?: string[]
  status: string
  created_at: string
}

export default function Context() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'packs' | 'decisions'>('packs')
  const [viewing, setViewing] = useState<ContextPack | null>(null)
  const [exported, setExported] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  const [decForm, setDecForm] = useState({ title: '', decision: '', reason: '', rejected: '', impact: '' })

  const { data: packs, isLoading, isError, refetch } = useQuery<ContextPack[]>({
    queryKey: ['context-packs'],
    queryFn: () => contextPacksApi.getAll().then(res => res.data),
  })

  const { data: decisions } = useQuery<Decision[]>({
    queryKey: ['decisions'],
    queryFn: () => decisionsApi.getAll().then(res => res.data),
  })

  const generate = useMutation({
    mutationFn: () => contextPacksApi.generate({ title: `Context Pack ${new Date().toLocaleString()}` }),
    onSuccess: () => {
      setMsg('Context Pack generado desde datos reales')
      queryClient.invalidateQueries({ queryKey: ['context-packs'] })
      setTimeout(() => setMsg(''), 4000)
    },
  })

  const deletePack = useMutation({
    mutationFn: (id: string) => contextPacksApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['context-packs'] }),
  })

  const createDecision = useMutation({
    mutationFn: () => decisionsApi.create({
      title: decForm.title.trim(),
      decision: decForm.decision.trim(),
      reason: decForm.reason.trim() || undefined,
      rejected: decForm.rejected.split(',').map(s => s.trim()).filter(Boolean),
      impact: decForm.impact.split(',').map(s => s.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      setDecForm({ title: '', decision: '', reason: '', rejected: '', impact: '' })
      setMsg('Decisión registrada')
      queryClient.invalidateQueries({ queryKey: ['decisions'] })
      setTimeout(() => setMsg(''), 4000)
    },
    onError: (e: any) => { setMsg(e.response?.data?.detail || 'Error'); setTimeout(() => setMsg(''), 5000) },
  })

  const deleteDecision = useMutation({
    mutationFn: (id: string) => decisionsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['decisions'] }),
  })

  const doExport = async (pack: ContextPack, format: string) => {
    try {
      const r = await contextPacksApi.export(pack.id, format)
      setExported(format === 'json' ? JSON.stringify(r.data, null, 2) : r.data.content)
    } catch (e: any) {
      setExported(`Error: ${e.message}`)
    }
  }

  if (isLoading) return <LoadingState label="Loading context fabric..." />
  if (isError) return <ErrorState message="No se pudo cargar el Context Fabric." onRetry={() => refetch()} />

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// CONTEXT & MEMORY</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ knowledge ≠ memory ≠ context · context packs · transfer</p>
        </div>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
        >
          {generate.isPending ? 'Generando...' : '⚡ Generar Context Pack'}
        </button>
      </div>

      {msg && <p className="text-xs text-primary-400 mb-4">{msg}</p>}

      {/* Modelo conceptual (spec §24) */}
      <div className="bg-bg-900/60 border border-bg-700 rounded-lg p-4 mb-6 text-xs text-gray-500">
        <p>
          <span className="text-primary-400">KNOWLEDGE</span> (información externa: docs, repos, web) +{' '}
          <span className="text-primary-400">MEMORY</span> (lo aprendido: decisiones, estado, historial) +{' '}
          <span className="text-primary-400">CURRENT STATE</span> → <span className="text-yellow-400">CONTEXT</span> → ejecución del agente.
          El prompt <span className="text-gray-400">no es la memoria</span>: el contexto canónico vive acá.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <TabBtn active={tab === 'packs'} onClick={() => { setTab('packs'); setViewing(null); setExported(null) }} label="CONTEXT PACKS" />
        <TabBtn active={tab === 'decisions'} onClick={() => { setTab('decisions'); setViewing(null); setExported(null) }} label="DECISION MEMORY" />
      </div>

      {tab === 'packs' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 hack-card p-5">
            <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// PACKS</h2>
            {packs && packs.length > 0 ? (
              <div className="space-y-2">
                {packs.map((p) => (
                  <div key={p.id} className="flex items-center justify-between bg-bg-950/60 border border-bg-800 rounded-lg px-3 py-2">
                    <button onClick={() => setViewing(viewing?.id === p.id ? null : p)} className="text-left min-w-0">
                      <span className="text-sm text-gray-200 font-medium">{p.title}</span>
                      <span className="text-xs text-gray-600 block mt-0.5">
                        {p.content?.decisions?.length || 0} decisiones · {p.content?.architecture?.length || 0} arch · {p.content?.tasks?.length || 0} tasks · {new Date(p.created_at).toLocaleString()}
                      </span>
                    </button>
                    <div className="flex gap-2 shrink-0">
                      <button onClick={() => doExport(p, 'markdown')} className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50">Export</button>
                      <button onClick={() => { if (confirm('¿Eliminar pack?')) deletePack.mutate(p.id) }} className="text-xs px-2 py-1 rounded border border-alert-500/40 text-alert-400 hover:bg-alert-500/10">✕</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Sin context packs"
                message="Generá uno: junta project, architecture, decisions, tasks y memory en una estructura canónica."
                actionLabel="generar pack"
                onAction={() => generate.mutate()}
              />
            )}
          </div>

          <div className="space-y-6">
            {/* Vista de pack */}
            {viewing && (
              <div className="hack-card p-5">
                <h3 className="text-sm font-bold text-primary-400 mb-3">// {viewing.title}</h3>
                <div className="text-xs space-y-2 text-gray-400">
                  <p><span className="text-gray-600">PROJECT:</span> {viewing.content?.project}</p>
                  <p><span className="text-gray-600">MISSION:</span> {viewing.content?.mission || '—'}</p>
                  <p><span className="text-gray-600">DECISIONS:</span> {(viewing.content?.decisions || []).join(', ') || '—'}</p>
                  <p><span className="text-gray-600">CONSTRAINTS:</span></p>
                  <ul className="list-disc pl-5">
                    {(viewing.content?.constraints || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
                <div className="mt-3 flex gap-2">
                  <button onClick={() => doExport(viewing, 'markdown')} className="flex-1 text-xs px-3 py-2 rounded-lg border border-primary-500/40 text-primary-400 hover:bg-primary-500/10">⬇ Markdown</button>
                  <button onClick={() => doExport(viewing, 'json')} className="flex-1 text-xs px-3 py-2 rounded-lg border border-bg-600 text-gray-400 hover:text-primary-300">⬇ JSON</button>
                </div>
              </div>
            )}

            {/* Export result */}
            {exported && (
              <div className="hack-card p-5">
                <h3 className="text-sm font-bold text-primary-400 mb-3">// EXPORT</h3>
                <pre className="text-[10px] text-gray-400 font-mono bg-bg-950 border border-bg-800 rounded p-3 max-h-72 overflow-auto whitespace-pre-wrap">{exported}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'decisions' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 hack-card p-5">
            <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// DECISIONS</h2>
            {decisions && decisions.length > 0 ? (
              <div className="space-y-3">
                {decisions.map((d) => (
                  <div key={d.id} className="bg-bg-950/60 border border-bg-800 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs text-primary-500 font-mono">{d.ref} · {new Date(d.created_at).toLocaleDateString()} · {d.status}</p>
                        <h3 className="text-sm font-medium text-gray-200 mt-1">{d.title}</h3>
                        <p className="text-xs text-gray-400 mt-1">{d.decision}</p>
                        {d.reason && <p className="text-xs text-gray-600 mt-2"><span className="text-gray-500">Razón:</span> {d.reason}</p>}
                        {d.rejected && d.rejected.length > 0 && (
                          <p className="text-xs text-gray-600 mt-1"><span className="text-gray-500">Descartado:</span> {d.rejected.join(', ')}</p>
                        )}
                        {d.impact && d.impact.length > 0 && (
                          <p className="text-xs text-gray-600 mt-1"><span className="text-gray-500">Impacto:</span> {d.impact.join(', ')}</p>
                        )}
                      </div>
                      <button onClick={() => { if (confirm('¿Eliminar decisión?')) deleteDecision.mutate(d.id) }} className="text-xs px-2 py-1 rounded border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 shrink-0">✕</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="Sin decisiones" message="Las decisiones de arquitectura/producto se registran acá como objetos de primera clase (DEC-NNN)." />
            )}
          </div>

          <div className="hack-card p-5">
            <h2 className="text-sm font-semibold text-primary-400 tracking-wider mb-4">// NEW_DECISION</h2>
            <div className="space-y-3">
              <input value={decForm.title} onChange={e => setDecForm({ ...decForm, title: e.target.value })} placeholder="Título (ej. Mission vs Project)" className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none" />
              <textarea value={decForm.decision} onChange={e => setDecForm({ ...decForm, decision: e.target.value })} rows={3} placeholder="Decisión..." className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none" />
              <input value={decForm.reason} onChange={e => setDecForm({ ...decForm, reason: e.target.value })} placeholder="Razón" className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none" />
              <input value={decForm.rejected} onChange={e => setDecForm({ ...decForm, rejected: e.target.value })} placeholder="Descartadas (coma separada)" className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none" />
              <input value={decForm.impact} onChange={e => setDecForm({ ...decForm, impact: e.target.value })} placeholder="Impacto (UX, API, ...)" className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none" />
              <button
                onClick={() => createDecision.mutate()}
                disabled={!decForm.title.trim() || !decForm.decision.trim() || createDecision.isPending}
                className="w-full px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
              >
                + Registrar decisión
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-4">
              💡 Las decisiones quedan linkeables a missions, tasks, agents, files y context packs.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

function TabBtn({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-xs font-semibold tracking-wider rounded-lg border transition-all ${active ? 'bg-primary-500/10 text-primary-400 border-primary-500/40' : 'border-bg-700 text-gray-500 hover:text-gray-300'}`}
    >
      {label}
    </button>
  )
}
