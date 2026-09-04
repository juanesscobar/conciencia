/* Pipeline kanban (mini CRM) — extraído de Leads.tsx (Fase 7). */

import { Lead, scoreColor } from './types'

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

export function PipelineBoard({ leads, onSelect, onMove, busy }: {
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
