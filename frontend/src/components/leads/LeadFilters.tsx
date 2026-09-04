/* Barra de búsqueda (NL + semántica), filtros, caza y búsquedas guardadas.
   Extraído de Leads.tsx (Fase 7 — slimming). */

import { LeadList, SavedSearch, huntCriteriaFromFilters, applySavedFilters } from './types'

interface Mut {
  mutate: (data?: any) => void
  isPending?: boolean
}

export interface LeadFiltersProps {
  nlQuery: string
  setNlQuery: (v: string) => void
  nlBusy: boolean
  interpretNl: () => void
  runSemantic: () => void
  semanticBusy: boolean
  semanticErr: string
  nlResult: any
  nlChips: { key: string; label: string }[]
  nlDisabled: string[]
  toggleNlChip: (k: string) => void
  applyNl: () => void
  clearNl: () => void
  search: string
  setSearch: (v: string) => void
  filterStatus: string
  setFilterStatus: (v: string) => void
  filterSource: string
  setFilterSource: (v: string) => void
  filterRegion: string
  setFilterRegion: (v: string) => void
  filterSegment: string
  setFilterSegment: (v: string) => void
  filterIndustry: string
  setFilterIndustry: (v: string) => void
  filterOnline: string
  setFilterOnline: (v: string) => void
  filterAge: string
  setFilterAge: (v: string) => void
  filterMinScore: string
  setFilterMinScore: (v: string) => void
  filterList: string
  setFilterList: (v: string) => void
  sort: string
  setSort: (v: string) => void
  showFilters: boolean
  setShowFilters: (v: boolean) => void
  activeFilters: number
  regions?: string[]
  leadLists?: LeadList[]
  savedSearches?: SavedSearch[]
  saveSearchName: string
  setSaveSearchName: (v: string) => void
  showSaveSearch: boolean
  setShowSaveSearch: (v: boolean) => void
  newListName: string
  setNewListName: (v: string) => void
  showNewList: boolean
  setShowNewList: (v: boolean) => void
  listMsg: string
  saveSearch: Mut
  deleteSearch: Mut
  createList: Mut
  deleteList: Mut
  huntRun: Mut
  resetFilters: () => void
}

export function LeadFilters(p: LeadFiltersProps) {
  const filterSetters = {
    setSearch: p.setSearch,
    setFilterStatus: p.setFilterStatus,
    setFilterSource: p.setFilterSource,
    setFilterRegion: p.setFilterRegion,
    setFilterSegment: p.setFilterSegment,
    setFilterIndustry: p.setFilterIndustry,
    setFilterOnline: p.setFilterOnline,
    setFilterAge: p.setFilterAge,
    setFilterMinScore: p.setFilterMinScore,
    setFilterList: p.setFilterList,
    setSort: p.setSort,
  }

  return (
    <div className="bg-bg-900 border border-bg-700 rounded-lg p-4 mb-4">
      {/* Búsqueda en lenguaje natural (Fase 2) */}
      <div className="mb-3 pb-3 border-b border-bg-700">
        <div className="flex flex-col md:flex-row gap-2">
          <input
            type="text"
            value={p.nlQuery}
            onChange={e => p.setNlQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') p.interpretNl() }}
            placeholder='🧠 Buscar en lenguaje natural: "playas de autos usados en Ciudad del Este"'
            className="flex-1 px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
          />
          <button
            onClick={p.interpretNl}
            disabled={p.nlBusy || !p.nlQuery.trim()}
            className="px-4 py-2 text-sm rounded-lg border border-primary-500/40 bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 transition-all shadow-neon disabled:opacity-40 whitespace-nowrap"
          >
            {p.nlBusy ? '⏳ Interpretando...' : '🧠 Interpretar'}
          </button>
          <button
            onClick={p.runSemantic}
            disabled={p.semanticBusy || !(p.nlQuery.trim() || p.search.trim())}
            title="Búsqueda semántica: embed la consulta y rankea por similitud (Fase 5)"
            className="px-4 py-2 text-sm rounded-lg border border-cyan-500/40 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 transition-all disabled:opacity-40 whitespace-nowrap"
          >
            {p.semanticBusy ? '⏳ Buscando...' : '🧬 Semántica'}
          </button>
        </div>
        {p.semanticErr && (
          <p className="text-xs text-alert-400 mt-2">{p.semanticErr}</p>
        )}
        {p.nlResult?.error && (
          <p className="text-xs text-alert-400 mt-2">{p.nlResult.error}</p>
        )}
        {p.nlResult && !p.nlResult.error && p.nlChips.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-[10px] text-gray-600 uppercase tracking-wider">Filtros detectados:</span>
            {p.nlChips.map(c => (
              <button
                key={c.key}
                onClick={() => p.toggleNlChip(c.key)}
                title={p.nlDisabled.includes(c.key) ? 'Quitado — click para volver a incluirlo' : 'Click para quitar este filtro'}
                className={`text-[11px] px-2 py-1 rounded border font-mono transition-colors ${p.nlDisabled.includes(c.key) ? 'border-bg-600 text-gray-600 line-through' : 'border-primary-500/40 text-primary-300 bg-primary-500/10 hover:bg-primary-500/20'}`}
              >
                {c.label} ✕
              </button>
            ))}
            <div className="flex items-center gap-2 ml-1">
              <button
                onClick={p.applyNl}
                className="text-[11px] px-3 py-1 rounded border border-primary-500/50 text-primary-300 bg-primary-500/20 hover:bg-primary-500/30 transition-colors"
              >
                Aplicar búsqueda
              </button>
              <button
                onClick={p.clearNl}
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
          value={p.search}
          onChange={e => p.setSearch(e.target.value)}
          placeholder="Buscar empresa, contacto, email..."
          className="flex-1 px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
        />
        <select value={p.filterStatus} onChange={e => p.setFilterStatus(e.target.value)} className="px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
          <option value="">Status: todos</option>
          <option value="new">new</option>
          <option value="contacted">contacted</option>
          <option value="qualified">qualified</option>
          <option value="proposal">proposal</option>
          <option value="won">won</option>
          <option value="lost">lost</option>
        </select>
        <select value={p.filterSource} onChange={e => p.setFilterSource(e.target.value)} className="px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
          <option value="">Fuente: todas</option>
          <option value="manual">manual</option>
          <option value="conciencia">conciencia</option>
          <option value="referral">referral</option>
          <option value="web">web</option>
          <option value="linkedin">linkedin</option>
          <option value="overpass">OSM (overpass)</option>
          <option value="import">import</option>
        </select>
        <select value={p.sort} onChange={e => p.setSort(e.target.value)} className="px-4 py-2 bg-bg-950 border border-bg-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
          <option value="newest">Orden: más nuevos</option>
          <option value="oldest">Orden: más viejos</option>
          <option value="score">Orden: mejor score</option>
          <option value="company">Orden: empresa A-Z</option>
        </select>
        <button
          onClick={() => p.setShowFilters(!p.showFilters)}
          className={`px-4 py-2 text-sm rounded-lg border transition-colors ${p.showFilters || p.activeFilters > 0 ? 'text-primary-400 border-primary-500/40 bg-primary-500/10' : 'text-gray-400 border-bg-600 hover:text-primary-300'}`}
        >
          ⚙ Filtros {p.activeFilters > 0 && `(${p.activeFilters})`}
        </button>
        {/* Cazar con los filtros activos, pegadito a ellos */}
        <button
          onClick={() => p.huntRun.mutate(huntCriteriaFromFilters({ filterSource: p.filterSource, filterRegion: p.filterRegion, filterSegment: p.filterSegment, filterIndustry: p.filterIndustry }) || undefined)}
          disabled={p.huntRun.isPending}
          title={
            huntCriteriaFromFilters({ filterSource: p.filterSource, filterRegion: p.filterRegion, filterSegment: p.filterSegment, filterIndustry: p.filterIndustry })
              ? 'Cazar leads nuevos que matcheen los filtros activos (fuente/región/segmento/sector)'
              : 'Sin filtros de caza: buscá con ⚙ Filtros (sector/región/segmento) para acotar, o usá Cazar TODO arriba'
          }
          className="px-4 py-2 text-sm rounded-lg border border-primary-500/40 bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 transition-all shadow-neon disabled:opacity-40 disabled:cursor-wait whitespace-nowrap"
        >
          {p.huntRun.isPending ? '⌛ Cazando...' : '🔎 Cazar leads con filtros'}
        </button>
      </div>

      {/* Búsquedas guardadas + listas (accesos rápidos) */}
      <div className="mt-3 pt-3 border-t border-bg-700 flex flex-wrap items-center gap-2">
        {/* Guardar búsqueda actual */}
        {p.showSaveSearch ? (
          <div className="flex items-center gap-2">
            <input
              value={p.saveSearchName}
              onChange={e => p.setSaveSearchName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && p.saveSearchName.trim()) p.saveSearch.mutate(p.saveSearchName.trim()) }}
              placeholder="Nombre de la búsqueda"
              autoFocus
              className="px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
            />
            <button onClick={() => p.saveSearchName.trim() && p.saveSearch.mutate(p.saveSearchName.trim())} disabled={!p.saveSearchName.trim() || p.saveSearch.isPending} className="px-3 py-1.5 text-xs rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">💾 Guardar</button>
            <button onClick={() => { p.setShowSaveSearch(false); p.setSaveSearchName('') }} className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-300">✕</button>
          </div>
        ) : (
          <button onClick={() => p.setShowSaveSearch(true)} className="px-3 py-1.5 text-xs rounded border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors" title="Guardar los filtros actuales como búsqueda">
            💾 Guardar búsqueda
          </button>
        )}

        {/* Búsquedas guardadas */}
        {p.savedSearches && p.savedSearches.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-[10px] text-gray-600 uppercase tracking-wider">Guardadas:</span>
            {p.savedSearches.map(s => (
              <span key={s.id} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-bg-600 text-gray-300 bg-bg-950">
                <button onClick={() => applySavedFilters(s, filterSetters)} title="Cargar esta búsqueda" className="hover:text-primary-300">
                  🔍 {s.name}
                </button>
                <button onClick={() => p.deleteSearch.mutate(s.id)} title="Borrar" className="text-gray-600 hover:text-alert-400">✕</button>
              </span>
            ))}
          </div>
        )}

        <span className="text-gray-800 mx-1">|</span>

        {/* Lista de leads */}
        <select
          value={p.filterList}
          onChange={e => p.setFilterList(e.target.value)}
          className="px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
          title="Filtrar por lista guardada"
        >
          <option value="">📁 Lista: todas</option>
          {p.leadLists?.map(l => (
            <option key={l.id} value={l.id}>{l.name} ({l.lead_count})</option>
          ))}
        </select>
        {p.filterList && (
          <button onClick={() => p.deleteList.mutate(p.filterList)} className="text-[10px] text-gray-600 hover:text-alert-400" title="Eliminar lista actual">🗑 lista</button>
        )}
        {p.showNewList ? (
          <div className="flex items-center gap-2">
            <input
              value={p.newListName}
              onChange={e => p.setNewListName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && p.newListName.trim()) p.createList.mutate(p.newListName.trim()) }}
              placeholder="Nombre de la lista"
              autoFocus
              className="px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
            />
            <button onClick={() => p.newListName.trim() && p.createList.mutate(p.newListName.trim())} disabled={!p.newListName.trim() || p.createList.isPending} className="px-3 py-1.5 text-xs rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40">+ Crear</button>
            <button onClick={() => { p.setShowNewList(false); p.setNewListName('') }} className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-300">✕</button>
          </div>
        ) : (
          <button onClick={() => p.setShowNewList(true)} className="px-3 py-1.5 text-xs rounded border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors" title="Crear una lista para agrupar leads (ej: seguimiento, región)">
            📁 + Nueva lista
          </button>
        )}
        {p.listMsg && <span className="text-[11px] text-primary-400">{p.listMsg}</span>}
      </div>

      {p.showFilters && (
        <div className="mt-4 pt-4 border-t border-bg-700 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wider">Región</label>
            <input
              list="region-list"
              value={p.filterRegion}
              onChange={e => p.setFilterRegion(e.target.value)}
              placeholder="Asunción, Luque, Lambaré..."
              className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
            />
            <datalist id="region-list">
              {p.regions?.map(r => <option key={r} value={r} />)}
            </datalist>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wider">Tamaño (segmento)</label>
            <select value={p.filterSegment} onChange={e => p.setFilterSegment(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
              <option value="">Todos</option>
              <option value="pyme">Pyme</option>
              <option value="mediana">Mediana</option>
              <option value="corporativo">Corporativo</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wider">Presencia online</label>
            <select value={p.filterOnline} onChange={e => p.setFilterOnline(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
              <option value="">Cualquiera</option>
              <option value="any">Con algún canal digital</option>
              <option value="website">Con website</option>
              <option value="email">Con email</option>
              <option value="phone">Con teléfono</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wider">Antigüedad</label>
            <select value={p.filterAge} onChange={e => p.setFilterAge(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
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
              value={p.filterIndustry}
              onChange={e => p.setFilterIndustry(e.target.value)}
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
              value={p.filterMinScore}
              onChange={e => p.setFilterMinScore(e.target.value)}
              placeholder="ej: 40"
              className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
            />
          </div>
          <div className="col-span-2 flex items-end gap-2">
            <button
              onClick={p.resetFilters}
              className="px-4 py-2 text-sm rounded-lg border border-bg-600 text-gray-400 hover:text-primary-300 hover:border-primary-500/50 transition-colors"
            >
              ⟲ Limpiar filtros
            </button>
            {huntCriteriaFromFilters({ filterSource: p.filterSource, filterRegion: p.filterRegion, filterSegment: p.filterSegment, filterIndustry: p.filterIndustry }) && (
              <button
                onClick={() => p.huntRun.mutate(huntCriteriaFromFilters({ filterSource: p.filterSource, filterRegion: p.filterRegion, filterSegment: p.filterSegment, filterIndustry: p.filterIndustry }) || undefined)}
                disabled={p.huntRun.isPending}
                className="px-4 py-2 text-sm rounded-lg border border-primary-500/40 bg-primary-500/15 text-primary-300 hover:bg-primary-500/25 transition-all disabled:opacity-40"
              >
                {p.huntRun.isPending ? '⌛ Cazando...' : `🔎 Cazar: ${[p.filterIndustry, p.filterSegment, p.filterRegion, p.filterSource].filter(Boolean).join(' · ')}`}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
