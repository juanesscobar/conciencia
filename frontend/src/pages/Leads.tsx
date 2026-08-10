import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { leadsApi } from '../services/api'
import { useRef, useState } from 'react'

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
  region: string | null
  status: string
  score: number
  notes: string | null
  metadata: any
  online_presence?: { website: boolean; email: boolean; phone: boolean; social: boolean }
  created_at: string | null
}

interface LeadEvent {
  id: string
  event_type: string
  description: string | null
  created_at: string | null
}

interface LeadProposal {
  id: string
  lead_id: string
  title: string | null
  content: string
  status: string
  model: string | null
  created_at: string | null
  sent_at: string | null
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
  import: '📥 import',
  other: 'otro',
}

const eventLabels: Record<string, string> = {
  created: '🆕 Creado',
  contacted: '📞 Contactado',
  qualified: '✔️ Calificado',
  proposal_generated: '📄 Propuesta generada',
  proposal_sent: '✉️ Propuesta enviada',
  won: '🏆 Ganado',
  lost: '❌ Perdido',
  note: '📝 Nota',
  enriched: '🛰️ Enriquecido',
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-primary-400 border-primary-500/50'
  if (score >= 40) return 'text-yellow-400 border-yellow-500/50'
  return 'text-gray-400 border-gray-500/40'
}

function fmtDateTime(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('es-PY', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function Leads() {
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [filterRegion, setFilterRegion] = useState('')
  const [filterSegment, setFilterSegment] = useState('')
  const [filterIndustry, setFilterIndustry] = useState('')
  const [filterOnline, setFilterOnline] = useState('')
  const [filterAge, setFilterAge] = useState('')
  const [filterMinScore, setFilterMinScore] = useState('')
  const [sort, setSort] = useState('newest')
  const [showFilters, setShowFilters] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [huntResult, setHuntResult] = useState<HuntSummary | null>(null)
  const [importMsg, setImportMsg] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: stats } = useQuery<LeadStats>({
    queryKey: ['lead-stats'],
    queryFn: () => leadsApi.stats().then(res => res.data),
  })

  const { data: regions } = useQuery<string[]>({
    queryKey: ['lead-regions'],
    queryFn: () => leadsApi.regions().then(res => res.data),
  })

  const { data: leadsData, isLoading } = useQuery<LeadList>({
    queryKey: ['leads', search, filterStatus, filterSource, filterRegion, filterSegment, filterIndustry, filterOnline, filterAge, filterMinScore, sort],
    queryFn: () =>
      leadsApi.getAll({
        search: search || undefined,
        status: filterStatus || undefined,
        source: filterSource || undefined,
        region: filterRegion || undefined,
        segment: filterSegment || undefined,
        industry: filterIndustry || undefined,
        online: filterOnline || undefined,
        age_days: filterAge || undefined,
        min_score: filterMinScore || undefined,
        sort,
        page_size: 100,
      }).then(res => res.data),
  })

  const { data: huntSources } = useQuery({
    queryKey: ['hunt-sources'],
    queryFn: () => leadsApi.huntSources().then(res => res.data),
  })

  const { data: huntRuns } = useQuery<HuntRun[]>({
    queryKey: ['hunt-runs'],
    queryFn: () => leadsApi.huntRuns().then(res => res.data),
  })

  const createLead = useMutation({
    mutationFn: (data: any) => leadsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
      setShowModal(false)
    },
  })

  const huntRun = useMutation({
    mutationFn: () => leadsApi.huntRun(),
    onSuccess: (res) => {
      setHuntResult(res.data)
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
      queryClient.invalidateQueries({ queryKey: ['hunt-runs'] })
    },
  })

  const enrichWebsite = useMutation({
    mutationFn: (id: string) => leadsApi.enrichWebsite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      if (selectedLead) loadLead(selectedLead.id)
    },
  })

  const enrichAi = useMutation({
    mutationFn: (id: string) => leadsApi.enrich(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const importCsv = useMutation({
    mutationFn: (file: File) => leadsApi.importCsv(file),
    onSuccess: (res: any) => {
      const r = res.data
      setImportMsg(`CSV importado: ${r.total} filas → ${r.added} nuevos, ${r.duplicates} duplicados, ${r.errors} errores`)
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
      setTimeout(() => setImportMsg(''), 6000)
    },
    onError: (e: any) => {
      setImportMsg(`Error importando CSV: ${e.response?.data?.detail || e.message}`)
      setTimeout(() => setImportMsg(''), 6000)
    },
  })

  const loadLead = (id: string) => {
    queryClient.invalidateQueries({ queryKey: ['lead-detail', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-events', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-proposals', id] })
  }

  const refreshAfterAction = (id: string) => {
    queryClient.invalidateQueries({ queryKey: ['leads'] })
    queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
    queryClient.invalidateQueries({ queryKey: ['lead-detail', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-events', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-proposals', id] })
  }

  const leads = leadsData?.items || []
  const total = leadsData?.total || 0

  const activeFilters = [filterRegion, filterSegment, filterIndustry, filterOnline, filterAge, filterMinScore].filter(Boolean).length

  return (
    <div>
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// LEAD HUNTER</h1>
          <p className="text-sm text-gray-500 mt-1">Caza, filtra y ejecuta el pipeline completo hasta la propuesta</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) importCsv.mutate(f); e.target.value = '' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-2 text-sm rounded-lg border border-bg-600 text-gray-300 hover:border-primary-500/50 hover:text-primary-300 transition-colors"
          >
            📥 Import CSV
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all shadow-neon"
          >
            + Nuevo lead
          </button>
        </div>
      </div>

      {/* Hunt panel */}
      <div className="bg-bg-900 border border-bg-700 rounded-lg p-4 mb-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <div>
            <h2 className="text-sm font-bold text-primary-400 tracking-wider">// PROSPECCIÓN AUTOMÁTICA</h2>
            <p className="text-xs text-gray-500 mt-1">
              {huntSources?.map((s: any) => s.label).join(' · ') || 'Cargando fuentes...'}
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
        {importMsg && <p className="mt-3 pt-3 border-t border-bg-700 text-xs text-primary-400">{importMsg}</p>}
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

      {/* Filtros */}
      <div className="bg-bg-900 border border-bg-700 rounded-lg p-4 mb-4">
        <div className="flex flex-col md:flex-row gap-3">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar empresa, contacto, email..."
            className="flex-1 px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
          />
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
            <option value="">Status: todos</option>
            <option value="new">new</option>
            <option value="contacted">contacted</option>
            <option value="qualified">qualified</option>
            <option value="proposal">proposal</option>
            <option value="won">won</option>
            <option value="lost">lost</option>
          </select>
          <select value={filterSource} onChange={e => setFilterSource(e.target.value)} className="px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
            <option value="">Fuente: todas</option>
            <option value="manual">manual</option>
            <option value="conciencia">conciencia</option>
            <option value="referral">referral</option>
            <option value="web">web</option>
            <option value="linkedin">linkedin</option>
            <option value="overpass">OSM (overpass)</option>
            <option value="import">import</option>
          </select>
          <select value={sort} onChange={e => setSort(e.target.value)} className="px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
            <option value="newest">Orden: más nuevos</option>
            <option value="oldest">Orden: más viejos</option>
            <option value="score">Orden: mejor score</option>
            <option value="company">Orden: empresa A-Z</option>
          </select>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 text-sm rounded-lg border transition-colors ${showFilters || activeFilters ? 'text-primary-400 border-primary-500/40 bg-primary-500/10' : 'text-gray-400 border-bg-600 hover:text-primary-300'}`}
          >
            ⚙ Filtros {activeFilters > 0 && `(${activeFilters})`}
          </button>
        </div>

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-bg-700 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Región</label>
              <input
                list="region-list"
                value={filterRegion}
                onChange={e => setFilterRegion(e.target.value)}
                placeholder="Asunción, Luque, Lambaré..."
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
              />
              <datalist id="region-list">
                {regions?.map(r => <option key={r} value={r} />)}
              </datalist>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Tamaño (segmento)</label>
              <select value={filterSegment} onChange={e => setFilterSegment(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                <option value="">Todos</option>
                <option value="pyme">Pyme</option>
                <option value="mediana">Mediana</option>
                <option value="corporativo">Corporativo</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Presencia online</label>
              <select value={filterOnline} onChange={e => setFilterOnline(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                <option value="">Cualquiera</option>
                <option value="any">Con algún canal digital</option>
                <option value="website">Con website</option>
                <option value="email">Con email</option>
                <option value="phone">Con teléfono</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Antigüedad</label>
              <select value={filterAge} onChange={e => setFilterAge(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                <option value="">Todas</option>
                <option value="1">Últimas 24hs</option>
                <option value="7">Última semana</option>
                <option value="30">Último mes</option>
                <option value="90">Últimos 3 meses</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Sector</label>
              <input
                value={filterIndustry}
                onChange={e => setFilterIndustry(e.target.value)}
                placeholder="salud, cooperativa, farmacia..."
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Score mínimo</label>
              <input
                type="number"
                min={0}
                max={100}
                value={filterMinScore}
                onChange={e => setFilterMinScore(e.target.value)}
                placeholder="ej: 40"
                className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
              />
            </div>
            <div className="col-span-2 flex items-end">
              <button
                onClick={() => { setFilterRegion(''); setFilterSegment(''); setFilterIndustry(''); setFilterOnline(''); setFilterAge(''); setFilterMinScore(''); setFilterStatus(''); setFilterSource(''); setSearch('') }}
                className="px-4 py-2 text-sm rounded-lg border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors"
              >
                ⟲ Limpiar filtros
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Tabla */}
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
                  <th className="px-4 py-3">Región</th>
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
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                      Sin leads con esos filtros — apretá «Cazar leads ahora» o importá un CSV
                    </td>
                  </tr>
                )}
                {leads.map(lead => (
                  <tr
                    key={lead.id}
                    className="border-b border-bg-800 hover:bg-bg-800/50 transition-colors cursor-pointer"
                    onClick={() => setSelectedLead(lead)}
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-200">{lead.company}</p>
                      {lead.website && (
                        <a href={lead.website} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()} className="text-xs text-primary-500 hover:underline">
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
                      {lead.region ? (
                        <span className="text-xs text-gray-300">📍 {lead.region}</span>
                      ) : (
                        <span className="text-xs text-gray-600">—</span>
                      )}
                      <div className="flex gap-1 mt-1">
                        {lead.online_presence?.website && <span title="website" className="text-[10px] text-primary-400">🌐</span>}
                        {lead.online_presence?.email && <span title="email" className="text-[10px] text-primary-400">✉</span>}
                        {lead.online_presence?.phone && <span title="teléfono" className="text-[10px] text-primary-400">📞</span>}
                      </div>
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
                        onClick={e => e.stopPropagation()}
                        onChange={e => leadsApi.action(lead.id, e.target.value === 'won' ? 'won' : e.target.value === 'lost' ? 'lost' : e.target.value, e.target.value === 'contacted' ? { reason: 'Contactado desde tabla' } : {}).then(() => refreshAfterAction(lead.id))}
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
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex gap-1">
                        <button
                          onClick={() => { setSelectedLead(lead); setTimeout(() => enrichWebsite.mutate(lead.id), 50) }}
                          disabled={enrichWebsite.isPending || !lead.website}
                          title="Rastrear website (email/tel)"
                          className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 hover:text-primary-300 transition-colors disabled:opacity-30"
                        >
                          🌐
                        </button>
                        <button
                          onClick={() => enrichAi.mutate(lead.id)}
                          disabled={enrichAi.isPending}
                          title="Enriquecer con IA"
                          className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 hover:text-primary-300 transition-colors disabled:opacity-40"
                        >
                          ✦
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 text-xs text-gray-600 border-t border-bg-700">
            {total} leads · {leads.filter(l => l.status === 'new').length} nuevos en esta vista
          </div>
        </div>
      )}

      {showModal && <LeadModal onClose={() => setShowModal(false)} onCreate={createLead.mutate} />}
      {selectedLead && (
        <LeadDetail
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onAction={refreshAfterAction}
          onEnrichWebsite={(id) => enrichWebsite.mutate(id)}
          onEnrichAi={(id) => enrichAi.mutate(id)}
        />
      )}
    </div>
  )
}

/* ================= Modal de detalle con pipeline ================= */

function LeadDetail({ lead, onClose, onAction, onEnrichWebsite, onEnrichAi }: {
  lead: Lead
  onClose: () => void
  onAction: (id: string) => void
  onEnrichWebsite: (id: string) => void
  onEnrichAi: (id: string) => void
}) {
  const [noteText, setNoteText] = useState('')
  const [reasonText, setReasonText] = useState('')
  const [showProposalForm, setShowProposalForm] = useState(false)
  const [propTitle, setPropTitle] = useState('')
  const [propContent, setPropContent] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const { data: events } = useQuery<LeadEvent[]>({
    queryKey: ['lead-events', lead.id],
    queryFn: () => leadsApi.events(lead.id).then(res => res.data),
  })

  const { data: proposals } = useQuery<LeadProposal[]>({
    queryKey: ['lead-proposals', lead.id],
    queryFn: () => leadsApi.proposals(lead.id).then(res => res.data),
  })

  const { data: detail } = useQuery<Lead>({
    queryKey: ['lead-detail', lead.id],
    queryFn: () => leadsApi.getById(lead.id).then(res => res.data),
  })

  const current = detail || lead

  const doAction = async (action: string, body?: any) => {
    setBusy(true)
    try {
      await leadsApi.action(current.id, action, body)
      onAction(current.id)
      if (action === 'lost' || action === 'won') {
        setMsg(action === 'won' ? '🏆 Cliente ganado' : 'Lead cerrado como perdido')
        setTimeout(() => setMsg(''), 4000)
      }
    } catch (e: any) {
      setMsg(`Error: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const addNote = async () => {
    if (!noteText.trim()) return
    await doAction('note', { note: noteText.trim() })
    setNoteText('')
  }

  const generateProposal = async () => {
    setBusy(true)
    try {
      await leadsApi.proposalGenerate(current.id)
      onAction(current.id)
      setMsg('📄 Propuesta generada con IA')
      setTimeout(() => setMsg(''), 4000)
    } catch (e: any) {
      setMsg(`Error: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const createProposal = async () => {
    if (!propContent.trim()) return
    setBusy(true)
    try {
      await leadsApi.proposalCreate(current.id, { title: propTitle.trim() || undefined, content: propContent })
      setShowProposalForm(false)
      setPropTitle(''); setPropContent('')
      onAction(current.id)
    } catch (e: any) {
      setMsg(`Error: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const sendProposal = async (pid: string) => {
    setBusy(true)
    try {
      await leadsApi.proposalSend(pid)
      onAction(current.id)
      setMsg('✉️ Propuesta marcada como enviada')
      setTimeout(() => setMsg(''), 4000)
    } catch (e: any) {
      setMsg(`Error: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const deleteLead = async () => {
    if (!confirm(`¿Eliminar definitivamente el lead "${current.company}"?`)) return
    setBusy(true)
    try {
      await leadsApi.delete(current.id)
      onAction(current.id)
      onClose()
    } catch (e: any) {
      setMsg(`Error: ${e.response?.data?.detail || e.message}`)
      setBusy(false)
    }
  }

  const op = current.online_presence

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-bg-900 border border-bg-700 rounded-lg w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-neon"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-bg-700 sticky top-0 bg-bg-900 z-10">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="font-bold text-primary-400 tracking-wider">{current.company}</h2>
              <span className={`text-xs px-2 py-0.5 rounded ${statusColors[current.status] || statusColors.new}`}>{current.status}</span>
              <span className={`text-xs px-2 py-0.5 rounded border font-mono ${scoreColor(current.score)}`}>{current.score}</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {[current.industry, current.segment, current.region && `📍 ${current.region}`, sourceLabels[current.source] || current.source].filter(Boolean).join(' · ')}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        <div className="p-5 grid grid-cols-1 md:grid-cols-5 gap-5">
          {/* Columna izq: datos + acciones */}
          <div className="md:col-span-2 space-y-4">
            <div className="bg-bg-950 border border-bg-700 rounded-lg p-4 text-sm space-y-2">
              <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">CONTACTO</h3>
              {current.contact_name && <p><span className="text-gray-500">Nombre:</span> <span className="text-gray-200">{current.contact_name}</span></p>}
              {current.email && <p><span className="text-gray-500">Email:</span> <a className="text-primary-400 hover:underline" href={`mailto:${current.email}`}>{current.email}</a></p>}
              {current.phone && <p><span className="text-gray-500">Tel:</span> <span className="text-gray-200">{current.phone}</span></p>}
              {current.website && <p><span className="text-gray-500">Web:</span> <a className="text-primary-400 hover:underline break-all" href={current.website} target="_blank" rel="noreferrer">{current.website}</a></p>}
              {current.notes && <p className="pt-2 border-t border-bg-700"><span className="text-gray-500">Notas:</span> <span className="text-gray-300">{current.notes}</span></p>}
              <div className="pt-2 border-t border-bg-700">
                <span className="text-gray-500 text-xs">Presencia online: </span>
                <span className="text-xs text-gray-300">
                  {op?.website ? '🌐 web' : ''} {op?.email ? '✉ email' : ''} {op?.phone ? '📞 tel' : ''}
                  {!(op?.website || op?.email || op?.phone) && <span className="text-gray-600">sin canales digitales</span>}
                </span>
              </div>
            </div>

            <div className="bg-bg-950 border border-bg-700 rounded-lg p-4">
              <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-3">ACCIONES</h3>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => doAction('contact', { reason: 'Primer contacto' })} disabled={busy} className="px-3 py-2 text-xs rounded-lg border border-yellow-500/40 text-yellow-400 hover:bg-yellow-500/10 transition-colors disabled:opacity-40">📞 Contactar</button>
                <button onClick={() => doAction('qualify')} disabled={busy} className="px-3 py-2 text-xs rounded-lg border border-purple-500/40 text-purple-400 hover:bg-purple-500/10 transition-colors disabled:opacity-40">✔️ Calificar</button>
                <button onClick={generateProposal} disabled={busy} className="px-3 py-2 text-xs rounded-lg border border-orange-500/40 text-orange-400 hover:bg-orange-500/10 transition-colors disabled:opacity-40">🤖 Generar propuesta</button>
                <button onClick={() => doAction('won')} disabled={busy} className="px-3 py-2 text-xs rounded-lg border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">🏆 Ganar</button>
                <button onClick={() => doAction('lost', { reason: reasonText || 'No cerrado' })} disabled={busy} className="px-3 py-2 text-xs rounded-lg border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 transition-colors disabled:opacity-40">❌ Perder</button>
                <button onClick={deleteLead} disabled={busy} className="px-3 py-2 text-xs rounded-lg border border-bg-600 text-gray-500 hover:text-alert-400 hover:border-alert-500/40 transition-colors disabled:opacity-40">🗑 Eliminar</button>
              </div>
              <div className="mt-3 flex gap-2">
                <button onClick={() => onEnrichWebsite(current.id)} disabled={!current.website} className="flex-1 px-3 py-2 text-xs rounded-lg border border-bg-600 text-primary-400 hover:border-primary-500/50 transition-colors disabled:opacity-30">🌐 Rastrear web</button>
                <button onClick={() => onEnrichAi(current.id)} className="flex-1 px-3 py-2 text-xs rounded-lg border border-bg-600 text-primary-400 hover:border-primary-500/50 transition-colors">✦ IA</button>
              </div>
              <input
                value={reasonText}
                onChange={e => setReasonText(e.target.value)}
                placeholder="Motivo (para perder/ganar)"
                className="w-full mt-2 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
              />
              <div className="mt-2 flex gap-2">
                <input
                  value={noteText}
                  onChange={e => setNoteText(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') addNote() }}
                  placeholder="Nueva nota..."
                  className="flex-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
                />
                <button onClick={addNote} disabled={!noteText.trim() || busy} className="px-3 py-2 text-xs rounded-lg border border-bg-600 text-gray-300 hover:text-primary-300 transition-colors disabled:opacity-40">Agregar</button>
              </div>
              {msg && <p className="text-xs text-primary-400 mt-2">{msg}</p>}
            </div>
          </div>

          {/* Columna der: timeline + propuestas */}
          <div className="md:col-span-3 space-y-4">
            <div className="bg-bg-950 border border-bg-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs text-gray-500 uppercase tracking-wider">PROPUESTAS ({proposals?.length || 0})</h3>
                <div className="flex gap-2">
                  <button onClick={generateProposal} disabled={busy} className="text-xs px-2 py-1 rounded border border-orange-500/40 text-orange-400 hover:bg-orange-500/10 transition-colors disabled:opacity-40">🤖 Con IA</button>
                  <button onClick={() => setShowProposalForm(!showProposalForm)} className="text-xs px-2 py-1 rounded border border-bg-600 text-gray-300 hover:text-primary-300 transition-colors">+ Manual</button>
                </div>
              </div>

              {showProposalForm && (
                <div className="mb-3 space-y-2 bg-bg-900 border border-bg-700 rounded-lg p-3">
                  <input value={propTitle} onChange={e => setPropTitle(e.target.value)} placeholder="Título (opcional)" className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50" />
                  <textarea value={propContent} onChange={e => setPropContent(e.target.value)} rows={5} placeholder="Contenido de la propuesta..." className="w-full px-3 py-2 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50" />
                  <div className="flex justify-end">
                    <button onClick={createProposal} disabled={!propContent.trim() || busy} className="px-3 py-1.5 text-xs rounded-lg border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">Guardar propuesta</button>
                  </div>
                </div>
              )}

              {(!proposals || proposals.length === 0) && (
                <p className="text-xs text-gray-600 py-2">Sin propuestas todavía. Generala con IA o cargala manual.</p>
              )}
              <div className="space-y-2">
                {proposals?.map(p => (
                  <div key={p.id} className="bg-bg-900 border border-bg-700 rounded-lg p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-gray-200">{p.title || `Propuesta ${fmtDateTime(p.created_at)}`}</p>
                      <div className="flex items-center gap-2">
                        {p.model && <span className="text-[10px] text-gray-600">{p.model}</span>}
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${p.status === 'sent' ? 'text-primary-400 border-primary-500/40' : 'text-gray-500 border-bg-600'}`}>{p.status}</span>
                        {p.status !== 'sent' && (
                          <button onClick={() => sendProposal(p.id)} disabled={busy} className="text-[10px] px-2 py-1 rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">✉️ Enviar</button>
                        )}
                      </div>
                    </div>
                    <pre className="mt-2 text-[11px] text-gray-400 whitespace-pre-wrap font-mono max-h-40 overflow-y-auto">{p.content}</pre>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-bg-950 border border-bg-700 rounded-lg p-4">
              <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-3">TIMELINE ({events?.length || 0})</h3>
              {(!events || events.length === 0) && <p className="text-xs text-gray-600 py-2">Sin actividad registrada.</p>}
              <div className="space-y-2">
                {events?.map(e => (
                  <div key={e.id} className="flex gap-3 text-xs">
                    <span className="text-gray-600 whitespace-nowrap mt-0.5">{fmtDateTime(e.created_at)}</span>
                    <span className="text-gray-500 whitespace-nowrap">{eventLabels[e.event_type] || e.event_type}</span>
                    <span className="text-gray-300">{e.description}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ================= Modal nuevo lead ================= */

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
    region: '',
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
              <input value={form.company} onChange={e => set('company', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="Cooperativa XYZ S.A." />
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
              <label className="text-xs text-gray-500 uppercase tracking-wider">Región / Ciudad</label>
              <input value={form.region} onChange={e => set('region', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" placeholder="Asunción, Luque..." />
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
              <textarea value={form.notes} onChange={e => set('notes', e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50 h-20" placeholder="Contexto, necesidades detectadas..." />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 px-5 py-4 border-t border-bg-700">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">Cancelar</button>
          <button onClick={() => form.company && onCreate(form)} disabled={!form.company} className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40">Crear lead</button>
        </div>
      </div>
    </div>
  )
}
