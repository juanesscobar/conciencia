/* Lead Hunter — página de composición (Fase 7: slimming).

   La UI se divide en components/leads/: LeadFilters, LeadTable, LeadDetail,
   PipelineBoard, LeadModal, types. Este archivo solo orquesta estado + datos.
*/

import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { leadsApi } from '../services/api'
import { useRef, useState } from 'react'
import { LeadFilters } from '../components/leads/LeadFilters'
import { LeadTable } from '../components/leads/LeadTable'
import { LeadDetail } from '../components/leads/LeadDetail'
import { PipelineBoard } from '../components/leads/PipelineBoard'
import { LeadModal } from '../components/leads/LeadModal'
import {
  Lead, LeadPage, LeadList, LeadStats, HuntRun, HuntSummary, SavedSearch,
  buildFilterPayload, huntCriteriaFromFilters, fmtDateTime,
} from '../components/leads/types'

export default function LeadsPage() {
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

  const { data: leadsData, isLoading } = useQuery<LeadPage>({
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

  const clearNl = () => { setNlResult(null); setNlQuery(''); setNlDisabled([]) }

  const resetFilters = () => {
    setFilterRegion(''); setFilterSegment(''); setFilterIndustry(''); setFilterOnline('')
    setFilterAge(''); setFilterMinScore(''); setFilterStatus(''); setFilterSource('')
    setFilterList(''); setSearch('')
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

  const handleStatusChange = (lead: Lead, status: string) => {
    leadsApi.action(lead.id, status === 'won' ? 'won' : status === 'lost' ? 'lost' : status,
      status === 'contacted' ? { reason: 'Contactado desde tabla' } : {})
      .then(() => refreshAfterAction(lead.id))
  }

  const handleEnrichWebsiteRow = (lead: Lead) => {
    setSelectedLead(lead)
    setTimeout(() => enrichWebsite.mutate(lead.id), 50)
  }

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
      <LeadFilters
        nlQuery={nlQuery} setNlQuery={setNlQuery} nlBusy={nlBusy} interpretNl={interpretNl}
        runSemantic={runSemantic} semanticBusy={semanticBusy} semanticErr={semanticErr}
        nlResult={nlResult} nlChips={nlChips} nlDisabled={nlDisabled} toggleNlChip={toggleNlChip}
        applyNl={applyNl} clearNl={clearNl}
        search={search} setSearch={setSearch}
        filterStatus={filterStatus} setFilterStatus={setFilterStatus}
        filterSource={filterSource} setFilterSource={setFilterSource}
        filterRegion={filterRegion} setFilterRegion={setFilterRegion}
        filterSegment={filterSegment} setFilterSegment={setFilterSegment}
        filterIndustry={filterIndustry} setFilterIndustry={setFilterIndustry}
        filterOnline={filterOnline} setFilterOnline={setFilterOnline}
        filterAge={filterAge} setFilterAge={setFilterAge}
        filterMinScore={filterMinScore} setFilterMinScore={setFilterMinScore}
        filterList={filterList} setFilterList={setFilterList}
        sort={sort} setSort={setSort}
        showFilters={showFilters} setShowFilters={setShowFilters} activeFilters={activeFilters}
        regions={regions} leadLists={leadLists} savedSearches={savedSearches}
        saveSearchName={saveSearchName} setSaveSearchName={setSaveSearchName}
        showSaveSearch={showSaveSearch} setShowSaveSearch={setShowSaveSearch}
        newListName={newListName} setNewListName={setNewListName}
        showNewList={showNewList} setShowNewList={setShowNewList}
        listMsg={listMsg}
        saveSearch={saveSearch} deleteSearch={deleteSearch} createList={createList}
        deleteList={deleteList} huntRun={huntRun}
        resetFilters={resetFilters}
      />

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
        <LeadTable
          leads={leads}
          total={total}
          semanticRes={semanticRes}
          onClearSemantic={() => { setSemanticRes(null); setSemanticErr('') }}
          onSelect={setSelectedLead}
          onStatusChange={handleStatusChange}
          onEnrichWebsite={handleEnrichWebsiteRow}
          onEnrichAi={(id) => enrichAi.mutate(id)}
          enrichWebsitePending={enrichWebsite.isPending}
          enrichAiPending={enrichAi.isPending}
        />
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
