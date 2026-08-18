import { Link } from 'react-router-dom'

// Componentes de estado estándar (Fase 1 — spec §45 UI States)
// Reutilizables en todas las pantallas: loading / empty / error / restricted.

interface LoadingStateProps {
  label?: string
}

export function LoadingState({ label = 'Loading system...' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="w-8 h-8 border-2 border-bg-700 border-t-primary-400 rounded-full animate-spin" />
      <p className="text-sm text-primary-400 font-mono animate-blink">{label}</p>
    </div>
  )
}

interface EmptyStateProps {
  title: string
  message?: string
  actionLabel?: string
  onAction?: () => void
  to?: string
}

export function EmptyState({ title, message, actionLabel, onAction, to }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center border border-dashed border-bg-700 rounded-lg bg-bg-900/40">
      <span className="text-2xl mb-3">◇</span>
      <h3 className="text-sm font-semibold text-gray-300 tracking-wider">{title}</h3>
      {message && <p className="text-xs text-gray-600 mt-2 max-w-sm">{message}</p>}
      {actionLabel && to && (
        <Link
          to={to}
          className="mt-4 px-4 py-2 text-xs font-mono rounded-lg border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors"
        >
          ▸ {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-4 py-2 text-xs font-mono rounded-lg border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors"
        >
          ▸ {actionLabel}
        </button>
      )}
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
}

export function ErrorState({ title = 'SYSTEM_ERROR', message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center border border-alert-500/40 rounded-lg bg-alert-500/5">
      <span className="text-2xl mb-3">✕</span>
      <h3 className="text-sm font-semibold text-alert-400 tracking-wider">{title}</h3>
      {message && <p className="text-xs text-gray-500 mt-2 max-w-md font-mono">{message}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 px-4 py-2 text-xs font-mono rounded-lg border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 transition-colors"
        >
          ↻ retry
        </button>
      )}
    </div>
  )
}
