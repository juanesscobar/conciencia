import { Link, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: '◉' },
  { name: 'Projects', href: '/projects', icon: '▣' },
  { name: 'Tasks', href: '/tasks', icon: '☑' },
  { name: 'Agents', href: '/agents', icon: '◈' },
]

function TerminalHeader() {
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
      <div className="flex items-center gap-2">
        <span className="w-3 h-3 rounded-full bg-alert-500 inline-block"></span>
        <span className="w-3 h-3 rounded-full bg-yellow-500 inline-block"></span>
        <span className="w-3 h-3 rounded-full bg-green-500 inline-block"></span>
        <span className="ml-3 text-xs text-gray-500">iron@mission-control:~$</span>
      </div>
      <span className="text-xs text-primary-500 animate-blink">▊</span>
    </div>
  )
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-bg-950 scanlines">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-bg-900 border-r border-bg-700">
        <TerminalHeader />

        <div className="flex items-center h-14 px-6 border-b border-bg-800">
          <span className="text-lg font-bold text-primary-400 tracking-wider">◉ MISSION CONTROL</span>
        </div>

        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
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
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-bg-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-bg-800 border border-primary-500/50 flex items-center justify-center text-primary-400 font-bold text-sm shadow-neon">
                {user?.display_name?.charAt(0) || '?'}
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-200">{user?.display_name || user?.username}</p>
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
      <div className="pl-64">
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
