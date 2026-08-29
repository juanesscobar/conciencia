/* Tipos y helpers compartidos del módulo Leads (Fase 7 — slimming). */

export interface Lead {
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

export interface LeadEvent {
  id: string
  event_type: string
  description: string | null
  created_at: string | null
}

export interface LeadProposal {
  id: string
  lead_id: string
  title: string | null
  content: string
  status: string
  model: string | null
  created_at: string | null
  sent_at: string | null
}

export interface LeadStats {
  total: number
  by_status: Record<string, number>
  by_source: Record<string, number>
  avg_score: number
  top_sources: { source: string; count: number }[]
}

/** Respuesta paginada de GET /api/v1/leads/ */
export interface LeadPage {
  items: Lead[]
  total: number
  page: number
  page_size: number
}

/** Lista guardada de leads */
export interface LeadList {
  id: string
  name: string
  description: string | null
  lead_count: number
  created_at: string | null
}

export interface HuntRun {
  id: string
  source: string
  status: string
  found: number
  added: number
  duplicates: number
  error: string | null
  started_at: string | null
}

export interface HuntSummary {
  results: { source: string; found: number; added: number; duplicates: number; status: string; error?: string | null }[]
  total_found: number
  total_added: number
  total_duplicates: number
}

export interface SavedSearch {
  id: string
  name: string
  filters: Record<string, string>
  created_at: string | null
}

export const proposalStatusStyle: Record<string, string> = {
  draft: 'text-gray-500 border-bg-600',
  sent: 'text-primary-400 border-primary-500/40',
  failed: 'text-alert-400 border-alert-500/40',
}

export const statusColors: Record<string, string> = {
  new: 'bg-blue-500/10 text-blue-400 border border-blue-500/40',
  contacted: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  qualified: 'bg-purple-500/10 text-purple-400 border border-purple-500/40',
  proposal: 'bg-orange-500/10 text-orange-400 border border-orange-500/40',
  won: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  lost: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
}

export const sourceLabels: Record<string, string> = {
  manual: 'manual',
  conciencia: '🌐 conciencia',
  referral: 'referral',
  web: 'web',
  linkedin: 'linkedin',
  overpass: '🗺️ OSM',
  import: '📥 import',
  other: 'otro',
}

export const eventLabels: Record<string, string> = {
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

export function scoreColor(score: number): string {
  if (score >= 70) return 'text-primary-400 border-primary-500/50'
  if (score >= 40) return 'text-yellow-400 border-yellow-500/50'
  return 'text-gray-400 border-bg-600'
}

export function fmtDateTime(d: string | null): string {
  if (!d) return '—'
  const date = new Date(d)
  if (isNaN(date.getTime())) return d
  return date.toLocaleDateString('es-PY', { day: '2-digit', month: '2-digit', year: '2-digit' }) +
    ' ' + date.toLocaleTimeString('es-PY', { hour: '2-digit', minute: '2-digit' })
}

export interface FilterState {
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
}

export function buildFilterPayload(f: FilterState): Record<string, string> {
  const payload: Record<string, string> = {}
  if (f.search) payload.search = f.search
  if (f.filterStatus) payload.status = f.filterStatus
  if (f.filterSource) payload.source = f.filterSource
  if (f.filterRegion) payload.region = f.filterRegion
  if (f.filterSegment) payload.segment = f.filterSegment
  if (f.filterIndustry) payload.industry = f.filterIndustry
  if (f.filterOnline) payload.online = f.filterOnline
  if (f.filterAge) payload.age_days = f.filterAge
  if (f.filterMinScore) payload.min_score = f.filterMinScore
  if (f.filterList) payload.list_id = f.filterList
  if (f.sort) payload.sort = f.sort
  return payload
}

export function applySavedFilters(
  s: SavedSearch,
  setters: {
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
  },
) {
  const flt = s.filters || {}
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

export function huntCriteriaFromFilters(f: { filterSource: string; filterRegion: string; filterSegment: string; filterIndustry: string }): Record<string, string> | null {
  const criteria: Record<string, string> = {}
  if (f.filterSource) criteria.source = f.filterSource
  if (f.filterRegion) criteria.region = f.filterRegion
  if (f.filterSegment) criteria.segment = f.filterSegment
  if (f.filterIndustry) criteria.industry = f.filterIndustry
  return Object.keys(criteria).length ? criteria : null
}
