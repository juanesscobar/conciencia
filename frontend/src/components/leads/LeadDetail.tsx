/* Modal de detalle de lead con pipeline completo (extraído de Leads.tsx, Fase 7). */

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { leadsApi } from '../../services/api'
import { Lead, LeadEvent, LeadProposal, LeadList, eventLabels, proposalStatusStyle, scoreColor, sourceLabels, statusColors, fmtDateTime } from './types'

export function LeadDetail({ lead, onClose, onAction, onEnrichWebsite, onEnrichAi }: {
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
