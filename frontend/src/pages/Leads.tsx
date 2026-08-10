import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { leadsApi } from '../services/api'
import { useState } from 'react'

interface Lead {
  id: string
  company: string
  contact_name: string | null
  email: string | null
  phone: string | null
  website: string | null
  source: string
  industry: string | null
  segment: string | null
  status: string
  score: number
  notes: string | null
  created_at: string | null
}

interface LeadStats {
  total: number
  by_status: Record<string, number>
  by_source: Record<string, number>
  avg_score: number
  top_sources: { source: string; count: number }[]
}

interface LeadList {
  items: Lead[]
  total: number
  page: number
  page_size: number
}

const statusColors: Record<string, string> = {
  new: 'bg-blue-500/10 text-blue-400 border border-blue-500/40',
  contacted: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  qualified: 'bg-purple-500/10 text-purple-400 border border-purple-500/40',
  proposal: 'bg-orange-500/10 text-orange-400 border border-orange-500/40',
  won: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  lost: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
}

const sourceLabels: Record<string, string> = {
  manual: 'manual',
  conciencia: '🌐 conciencia',
  referral: 'referral',
  web: 'web',
  linkedin: 'linkedin',
  overpass: '🗺️ OSM',
  other: 'otro',
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-primary-400 border-primary-500/50'
  if (score >= 40) return 'text-yellow-400 border-yellow-500/50'
  return 'text-gray-400 border-gray-500/40'
}

interface HuntSource {
  name: string
  label: string
  description: string
  enabled: boolean
}

interface HuntRun {
  id: string
  source: string
  status: string
  found: number
  added: number
  duplicates: number
  error: string | null
  started_at: string | null
}

interface HuntSummary {
  results: { source: string; found: number; added: number; duplicates: number; status: string; error?: string | null }[]
  total_found: number
  total_added: number
  total_duplicates: number
}

function fmtDateTime(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('es-PY', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function Leads() {
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const { data: stats } = useQuery<LeadStats>({
    queryKey: ['lead-stats'],
    queryFn: () => leadsApi.stats().then(res => res.data),
  })

  const { data: leadsData, isLoading } = useQuery<LeadList>({
    queryKey: ['leads', search, filterStatus, filterSource],
    queryFn: () =>
      leadsApi.getAll({
        search: search || undefined,
        status: filterStatus || undefined,
        source: filterSource || undefined,
        page_size: 100,
      }).then(res => res.data),
  })

  const createLead = useMutation({
    mutationFn: (data: any) => leadsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
      setShowModal(false)
    },
  })

  const { data: huntSources } = useQuery<HuntSource[]>({
    queryKey: ['hunt-sources'],
    queryFn: () => leadsApi.huntSources().then(res => res.data),
  })

  const { data: huntRuns } = useQuery<HuntRun[]>({
    queryKey: ['hunt-runs'],
    queryFn: () => leadsApi.huntRuns().then(res => res.data),
  })

  const [huntResult, setHuntResult] = useState<HuntSummary | null>(null)

  const huntRun = useMutation({
    mutationFn: () => leadsApi.huntRun(),
    onSuccess: (res) => {
      setHuntResult(res.data)
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
      queryClient.invalidateQueries({ queryKey: ['hunt-runs'] })
    },
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      leadsApi.update(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
    },
  })

  const enrichLead = useMutation({
    mutationFn: (id: string) => leadsApi.enrich(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const enrichWebsite = useMutation({
    mutationFn: (id: string) => leadsApi.enrichWebsite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const leads = leadsData?.items || []
  const total = leadsData?.total || 0

  return (
    <div>
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// LEAD HUNTER</h1>
          <p className="text-sm text-gray-500 mt-1">Buscador y pipeline de clientes potenciales</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all shadow-neon"
        >
          + Nuevo lead
        </button>
      </div>

      {/* Hunt panel */}
      <div className="bg-bg-900 border border-bg-700 rounded-lg p-4 mb-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div>
            <h2 className="text-sm font-bold text-primary-400 tracking-wider">// PROSPECCIÓN AUTOMÁTICA</h2>
            <p className="text-xs text-gray-500 mt-1">
              {huntSources?.map(s => s.label).join(' · ') || 'Cargando fuentes...'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {huntRuns && huntRuns.length > 0 && (
              <span className="text-xs text-gray-500">
                último: {fmtDateTime(huntRuns[0].started_at)} · {huntRuns[0].found} encontrados / {huntRuns[0].added} nuevos
              </span>
            )}
            <button
              onClick={() => huntRun.mutate()}
              disabled={huntRun.isPending}
              className="px-4 py-2 bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all shadow-neon disabled:opacity-40 disabled:cursor-wait"
            >
              {huntRun.isPending ? '⌛ Cazando...' : '🔎 Cazar leads ahora'}
            </button>
          </div>
        </div>
        {huntResult && (
          <div className="mt-3 pt-3 border-t border-bg-700 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div><span className="text-gray-500">Encontrados: </span><span className="text-primary-400 font-mono">{huntResult.total_found}</span></div>
            <div><span className="text-gray-500">Nuevos: </span><span className="text-primary-400 font-mono">{huntResult.total_added}</span></div>
            <div><span className="text-gray-500">Duplicados: </span><span className="text-yellow-400 font-mono">{huntResult.total_duplicates}</span></div>
            <div><span className="text-gray-500">Errores: </span><span className="text-alert-400 font-mono">{huntResult.results.filter(r => r.status === 'error').length}</span></div>
          </div>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Total leads</p>
            <p className="text-2xl font-bold text-primary-400 mt-1">{stats.total}</p>
          </div>
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Qualified+</p>
            <p className="text-2xl font-bold text-yellow-400 mt-1">
              {(stats.by_status?.qualified || 0) + (stats.by_status?.proposal || 0) + (stats.by_status?.won || 0)}
            </p>
          </div>
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Score promedio</p>
            <p className="text-2xl font-bold text-primary-400 mt-1">{stats.avg_score}</p>
          </div>
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Top fuente</p>
            <p className="text-sm font-bold text-gray-200 mt-2 truncate">
              {stats.top_sources?.[0]?.source || '—'} ({stats.top_sources?.[0]?.count || 0})
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar empresa, contacto, email..."
          className="flex-1 px-4 py-2 bg-bg-900 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
        />
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="px-4 py-2 bg-bg-900 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
        >
          <option value="">Status: todos</option>
          <option value="new">new</option>
          <option value="contacted">contacted</option>
          <option value="qualified">qualified</option>
          <option value="proposal">proposal</option>
          <option value="won">won</option>
          <option value="lost">lost</option>
        </select>
        <select
          value={filterSource}
          onChange={e => setFilterSource(e.target.value)}
          className="px-4 py-2 bg-bg-900 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
        >
          <option value="">Fuente: todas</option>
          <option value="manual">manual</option>
          <option value="conciencia">conciencia</option>
          <option value="referral">referral</option>
          <option value="web">web</option>
          <option value="linkedin">linkedin</option>
          <option value="overpass">OSM (overpass)</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-primary-400 animate-blink">Loading leads...</div>
      ) : (
        <div className="bg-bg-900 border border-bg-700 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bg-700 text-left text-xs uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3">Empresa</th>
                  <th className="px-4 py-3">Contacto</th>
                  <th className="px-4 py-3">Fuente</th>
                  <th className="px-4 py-3">Sector</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Creado</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                      Sin leads todavía — apretá «Cazar leads ahora» o agregá uno manual
                    </td>
                  </tr>
                )}
                {leads.map(lead => (
                  <tr key={lead.id} className="border-b border-bg-800 hover:bg-bg-800/50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-200">{lead.company}</p>
                      {lead.website && (
                        <a href={lead.website} target="_blank" rel="noreferrer" className="text-xs text-primary-500 hover:underline">
                          {lead.website.replace(/^https?:\/\//, '')}
                        </a>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {lead.contact_name && <p className="text-gray-300">{lead.contact_name}</p>}
                      {lead.email && <p className="text-xs text-gray-500">{lead.email}</p>}
                      {lead.phone && <p className="text-xs text-gray-500">{lead.phone}</p>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-400">{sourceLabels[lead.source] || lead.source}</span>
                      {lead.industry && <p className="text-xs text-gray-600 mt-1">{lead.industry}</p>}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">{lead.segment || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded border ${scoreColor(lead.score)} text-xs font-mono`}>
                        {lead.score}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={lead.status}
                        onChange={e => updateStatus.mutate({ id: lead.id, status: e.target.value })}
                        className={`text-xs px-2 py-1 rounded bg-transparent cursor-pointer ${statusColors[lead.status] || statusColors.new}`}
                      >
                        <option value="new">new</option>
                        <option value="contacted">contacted</option>
                        <option value="qualified">qualified</option>
                        <option value="proposal">proposal</option>
                        <option value="won">won</option>
                        <option value="lost">lost</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{fmtDateTime(lead.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button
                          onClick={() => enrichWebsite.mutate(lead.id)}
                          disabled={enrichWebsite.isPending || !lead.website}
                          title="Rastrear website (email/tel)"
                          className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 hover:text-primary-300 transition-colors disabled:opacity-30"
                        >
                          🌐
                        </button>
                        <button
                          onClick={() => enrichLead.mutate(lead.id)}
                          disabled={enrichLead.isPending}
                          title="Enriquecer con IA (DeepSeek)"
                          className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 hover:text-primary-300 transition-colors disabled:opacity-40"
                        >
                          ✦ IA
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 text-xs text-gray-600 border-t border-bg-700">
            {total} leads · pipeline {leads.length > 0 ? leads.filter(l => l.status === 'new').length : 0} nuevos
          </div>
        </div>
      )}

      {/* Modal nuevo lead */}
      {showModal && <LeadModal onClose={() => setShowModal(false)} onCreate={createLead.mutate} />}
    </div>
  )
}

function LeadModal({ onClose, onCreate }: { onClose: () => void; onCreate: (data: any) => void }) {
  const [form, setForm] = useState({
    company: '',
    contact_name: '',
    email: '',
    phone: '',
    website: '',
    source: 'manual',
    industry: '',
    segment: '',
    notes: '',
  })

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-bg-900 border border-bg-700 rounded-lg w-full max-w-lg shadow-neon"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-bg-700">
          <h2 className="font-bold text-primary-400 tracking-wider">+ NUEVO LEAD</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>
        <div className="p-5 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Empresa *</label>
              <input
                value={form.company}
                onChange={e => set('company', e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
                placeholder="Cooperativa XYZ S.A."
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Contacto</label>
              <input value={form.contact_name} onChange={e => set('contact_name', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="Nombre" />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Email</label>
              <input value={form.email} onChange={e => set('email', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="contacto@empresa.com" />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Teléfono</label>
              <input value={form.phone} onChange={e => set('phone', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="+595..." />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Website</label>
              <input value={form.website} onChange={e => set('website', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="https://..." />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Fuente</label>
              <select value={form.source} onChange={e => set('source', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                <option value="manual">manual</option>
                <option value="conciencia">conciencia</option>
                <option value="referral">referral</option>
                <option value="web">web</option>
                <option value="linkedin">linkedin</option>
                <option value="other">otro</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Sector</label>
              <input value={form.industry} onChange={e => set('industry', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="cooperativa, salud, distribuidora..." />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Segmento</label>
              <select value={form.segment} onChange={e => set('segment', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                <option value="">—</option>
                <option value="pyme">pyme</option>
                <option value="mediana">mediana</option>
                <option value="corporativo">corporativo</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Notas</label>
              <textarea
                value={form.notes}
                onChange={e => set('notes', e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50 h-20"
                placeholder="Contexto, necesidades detectadas..."
              />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 px-5 py-4 border-t border-bg-700">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">
            Cancelar
          </button>
          <button
            onClick={() => form.company && onCreate(form)}
            disabled={!form.company}
            className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
          >
            Crear lead
          </button>
        </div>
      </div>
    </div>
  )
}
