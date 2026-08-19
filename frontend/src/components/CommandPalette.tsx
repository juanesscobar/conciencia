import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface Command {
  id: string
  label: string
  hint?: string
  icon?: string
  action: () => void
  keywords?: string
}

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  onAskConciencia: (query?: string) => void
}

const COMMANDS: { group: string; items: { label: string; icon?: string; to?: string; hint?: string; keywords?: string; custom?: 'ask' }[] }[] = [
  {
    group: 'OPERATE',
    items: [
      { label: 'Mission Control', to: '/', icon: '◉' },
      { label: 'Missions', to: '/projects', icon: '▣' },
      { label: 'Tasks', to: '/tasks', icon: '☑' },
      { label: 'Approvals', to: '/approvals', icon: '⚠' },
      { label: 'Leads', to: '/leads', icon: '◎' },
      { label: 'Reports', to: '/reports', icon: '▤' },
    ],
  },
  {
    group: 'BUILD',
    items: [
      { label: 'Agents', to: '/agents', icon: '◈' },
      { label: 'Workflows', to: '/workflows', icon: '⇄' },
      { label: 'Context & Memory', to: '/context', icon: '◍' },
    ],
  },
  {
    group: 'CONTROL',
    items: [
      { label: 'Governance', to: '/governance', icon: '⚖' },
      { label: 'Traces', to: '/traces', icon: '≡' },
      { label: 'Costs', to: '/costs', icon: '$' },
      { label: 'Audit', to: '/audit', icon: '☰' },
    ],
  },
  {
    group: 'SYSTEM',
    items: [
      { label: 'Settings', to: '/settings', icon: '⚙' },
      { label: 'Ask Conciencia', icon: '✦', custom: 'ask', hint: 'preguntá sobre tu sistema (⌘K luego Enter)' },
    ],
  },
]

export default function CommandPalette({ open, onClose, onAskConciencia }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (open) {
      setQuery('')
      setIndex(0)
    }
  }, [open])

  const commands = useMemo<Command[]>(() => {
    const q = query.trim().toLowerCase()
    const out: Command[] = []
    for (const group of COMMANDS) {
      for (const item of group.items) {
        const label = item.label.toLowerCase()
        const kw = (item.keywords || '').toLowerCase()
        if (!q || label.includes(q) || kw.includes(q)) {
          out.push({
            id: `${group.group}-${item.label}`,
            label: item.label,
            icon: item.icon,
            hint: item.hint,
            action: () => {
              if (item.custom === 'ask') onAskConciencia(query)
              else if (item.to) navigate(item.to)
              onClose()
            },
          })
        }
      }
    }
    return out
  }, [query, navigate, onClose, onAskConciencia])

  useEffect(() => {
    setIndex(0)
  }, [query])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[15vh] px-4">
      <div className="fixed inset-0 bg-black/70" onClick={onClose} />
      <div className="relative w-full max-w-xl bg-bg-900 border border-primary-500/30 rounded-xl shadow-neon overflow-hidden">
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-bg-700">
          <span className="text-primary-400 text-sm font-mono">⌘K</span>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setIndex(i => Math.min(i + 1, commands.length - 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setIndex(i => Math.max(i - 1, 0)) }
              if (e.key === 'Enter' && commands[index]) commands[index].action()
              if (e.key === 'Escape') onClose()
            }}
            placeholder="Buscar o ejecutar... (ej. approvals, costs, ¿qué falló?)"
            autoFocus
            className="flex-1 bg-transparent text-sm text-gray-200 focus:outline-none placeholder:text-gray-600"
          />
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto p-2">
          {commands.length === 0 ? (
            <p className="text-xs text-gray-600 px-3 py-6 text-center">Sin comandos para «{query}»</p>
          ) : (
            commands.map((c, i) => (
              <button
                key={c.id}
                onClick={c.action}
                onMouseEnter={() => setIndex(i)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${i === index ? 'bg-primary-500/10 border border-primary-500/30' : 'border border-transparent'}`}
              >
                <span className="text-primary-400 text-sm">{c.icon || '▸'}</span>
                <span className="text-sm text-gray-200 flex-1">{c.label}</span>
                {c.hint && <span className="text-[10px] text-gray-600">{c.hint}</span>}
              </button>
            ))
          )}
        </div>

        <div className="px-4 py-2 border-t border-bg-700 text-[10px] text-gray-700 flex gap-4">
          <span>↑↓ navegar</span><span>↵ ejecutar</span><span>esc cerrar</span>
        </div>
      </div>
    </div>
  )
}
