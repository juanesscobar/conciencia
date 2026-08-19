import { Link, useLocation } from 'react-router-dom'
import { ReactNode, useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import CommandPalette from './CommandPalette'
import AskConciencia from './AskConciencia'

interface LayoutProps {
  children: ReactNode
}

// Navegación agrupada (Fase 1 — spec §11): solo rutas existentes, sin secciones vacías
const navigation = [
  {
    section: 'OPERATE',
    items: [
      { name: 'Mission Control', href: '/', icon: '◉' },
      { name: 'Missions', href: '/projects', icon: '▣' },
      { name: 'Tasks', href: '/tasks', icon: '☑' },
      { name: 'Approvals', href: '/approvals', icon: '⚠' },
      { name: 'Leads', href: '/leads', icon: '◎' },
      { name: 'Reports', href: '/reports', icon: '▤' },
    ],
  },
  {
    section: 'BUILD',
    items: [
      { name: 'Agents', href: '/agents', icon: '◈' },
      { name: 'Workflows', href: '/workflows', icon: '⇄' },
      { name: 'Context', href: '/context', icon: '◍' },
    ],
  },
  {
    section: 'CONTROL',
    items: [
      { name: 'Governance', href: '/governance', icon: '⚖' },
      { name: 'Traces', href: '/traces', icon: '≡' },
      { name: 'Costs', href: '/costs', icon: '$' },
      { name: 'Audit', href: '/audit', icon: '☰' },
    ],
  },
  {
    section: 'SYSTEM',
    items: [{ name: 'Settings', href: '/settings', icon: '⚙' }],
  },
]

function TerminalHeader() {
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
      <div className="flex items-center gap-2">
        <span className="w-3 h-3 rounded-full bg-alert-500 inline-block"></span>
        <span className="w-3 h-3 rounded-full bg-yellow-500 inline-block"></span>
        <span className="w-3 h-3 rounded-full bg-green-500 inline-block"></span>
        <span className="ml-3 text-xs text-gray-500">iron@conciencia-platform:~$</span>
      </div>
      <span className="text-xs text-primary-500 animate-blink">▊</span>
    </div>
  )
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [assistantQuery, setAssistantQuery] = useState<string | undefined>(undefined)

  const closeSidebar = () => setSidebarOpen(false)

  // Command Bar global: ⌘K / Ctrl+K (spec §26/§32)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen(p => !p)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const openAssistant = (query?: string) => {
    setAssistantQuery(query)
    setAssistantOpen(true)
  }

  return (
    <div className="min-h-screen bg-bg-950 scanlines">
      {/* Overlay mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-30 md:hidden"
          onClick={closeSidebar}
        ></div>
      )}

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 w-64 bg-bg-900 border-r border-bg-700 z-40 transform transition-transform duration-200 md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <TerminalHeader />

        <div className="flex items-center h-14 px-6 border-b border-bg-800">
          <span className="text-lg font-bold text-primary-400 tracking-wider">◉ CONCIENCIA PLATFORM</span>
        </div>

        <nav className="p-4 space-y-4">
          {navigation.map((group) => (
            <div key={group.section}>
              <p className="px-4 mb-1 text-[10px] font-semibold tracking-[0.2em] text-gray-700">
                // {group.section}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={closeSidebar}
                      aria-current={isActive ? 'page' : undefined}
                      className={`flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                        isActive
                          ? 'bg-bg-800 text-primary-400 border border-primary-500/30 shadow-neon'
                          : 'text-gray-500 border border-transparent hover:bg-bg-800 hover:text-primary-300'
                      }`}
                    >
                      <span className="mr-3">{item.icon}</span>
                      {item.name}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}

          {/* Command Center (spec §64: GUI → Observe · Command Bar → Act · Ask → Understand) */}
          <div>
            <p className="px-4 mb-1 text-[10px] font-semibold tracking-[0.2em] text-gray-700">// COMMAND CENTER</p>
            <div className="space-y-1">
              <button
                onClick={() => setPaletteOpen(true)}
                className="w-full flex items-center px-4 py-2 text-sm font-medium rounded-lg text-gray-500 border border-transparent hover:bg-bg-800 hover:text-primary-300 transition-all"
              >
                <span className="mr-3">⌘</span>
                Command Bar
                <span className="ml-auto text-[10px] text-gray-700 border border-bg-700 rounded px-1.5 py-0.5">⌘K</span>
              </button>
              <button
                onClick={() => openAssistant()}
                className="w-full flex items-center px-4 py-2 text-sm font-medium rounded-lg text-gray-500 border border-transparent hover:bg-bg-800 hover:text-primary-300 transition-all"
              >
                <span className="mr-3">✦</span>
                Ask Conciencia
              </button>
            </div>
          </div>
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-bg-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-bg-800 border border-primary-500/50 flex items-center justify-center text-primary-400 font-bold text-sm shadow-neon">
                {user?.display_name?.charAt(0) || '?'}
              </div>
              <div className="ml-3 min-w-0">
                <p className="text-sm font-medium text-gray-200 truncate">{user?.display_name || user?.username}</p>
                <p className="text-xs text-primary-500">{user?.role || 'operator'}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="text-xs text-gray-600 hover:text-alert-400 transition-colors"
              title="Sign out"
            >
              ⏻
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="md:pl-64">
        {/* Topbar mobile */}
        <div className="md:hidden sticky top-0 z-20 bg-bg-900/95 backdrop-blur border-b border-bg-700 px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-primary-400 text-xl p-1 hover:text-primary-300"
            aria-label="Open menu"
          >
            ☰
          </button>
          <span className="text-sm font-bold text-primary-400 tracking-wider">◉ CP</span>
          <span className="text-primary-500 animate-blink text-xs">▊</span>
        </div>

        <main className="p-4 md:p-8">
          {children}
        </main>
      </div>

      {/* Command Center global */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onAskConciencia={(q) => { setPaletteOpen(false); openAssistant(q) }}
      />
      {assistantOpen && <AskConciencia key={assistantQuery || 'default'} initialQuery={assistantQuery} onClose={() => setAssistantOpen(false)} />}
    </div>
  )
}
