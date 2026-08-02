import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { useEffect, useRef, useState } from 'react'

interface LogEntry {
  timestamp: string
  level: string
  source: string
  message: string
}

const levelColors: Record<string, string> = {
  INFO: 'text-primary-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-alert-400',
  DEBUG: 'text-gray-500',
  CRITICAL: 'text-alert-400 font-bold',
}

export default function SystemLogs() {
  const [paused, setPaused] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { data: logs } = useQuery<LogEntry[]>({
    queryKey: ['system-logs'],
    queryFn: () => api.get('/api/v1/system/logs?limit=60').then(res => res.data),
    refetchInterval: paused ? false : 3000,
  })

  // Auto-scroll al fondo
  useEffect(() => {
    if (scrollRef.current && !paused) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, paused])

  return (
    <div className="hack-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
        <span className="text-xs text-gray-500 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse-glow inline-block"></span>
          // system_logs — tail -f
        </span>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-gray-700">{logs?.length || 0} lines</span>
          <button
            onClick={() => setPaused(!paused)}
            className={`text-[10px] px-2 py-0.5 rounded border ${
              paused
                ? 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10'
                : 'text-primary-400 border-primary-500/40 bg-primary-500/10'
            }`}
          >
            {paused ? '❚❚ paused' : '▶ live'}
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="bg-bg-950 p-3 h-48 md:h-64 overflow-y-auto font-mono text-[11px] leading-relaxed"
      >
        {logs && logs.length > 0 ? (
          logs.map((log, i) => (
            <div key={i} className="flex gap-2 border-b border-bg-900 py-0.5">
              <span className="text-gray-700 whitespace-nowrap">{log.timestamp}</span>
              <span className={`whitespace-nowrap ${levelColors[log.level] || 'text-gray-400'}`}>
                [{log.level}]
              </span>
              <span className="text-gray-600 whitespace-nowrap">{log.source}:</span>
              <span className="text-gray-300 break-all">{log.message}</span>
            </div>
          ))
        ) : (
          <p className="text-gray-700">$ waiting for logs...</p>
        )}
      </div>
    </div>
  )
}
