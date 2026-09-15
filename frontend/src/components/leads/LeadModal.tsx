/* Modal de creación de lead (extraído de Leads.tsx, Fase 7). */

import { useState } from 'react'

export function LeadModal({ onClose, onCreate }: { onClose: () => void; onCreate: (data: any) => void }) {
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
