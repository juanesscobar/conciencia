/* Tabla de leads + banner semántico (extraído de Leads.tsx, Fase 7). */

import { Lead, scoreColor, sourceLabels, statusColors, fmtDateTime } from './types'

export interface LeadTableProps {
  leads: Lead[]
  total: number
  semanticRes: { items: Lead[]; query: string } | null
  onClearSemantic: () => void
  onSelect: (lead: Lead) => void
  onStatusChange: (lead: Lead, status: string) => void
  onEnrichWebsite: (lead: Lead) => void
  onEnrichAi: (id: string) => void
  enrichWebsitePending: boolean
  enrichAiPending: boolean
}

export function LeadTable(p: LeadTableProps) {
  const rows = p.semanticRes ? p.semanticRes.items : p.leads

  return (
    <div className="bg-bg-900 border border-bg-700 rounded-lg overflow-hidden">
      {p.semanticRes && (
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-cyan-500/30 bg-cyan-500/5">
          <p className="text-xs text-cyan-300">
            🧬 Resultados semánticos para «{p.semanticRes.query}» — {p.semanticRes.items.length} matches
          </p>
          <button
            onClick={p.onClearSemantic}
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
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                  Sin leads con esos filtros — apretá «Cazar leads ahora» o importá un CSV
                </td>
              </tr>
            )}
            {rows.map(lead => (
              <tr
                key={lead.id}
                className="border-b border-bg-800 hover:bg-bg-800/50 transition-colors cursor-pointer"
                onClick={() => p.onSelect(lead)}
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
                    onChange={e => p.onStatusChange(lead, e.target.value)}
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
                      onClick={() => p.onEnrichWebsite(lead)}
                      disabled={p.enrichWebsitePending || !lead.website}
                      title="Rastrear website (email/tel)"
                      className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 hover:text-primary-300 transition-colors disabled:opacity-30"
                    >
                      🌐
                    </button>
                    <button
                      onClick={() => p.onEnrichAi(lead.id)}
                      disabled={p.enrichAiPending}
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
        {p.semanticRes ? p.semanticRes.items.length : p.total} leads{p.semanticRes ? ' (semánticos)' : ` · ${p.leads.filter(l => l.status === 'new').length} nuevos en esta vista`}
      </div>
    </div>
  )
}
