import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { leadsApi } from '../services/api'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
  // --- Fase 4: ranking/scoring separados ---
  search_relevance?: number | null
  opportunity_score?: number | null
  data_quality?: number | null
  reasons?: string[] | null
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

const proposalStatusStyle: Record<string, string> = {
  draft: 'text-gray-500 border-bg-600',
  sent: 'text-primary-400 border-primary-500/40',
  failed: 'text-alert-400 border-alert-500/40',
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

interface SavedSearch {
  id: string
  name: string
  filters: Record<string, string>
  created_at: string | null
}

interface LeadList {
  id: string
  name: string
  description: string | null
  lead_count: number
  created_at: string | null
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

// Snapshot de filtros para guardar/cargar búsquedas
function buildFilterPayload(f: {
  search: string
  filterStatus: string
  filterSource: string
  filterRegion: string
  filterSegment: string
  filterIndustry: string
  filterOnline: string
  filterAge: string
  filterMinScore: string
  filterList: string
  sort: string
}): Record<string, string> {
  return {
    search: f.search || '',
    status: f.filterStatus || '',
    source: f.filterSource || '',
    region: f.filterRegion || '',
    segment: f.filterSegment || '',
    industry: f.filterIndustry || '',
    online: f.filterOnline || '',
    age_days: f.filterAge || '',
    min_score: f.filterMinScore || '',
    list_id: f.filterList || '',
    sort: f.sort || 'newest',
  }
}

// Aplica un snapshot de filtros guardado
function applySavedFilters(f: SavedSearch, setters: {
  setSearch: (v: string) => void
  setFilterStatus: (v: string) => void
  setFilterSource: (v: string) => void
  setFilterRegion: (v: string) => void
  setFilterSegment: (v: string) => void
  setFilterIndustry: (v: string) => void
  setFilterOnline: (v: string) => void
  setFilterAge: (v: string) => void
  setFilterMinScore: (v: string) => void
  setFilterList: (v: string) => void
  setSort: (v: string) => void
}) {
  const flt = f.filters || {}
  setters.setSearch(flt.search || '')
  setters.setFilterStatus(flt.status || '')
  setters.setFilterSource(flt.source || '')
  setters.setFilterRegion(flt.region || '')
  setters.setFilterSegment(flt.segment || '')
  setters.setFilterIndustry(flt.industry || '')
  setters.setFilterOnline(flt.online || '')
  setters.setFilterAge(flt.age_days || '')
  setters.setFilterMinScore(flt.min_score || '')
  setters.setFilterList(flt.list_id || '')
  setters.setSort(flt.sort || 'newest')
}

// Criterios de caza derivados de los filtros activos (para hunt/run)
function huntCriteriaFromFilters(f: {
  filterSource: string
  filterRegion: string
  filterSegment: string
  filterIndustry: string
}): Record<string, string> | undefined {
  const c: Record<string, string> = {}
  if (f.filterSource) c.source = f.filterSource
  if (f.filterRegion) c.region = f.filterRegion
  if (f.filterSegment) c.segment = f.filterSegment
  if (f.filterIndustry) c.industry = f.filterIndustry
  return Object.keys(c).length ? c : undefined
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
  const [filterList, setFilterList] = useState('')
  const [sort, setSort] = useState('newest')
  const [showFilters, setShowFilters] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  // --- Búsqueda semántica (Fase 5, spec §14) ---
  const [semanticRes, setSemanticRes] = useState<{ items: Lead[]; query: string } | null>(null)
  const [semanticBusy, setSemanticBusy] = useState(false)
  const [semanticErr, setSemanticErr] = useState('')
  const [viewMode, setViewMode] = useState<'table' | 'pipeline'>('table')
  const [huntResult, setHuntResult] = useState<HuntSummary | null>(null)
  const [importMsg, setImportMsg] = useState('')
  const [saveSearchName, setSaveSearchName] = useState('')
  const [showSaveSearch, setShowSaveSearch] = useState(false)
  const [newListName, setNewListName] = useState('')
  const [showNewList, setShowNewList] = useState(false)
  const [listMsg, setListMsg] = useState('')
  const [nlQuery, setNlQuery] = useState('')
  const [nlResult, setNlResult] = useState<any>(null)
  const [nlBusy, setNlBusy] = useState(false)
  const [nlDisabled, setNlDisabled] = useState<string[]>([])
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
    queryKey: ['leads', search, filterStatus, filterSource, filterRegion, filterSegment, filterIndustry, filterOnline, filterAge, filterMinScore, filterList, sort],
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
        list_id: filterList || undefined,
        sort,
        page_size: 100,
      }).then(res => res.data),
  })

  const { data: savedSearches } = useQuery<SavedSearch[]>({
    queryKey: ['lead-searches'],
    queryFn: () => leadsApi.searches().then(res => res.data),
  })

  const { data: leadLists } = useQuery<LeadList[]>({
    queryKey: ['lead-lists'],
    queryFn: () => leadsApi.lists().then(res => res.data),
  })

  const { data: huntSources } = useQuery({
    queryKey: ['hunt-sources'],
    queryFn: () => leadsApi.huntSources().then(res => res.data),
  })

  const { data: geoScope } = useQuery({
    queryKey: ['lead-geo-scope'],
    queryFn: () => leadsApi.geoScope().then(res => res.data),
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
    mutationFn: (params?: any) => leadsApi.huntRun(params),
    onSuccess: (res) => {
      setHuntResult(res.data)
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
      queryClient.invalidateQueries({ queryKey: ['hunt-runs'] })
    },
  })

  const saveSearch = useMutation({
    mutationFn: (name: string) => leadsApi.searchSave({ name, filters: buildFilterPayload({
      search, filterStatus, filterSource, filterRegion, filterSegment, filterIndustry, filterOnline, filterAge, filterMinScore, filterList, sort,
    }) }),
    onSuccess: () => {
      setSaveSearchName('')
      setShowSaveSearch(false)
      queryClient.invalidateQueries({ queryKey: ['lead-searches'] })
    },
  })

  const deleteSearch = useMutation({
    mutationFn: (id: string) => leadsApi.searchDelete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['lead-searches'] }),
  })

  const createList = useMutation({
    mutationFn: (name: string) => leadsApi.listCreate({ name }),
    onSuccess: (res) => {
      setNewListName('')
      setShowNewList(false)
      setFilterList(res.data.id)
      setListMsg(`Lista "${res.data.name}" creada`)
      queryClient.invalidateQueries({ queryKey: ['lead-lists'] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      setTimeout(() => setListMsg(''), 4000)
    },
  })

  const deleteList = useMutation({
    mutationFn: (id: string) => leadsApi.listDelete(id),
    onSuccess: () => {
      setFilterList('')
      queryClient.invalidateQueries({ queryKey: ['lead-lists'] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
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
    queryClient.invalidateQueries({ queryKey: ['lead-lists-of', id] })
  }

  const runSemantic = async () => {
    const text = (nlQuery.trim() || search.trim())
    if (!text) { setSemanticErr('Escribí una consulta (arriba o en el campo de búsqueda)'); return }
    setSemanticBusy(true); setSemanticErr('')
    try {
      const { data } = await leadsApi.semanticSearch(text, 25)
      if (data.items.length === 0) setSemanticErr('Sin resultados semánticos — probá otra redacción o habilitá embeddings reales en Settings')
      setSemanticRes({ items: data.items as Lead[], query: data.query })
    } catch (e: any) {
      setSemanticErr(e.response?.data?.detail || e.message || 'Error en búsqueda semántica')
    } finally {
      setSemanticBusy(false)
    }
  }
  // --- Búsqueda en lenguaje natural (Fase 2: interpret → chips editables) ---
  const interpretNl = async () => {
    if (!nlQuery.trim()) return
    setNlBusy(true)
    try {
      const { data } = await leadsApi.searchInterpret(nlQuery.trim())
      setNlResult(data)
      setNlDisabled([])
    } catch (e: any) {
      setNlResult({ error: e.response?.data?.detail || e.message })
    } finally {
      setNlBusy(false)
    }
  }

  const nlChips = (() => {
    if (!nlResult || nlResult.error) return []
    const chips: { key: string; label: string }[] = []
    if (nlResult.query) chips.push({ key: 'query', label: `🔎 ${nlResult.query}` })
    if (nlResult.category) chips.push({ key: 'category', label: `🏷️ ${nlResult.category}` })
    if (nlResult.region) chips.push({ key: 'region', label: `📍 ${nlResult.region}` })
    if (nlResult.city) chips.push({ key: 'city', label: `🏙️ ${nlResult.city}` })
    if (nlResult.country) chips.push({ key: 'country', label: `🌎 ${nlResult.country}` })
    if (nlResult.required_fields?.length) chips.push({ key: 'required', label: `📡 ${nlResult.required_fields.join(' + ')}` })
    if (nlResult.online) chips.push({ key: 'online', label: `🌐 ${nlResult.online}` })
    return chips.filter(c => !nlDisabled.includes(c.key))
  })()

  const toggleNlChip = (key: string) => {
    setNlDisabled(d => d.includes(key) ? d.filter(k => k !== key) : [...d, key])
  }

  const applyNl = () => {
    if (!nlResult || nlResult.error) return
    setSearch(nlResult.query || '')
    setFilterRegion(nlResult.region || '')
    setFilterIndustry(nlResult.industry || '')
    setFilterOnline(nlResult.online || (nlResult.required_fields?.length ? 'any' : ''))
    setNlResult(null)
    setNlQuery('')
  }

  const refreshAfterAction = (id: string) => {
    queryClient.invalidateQueries({ queryKey: ['leads'] })
    queryClient.invalidateQueries({ queryKey: ['lead-stats'] })
    queryClient.invalidateQueries({ queryKey: ['lead-detail', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-events', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-proposals', id] })
    queryClient.invalidateQueries({ queryKey: ['lead-lists'] })
    queryClient.invalidateQueries({ queryKey: ['lead-lists-of', id] })
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
          <div className="flex rounded-lg border border-bg-600 overflow-hidden">
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${viewMode === 'table' ? 'bg-primary-500/15 text-primary-400' : 'text-gray-400 hover:text-gray-200'}`}
            >
              ☰ Tabla
            </button>
            <button
              onClick={() => setViewMode('pipeline')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${viewMode === 'pipeline' ? 'bg-primary-500/15 text-primary-400' : 'text-gray-400 hover:text-gray-200'}`}
            >
              🗂 Pipeline
            </button>
          </div>
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
            <span
              className="text-xs px-2 py-1 rounded border border-bg-600 text-gray-400"
              title="Scope geográfico efectivo (Settings → Search Geography)"
            >
              {geoScope?.is_global ? '🌍 Global' : `📍 ${geoScope?.country || 'PY'} · ${
                geoScope?.scope === 'city' ? 'Ciudad' : geoScope?.scope === 'region' ? 'Región' : 'País'
              }`}
            </span>
            <button
              onClick={() => huntRun.mutate({
                ...(huntCriteriaFromFilters({ filterSource, filterRegion, filterSegment, filterIndustry }) || {}),
                country: geoScope?.country || undefined,
                city: geoScope?.city || undefined,
              })}
              disabled={huntRun.isPending}
              title="Cazar con los filtros activos dentro del scope geográfico configurado"
              className="px-4 py-2 bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all shadow-neon disabled:opacity-40 disabled:cursor-wait"
            >
              {huntRun.isPending ? '⌛ Cazando...' : '🔎 Cazar leads'}
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
        {/* Búsqueda en lenguaje natural (Fase 2) */}
        <div className="mb-3 pb-3 border-b border-bg-700">
          <div className="flex flex-col md:flex-row gap-2">
            <input
              type="text"
              value={nlQuery}
              onChange={e => setNlQuery(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') interpretNl() }}
              placeholder='🧠 Buscar en lenguaje natural: "playas de autos usados en Ciudad del Este"'
              className="flex-1 px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
            />
            <button
              onClick={interpretNl}
              disabled={nlBusy || !nlQuery.trim()}
              className="px-4 py-2 text-sm rounded-lg border border-primary-500/40 bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 transition-all shadow-neon disabled:opacity-40 whitespace-nowrap"
            >
              {nlBusy ? '⏳ Interpretando...' : '🧠 Interpretar'}
            </button>
            <button
              onClick={runSemantic}
              disabled={semanticBusy || !(nlQuery.trim() || search.trim())}
              title="Búsqueda semántica: embed la consulta y rankea por similitud (Fase 5)"
              className="px-4 py-2 text-sm rounded-lg border border-cyan-500/40 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 transition-all disabled:opacity-40 whitespace-nowrap"
            >
              {semanticBusy ? '⏳ Buscando...' : '🧬 Semántica'}
            </button>
          </div>
          {semanticErr && (
            <p className="text-xs text-alert-400 mt-2">{semanticErr}</p>
          )}
          {nlResult?.error && (
            <p className="text-xs text-alert-400 mt-2">{nlResult.error}</p>
          )}
          {nlResult && !nlResult.error && nlChips.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-[10px] text-gray-600 uppercase tracking-wider">Filtros detectados:</span>
              {nlChips.map(c => (
                <button
                  key={c.key}
                  onClick={() => toggleNlChip(c.key)}
                  title={nlDisabled.includes(c.key) ? 'Quitado — click para volver a incluirlo' : 'Click para quitar este filtro'}
                  className={`text-[11px] px-2 py-1 rounded border font-mono transition-colors ${nlDisabled.includes(c.key) ? 'border-bg-600 text-gray-600 line-through' : 'border-primary-500/40 text-primary-300 bg-primary-500/10 hover:bg-primary-500/20'}`}
                >
                  {c.label} ✕
                </button>
              ))}
              <div className="flex items-center gap-2 ml-1">
                <button
                  onClick={applyNl}
                  className="text-[11px] px-3 py-1 rounded border border-primary-500/50 text-primary-300 bg-primary-500/20 hover:bg-primary-500/30 transition-colors"
                >
                  Aplicar búsqueda
                </button>
                <button
                  onClick={() => { setNlResult(null); setNlQuery(''); setNlDisabled([]) }}
                  className="text-[11px] px-2 py-1 rounded text-gray-500 hover:text-gray-300 transition-colors"
                >
                  Limpiar
                </button>
              </div>
            </div>
          )}
        </div>
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
          {/* Cazar con los filtros activos, pegadito a ellos */}
          <button
            onClick={() => huntRun.mutate(huntCriteriaFromFilters({ filterSource, filterRegion, filterSegment, filterIndustry }))}
            disabled={huntRun.isPending}
            title={
              huntCriteriaFromFilters({ filterSource, filterRegion, filterSegment, filterIndustry })
                ? 'Cazar leads nuevos que matcheen los filtros activos (fuente/región/segmento/sector)'
                : 'Sin filtros de caza: buscá con ⚙ Filtros (sector/región/segmento) para acotar, o usá Cazar TODO arriba'
            }
            className="px-4 py-2 text-sm rounded-lg border border-primary-500/40 bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 transition-all shadow-neon disabled:opacity-40 disabled:cursor-wait whitespace-nowrap"
          >
            {huntRun.isPending ? '⌛ Cazando...' : '🔎 Cazar leads con filtros'}
          </button>
        </div>

        {/* Búsquedas guardadas + listas (accesos rápidos) */}
        <div className="mt-3 pt-3 border-t border-bg-700 flex flex-wrap items-center gap-2">
          {/* Guardar búsqueda actual */}
          {showSaveSearch ? (
            <div className="flex items-center gap-2">
              <input
                value={saveSearchName}
                onChange={e => setSaveSearchName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && saveSearchName.trim()) saveSearch.mutate(saveSearchName.trim()) }}
                placeholder="Nombre de la búsqueda"
                autoFocus
                className="px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
              />
              <button onClick={() => saveSearchName.trim() && saveSearch.mutate(saveSearchName.trim())} disabled={!saveSearchName.trim() || saveSearch.isPending} className="px-3 py-1.5 text-xs rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">💾 Guardar</button>
              <button onClick={() => { setShowSaveSearch(false); setSaveSearchName('') }} className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-300">✕</button>
            </div>
          ) : (
            <button onClick={() => setShowSaveSearch(true)} className="px-3 py-1.5 text-xs rounded border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors" title="Guardar los filtros actuales como búsqueda">
              💾 Guardar búsqueda
            </button>
          )}

          {/* Búsquedas guardadas */}
          {savedSearches && savedSearches.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-[10px] text-gray-600 uppercase tracking-wider">Guardadas:</span>
              {savedSearches.map(s => (
                <span key={s.id} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-bg-600 text-gray-300 bg-bg-950">
                  <button onClick={() => applySavedFilters(s, { setSearch, setFilterStatus, setFilterSource, setFilterRegion, setFilterSegment, setFilterIndustry, setFilterOnline, setFilterAge, setFilterMinScore, setFilterList, setSort })} title="Cargar esta búsqueda" className="hover:text-primary-300">
                    🔍 {s.name}
                  </button>
                  <button onClick={() => deleteSearch.mutate(s.id)} title="Borrar" className="text-gray-600 hover:text-alert-400">✕</button>
                </span>
              ))}
            </div>
          )}

          <span className="text-gray-800 mx-1">|</span>

          {/* Lista de leads */}
          <select
            value={filterList}
            onChange={e => setFilterList(e.target.value)}
            className="px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
            title="Filtrar por lista guardada"
          >
            <option value="">📁 Lista: todas</option>
            {leadLists?.map(l => (
              <option key={l.id} value={l.id}>{l.name} ({l.lead_count})</option>
            ))}
          </select>
          {filterList && (
            <button onClick={() => deleteList.mutate(filterList)} className="text-[10px] text-gray-600 hover:text-alert-400" title="Eliminar lista actual">🗑 lista</button>
          )}
          {showNewList ? (
            <div className="flex items-center gap-2">
              <input
                value={newListName}
                onChange={e => setNewListName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && newListName.trim()) createList.mutate(newListName.trim()) }}
                placeholder="Nombre de la lista"
                autoFocus
                className="px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
              />
              <button onClick={() => newListName.trim() && createList.mutate(newListName.trim())} disabled={!newListName.trim() || createList.isPending} className="px-3 py-1.5 text-xs rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">+ Crear</button>
              <button onClick={() => { setShowNewList(false); setNewListName('') }} className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-300">✕</button>
            </div>
          ) : (
            <button onClick={() => setShowNewList(true)} className="px-3 py-1.5 text-xs rounded border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors" title="Crear una lista para agrupar leads (ej: seguimiento, región)">
              📁 + Nueva lista
            </button>
          )}
          {listMsg && <span className="text-[11px] text-primary-400">{listMsg}</span>}
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
            <div className="col-span-2 flex items-end gap-2">
              <button
                onClick={() => { setFilterRegion(''); setFilterSegment(''); setFilterIndustry(''); setFilterOnline(''); setFilterAge(''); setFilterMinScore(''); setFilterStatus(''); setFilterSource(''); setFilterList(''); setSearch('') }}
                className="px-4 py-2 text-sm rounded-lg border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors"
              >
                ⟲ Limpiar filtros
              </button>
              {huntCriteriaFromFilters({ filterSource, filterRegion, filterSegment, filterIndustry }) && (
                <button
                  onClick={() => huntRun.mutate(huntCriteriaFromFilters({ filterSource, filterRegion, filterSegment, filterIndustry }))}
                  disabled={huntRun.isPending}
                  className="px-4 py-2 text-sm rounded-lg border border-primary-500/40 bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 transition-all disabled:opacity-40"
                >
                  {huntRun.isPending ? '⌛ Cazando...' : `🔎 Cazar: ${[filterIndustry, filterSegment, filterRegion, filterSource].filter(Boolean).join(' · ')}`}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Tabla / Pipeline */}
      {isLoading ? (
        <div className="text-primary-400 animate-blink">Loading leads...</div>
      ) : viewMode === 'pipeline' ? (
        <PipelineBoard
          leads={semanticRes ? semanticRes.items : leads}
          onSelect={setSelectedLead}
          onMove={(id, status) => leadsApi.action(id, status).then(() => refreshAfterAction(id))}
          busy={!!(enrichWebsite.isPending || enrichAi.isPending)}
        />
      ) : (
        <div className="bg-bg-900 border border-bg-700 rounded-lg overflow-hidden">
          {semanticRes && (
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-cyan-500/30 bg-cyan-500/5">
              <p className="text-xs text-cyan-300">
                🧬 Resultados semánticos para «{semanticRes.query}» — {semanticRes.items.length} matches
              </p>
              <button
                onClick={() => { setSemanticRes(null); setSemanticErr('') }}
                className="text-[11px] px-2 py-1 rounded border border-bg-600 text-gray-400 hover:text-gray-200 transition-colors"
              >
                ← volver a lista normal
              </button>
            </div>
          )}
          <div className="overflow-auto max-h-[calc(100vh-320px)]">
            <table className="w-full text-sm min-w-[1000px]">
              <thead className="sticky top-0 z-10 bg-bg-900">
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
                {(semanticRes ? semanticRes.items : leads).length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                      Sin leads con esos filtros — apretá «Cazar leads ahora» o importá un CSV
                    </td>
                  </tr>
                )}
                {(semanticRes ? semanticRes.items : leads).map(lead => (
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
                      <div className="flex flex-col gap-1">
                        <span className={`inline-flex px-2 py-0.5 rounded border ${scoreColor(lead.score)} text-xs font-mono`}>
                          {lead.score}
                        </span>
                        {(lead.data_quality != null || lead.opportunity_score != null || lead.search_relevance != null) && (
                          <span
                            title={(lead.reasons || []).join('\n') || 'Sin razones'}
                            className="text-[10px] font-mono text-gray-500 cursor-help"
                          >
                            {lead.search_relevance != null ? `R:${Math.round(lead.search_relevance)} ` : ''}O:{lead.opportunity_score ?? '–'} · Q:{lead.data_quality ?? '–'}
                          </span>
                        )}
                      </div>
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
            {semanticRes ? semanticRes.items.length : total} leads{semanticRes ? ' (semánticos)' : ` · ${leads.filter(l => l.status === 'new').length} nuevos en esta vista`}
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

/* ================= Pipeline (mini CRM kanban) ================= */

const PIPELINE_COLUMNS: { status: string; label: string; emoji: string }[] = [
  { status: 'new', label: 'Nuevos', emoji: '🆕' },
  { status: 'contacted', label: 'Contactados', emoji: '📞' },
  { status: 'qualified', label: 'Calificados', emoji: '✔️' },
  { status: 'proposal', label: 'Propuesta', emoji: '📄' },
  { status: 'won', label: 'Ganados', emoji: '🏆' },
  { status: 'lost', label: 'Perdidos', emoji: '❌' },
]

const PIPELINE_STYLES: Record<string, { header: string; card: string }> = {
  new: { header: 'border-blue-500/40 text-blue-400', card: 'border-blue-500/20 hover:border-blue-500/50' },
  contacted: { header: 'border-yellow-500/40 text-yellow-400', card: 'border-yellow-500/20 hover:border-yellow-500/50' },
  qualified: { header: 'border-purple-500/40 text-purple-400', card: 'border-purple-500/20 hover:border-purple-500/50' },
  proposal: { header: 'border-orange-500/40 text-orange-400', card: 'border-orange-500/20 hover:border-orange-500/50' },
  won: { header: 'border-primary-500/40 text-primary-400', card: 'border-primary-500/20 hover:border-primary-500/50' },
  lost: { header: 'border-alert-500/40 text-alert-400', card: 'border-alert-500/20 hover:border-alert-500/50' },
}

function PipelineBoard({ leads, onSelect, onMove, busy }: {
  leads: Lead[]
  onSelect: (lead: Lead) => void
  onMove: (id: string, status: string) => void
  busy: boolean
}) {
  const byStatus = (s: string) => leads.filter(l => l.status === s)

  const move = (lead: Lead, status: string) => {
    if (status === lead.status) return
    onMove(lead.id, status)
  }

  return (
    <div className="overflow-auto max-h-[calc(100vh-320px)] pb-2 -mx-1 px-1">
      <div className="flex gap-3 min-w-[900px]">
        {PIPELINE_COLUMNS.map(col => {
          const items = byStatus(col.status)
          const st = PIPELINE_STYLES[col.status] || PIPELINE_STYLES.new
          return (
            <div key={col.status} className="flex-1 min-w-[140px] bg-bg-950/60 border border-bg-700 rounded-lg flex flex-col">
              <div className={`px-3 py-2 border-b ${st.header} flex items-center justify-between`}>
                <span className="text-xs font-bold uppercase tracking-wider">{col.emoji} {col.label}</span>
                <span className="text-xs font-mono text-gray-500">{items.length}</span>
              </div>
              <div className="p-2 space-y-2 flex-1">
                {items.length === 0 && (
                  <p className="text-[10px] text-gray-700 text-center py-4">vacío</p>
                )}
                {items.map(lead => (
                  <div
                    key={lead.id}
                    onClick={() => onSelect(lead)}
                    className={`bg-bg-900 border rounded-lg p-2.5 cursor-pointer transition-all group ${st.card}`}
                  >
                    <p className="text-xs font-medium text-gray-200 leading-tight group-hover:text-primary-300 transition-colors">{lead.company}</p>
                    {lead.contact_name && <p className="text-[10px] text-gray-500 mt-1">👤 {lead.contact_name}</p>}
                    {(lead.region || lead.industry) && (
                      <p className="text-[10px] text-gray-600 mt-0.5">
                        {[lead.region && `📍 ${lead.region}`, lead.industry].filter(Boolean).join(' · ')}
                      </p>
                    )}
                    <div className="flex items-center justify-between mt-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${scoreColor(lead.score)}`}>{lead.score}</span>
                      <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                        {PIPELINE_COLUMNS.filter(c => c.status !== lead.status).map(c => (
                          <button
                            key={c.status}
                            disabled={busy}
                            onClick={() => move(lead, c.status)}
                            title={`Mover a ${c.label}`}
                            className="text-[10px] px-1.5 py-0.5 rounded border border-bg-600 text-gray-500 hover:text-primary-300 hover:border-primary-500/40 transition-colors disabled:opacity-30"
                          >
                            {c.emoji}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
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
  const [setupCta, setSetupCta] = useState<string | null>(null)
  const [addListId, setAddListId] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

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

  const { data: leadLists } = useQuery<LeadList[]>({
    queryKey: ['lead-lists-of', lead.id],
    queryFn: () => leadsApi.leadLists(lead.id).then(res => res.data),
  })

  const { data: allLists } = useQuery<LeadList[]>({
    queryKey: ['lead-lists'],
    queryFn: () => leadsApi.lists().then(res => res.data),
  })

  const current = detail || lead

  const toggleList = async (listId: string, isIn: boolean) => {
    setBusy(true)
    try {
      if (isIn) {
        await leadsApi.listRemoveLead(listId, current.id)
      } else {
        await leadsApi.listAddLead(listId, current.id)
      }
      onAction(current.id)
      queryClient.invalidateQueries({ queryKey: ['lead-lists'] })
      queryClient.invalidateQueries({ queryKey: ['lead-lists-of', current.id] })
      setAddListId('')
    } catch (e: any) {
      setMsg(`Error con lista: ${e.response?.data?.detail || e.message}`)
    } finally {
      setBusy(false)
    }
  }

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
    setMsg('🤖 Generando con el squad PM → R&D → Fin → Comms...')
    setSetupCta(null)
    try {
      await leadsApi.proposalGenerate(current.id)
      onAction(current.id)
      setMsg('📄 Propuesta generada con IA')
      setTimeout(() => setMsg(''), 5000)
    } catch (e: any) {
      if (e.response?.status === 409) {
        setMsg(e.response?.data?.detail || 'IA no configurada')
        setSetupCta('/settings')
      } else {
        setMsg(`Error: ${e.response?.data?.detail || e.message}`)
      }
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

  const sendProposal = async (pid: string, channel?: 'email' | 'whatsapp') => {
    setBusy(true)
    try {
      const res = await leadsApi.proposalSend(pid, channel ? { channel } : {})
      onAction(current.id)
      const sr = res.data?.send_result
      if (sr?.method === 'whatsapp_link' && sr?.url) {
        setMsg('🔗 WhatsApp no conectado — abriendo link wa.me')
        window.open(sr.url, '_blank')
      } else if (sr?.method === 'whatsapp_api' && sr?.sent) {
        setMsg('✅ Propuesta enviada por WhatsApp')
      } else if (sr?.method === 'smtp' && sr?.sent) {
        setMsg(`✅ Propuesta enviada por email a ${sr.to}`)
      } else if (sr?.method === 'mailto') {
        setMsg('📧 SMTP no configurado — se abrió tu cliente de correo')
        if (sr?.url) window.open(sr.url, '_blank')
      } else if (res.data?.status === 'failed' || sr?.sent === false) {
        setMsg(`❌ No se pudo enviar: ${sr?.error || sr?.reason || 'error desconocido'}`)
      } else {
        setMsg('✉️ Propuesta marcada como enviada')
      }
      setTimeout(() => setMsg(''), 5000)
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

  const downloadProposalPdf = async (pid: string) => {
    setBusy(true)
    try {
      const res = await leadsApi.proposalPdf(pid)
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `propuesta-${current.company.replace(/[^a-zA-Z0-9-_]+/g, '-').toLowerCase()}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setMsg('📄 PDF descargado')
      setTimeout(() => setMsg(''), 4000)
    } catch (e: any) {
      setMsg(`Error generando PDF: ${e.response?.data?.detail || e.message}`)
    } finally {
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
              {(current.metadata as any)?.analysis && (
                <div className="pt-2 border-t border-bg-700">
                  <p className="text-gray-500 text-xs mb-1">✦ Análisis IA:</p>
                  <pre className="text-[11px] text-gray-400 whitespace-pre-wrap font-mono max-h-40 overflow-y-auto">{(current.metadata as any).analysis}</pre>
                </div>
              )}
              <div className="pt-2 border-t border-bg-700">
                <span className="text-gray-500 text-xs">Presencia online: </span>
                <span className="text-xs text-gray-300">
                  {op?.website ? '🌐 web' : ''} {op?.email ? '✉ email' : ''} {op?.phone ? '📞 tel' : ''}
                  {!(op?.website || op?.email || op?.phone) && <span className="text-gray-600">sin canales digitales</span>}
                </span>
              </div>
            </div>

            <div className="bg-bg-950 border border-bg-700 rounded-lg p-4">
              <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-3">SCORE INTELLIGENCE</h3>
              <div className="space-y-2.5">
                {[
                  { label: 'Lead score', value: current.score, color: 'bg-primary-500' },
                  { label: 'Oportunidad', value: current.opportunity_score ?? null, color: 'bg-yellow-500' },
                  { label: 'Calidad de datos', value: current.data_quality ?? null, color: 'bg-purple-500' },
                  { label: 'Relevancia (búsqueda)', value: current.search_relevance ?? null, color: 'bg-cyan-500' },
                ].map(m => (
                  <div key={m.label}>
                    <div className="flex justify-between text-[11px] text-gray-500 mb-0.5">
                      <span>{m.label}</span>
                      <span className="font-mono text-gray-300">{m.value != null ? `${m.value}/100` : '—'}</span>
                    </div>
                    <div className="h-1.5 bg-bg-800 rounded overflow-hidden">
                      <div
                        className={`h-full ${m.color} rounded transition-all`}
                        style={{ width: `${m.value != null ? Math.max(2, Math.min(100, m.value)) : 0}%` }}
                      />
                    </div>
                  </div>
                ))}
                {(current.reasons?.length ?? 0) > 0 && (
                  <div className="pt-2 border-t border-bg-700">
                    <p className="text-[11px] text-gray-500 uppercase tracking-wider mb-1">¿Por qué este lead?</p>
                    <ul className="space-y-1">
                      {(current.reasons || []).map((r, i) => (
                        <li key={i} className="text-[11px] text-gray-400 flex gap-1.5">
                          <span className="text-primary-500">▸</span>{r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
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
              {msg && (
                <p className="text-xs text-primary-400 mt-2">
                  {msg}
                  {setupCta && (
                    <button onClick={() => navigate(setupCta)} className="underline text-primary-300 hover:text-primary-200 ml-1">
                      → Configurar en Integraciones
                    </button>
                  )}
                </p>
              )}
            </div>

            <div className="bg-bg-950 border border-bg-700 rounded-lg p-4">
              <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-3">LISTAS</h3>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {(!leadLists || leadLists.length === 0) && (
                  <span className="text-xs text-gray-600">No está en ninguna lista.</span>
                )}
                {leadLists?.map(l => (
                  <span key={l.id} className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded border border-primary-500/40 bg-primary-500/10 text-primary-300">
                    📁 {l.name}
                    <button onClick={() => toggleList(l.id, true)} disabled={busy} title="Sacar de la lista" className="text-gray-500 hover:text-alert-400 disabled:opacity-40">✕</button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <select
                  value={addListId}
                  onChange={e => setAddListId(e.target.value)}
                  className="flex-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
                >
                  <option value="">Agregar a lista...</option>
                  {(allLists || [])
                    .filter(l => !(leadLists || []).some(x => x.id === l.id))
                    .map(l => <option key={l.id} value={l.id}>{l.name} ({l.lead_count})</option>)}
                </select>
                <button
                  onClick={() => addListId && toggleList(addListId, false)}
                  disabled={!addListId || busy}
                  className="px-3 py-2 text-xs rounded-lg border border-bg-600 text-gray-300 hover:text-primary-300 hover:border-primary-500/50 transition-colors disabled:opacity-40"
                >
                  +
                </button>
              </div>
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
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${proposalStatusStyle[p.status] || proposalStatusStyle.draft}`}>
                          {p.status === 'sent' && p.sent_at ? `sent ${fmtDateTime(p.sent_at)}` : p.status}
                        </span>
                        {p.status !== 'sent' && (
                          <div className="flex gap-1">
                            <button onClick={() => sendProposal(p.id, 'email')} disabled={busy} title="Enviar por email (SMTP)" className="text-[10px] px-1.5 py-1 rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">📧</button>
                            <button onClick={() => sendProposal(p.id, 'whatsapp')} disabled={busy} title="Enviar por WhatsApp" className="text-[10px] px-1.5 py-1 rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">🟢</button>
                            <button onClick={() => sendProposal(p.id)} disabled={busy} title="Marcar enviada" className="text-[10px] px-1.5 py-1 rounded border border-bg-600 text-gray-400 hover:text-primary-300 transition-colors disabled:opacity-40">✓</button>
                          </div>
                        )}
                        <button onClick={() => downloadProposalPdf(p.id)} disabled={busy} title="Descargar PDF" className="text-[10px] px-1.5 py-1 rounded border border-orange-500/40 text-orange-400 hover:bg-orange-500/10 transition-colors disabled:opacity-40">⬇ PDF</button>
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
