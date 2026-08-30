import { useQuery, useMutation } from '@tanstack/react-query'
import { agentsApi } from '../services/api'
import { useState } from 'react'

interface Agent {
  id: string
  name: string
  emoji: string
  role: string
  status: string
  capabilities: string[]
  autonomy_level: string
  runtime?: string
  provider?: string
  model?: string
  health_status?: string
  created_at: string
}

interface AgentFile {
  name: string
  content: string
}

interface RuntimeConfig {
  name: string
  type: string
  label: string
  enabled: boolean
  command: string
  cwd: string
  timeout_s: number
  online: boolean
}

const statusColors: Record<string, string> = {
  working: 'bg-primary-500/10 text-primary-400 border border-primary-500/50 animate-pulse-glow',
  idle: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
  paused: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  error: 'bg-alert-500/10 text-alert-400 border border-alert-500/50',
}

const autonomyLabels: Record<string, string> = {
  full: 'FULL_AUTONOMY',
  preview: 'PREVIEW_REQ',
  approval: 'NEEDS_APPROVAL',
}

const roleIcons: Record<string, string> = {
  dev: '👨‍💻',
  ops: '🚀',
  qa: '🧪',
  pm: '📊',
  rd: '📚',
  comms: '🎨',
  fin: '💰',
  admin: '🎯',
}

export default function Agents() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [runOutput, setRunOutput] = useState<string>('')
  const [runTask, setRunTask] = useState('')
  const [runRuntime, setRunRuntime] = useState('')
  const [running, setRunning] = useState(false)

  const { data: agents, isLoading } = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => agentsApi.getAll().then(res => res.data),
    refetchInterval: 15000,
  })

  // Fase 9: configs de runtimes (CLI externos habilitados por el dueño)
  const { data: runtimes } = useQuery<RuntimeConfig[]>({
    queryKey: ['agent-runtimes-config'],
    queryFn: () => agentsApi.runtimeConfigs().then(res => res.data),
  })

  const { data: agentFiles } = useQuery<AgentFile[]>({
    queryKey: ['agent-files', selectedId],
    queryFn: () => agentsApi.getFiles(selectedId!).then(res => res.data),
    enabled: !!selectedId,
  })

  const { data: agentActivity } = useQuery({
    queryKey: ['agent-activity', selectedId],
    queryFn: () => agentsApi.getActivity(selectedId!).then(res => res.data),
    enabled: !!selectedId,
    refetchInterval: 15000,
  })

  const runMutation = useMutation({
    mutationFn: ({ id, task, runtime }: { id: string, task: string, runtime?: string }) =>
      agentsApi.run(id, { task_text: task, runtime: runtime || undefined }),
    onSuccess: (res) => {
      const data = res.data
      if (data.status === 'completed') {
        setRunOutput(`$ agent.execute → COMPLETED ${data.simulated ? '(SIMULADO)' : `(runtime: ${data.runtime} · model: ${data.model})`}${data.duration_ms ? ` · ${data.duration_ms}ms` : ''}${data.usage?.cost_estimate_usd ? ` · ~$${data.usage.cost_estimate_usd}` : ''}\n\n${data.output}`)
      } else {
        setRunOutput(`$ agent.execute → FAILED\n\n${data.error}`)
      }
    },
    onError: (err: any) => {
      setRunOutput(`$ agent.execute → ERROR\n\n${err.response?.data?.detail || err.message}`)
    },
  })

  if (isLoading) {
    return <div className="text-primary-400 animate-blink">Loading agents...</div>
  }

  const selected = agents?.find(a => a.id === selectedId) || agents?.[0]

  const handleRun = () => {
    if (!selected || !runTask.trim()) return
    setRunning(true)
    setRunOutput('$ agent.execute --task "' + runTask.slice(0, 60) + '"...')
    runMutation.mutate(
      { id: selected.id, task: runTask.trim(), runtime: runRuntime || undefined },
      {
        onSettled: () => setRunning(false),
      }
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// AGENTS</h1>
        <span className="text-xs text-gray-600 font-mono">$ ps aux | grep agent</span>
      </div>

      {/* Grid de agentes */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {agents?.map((agent) => (
          <button
            key={agent.id}
            onClick={() => setSelectedId(agent.id)}
            className={`hack-card p-4 text-left transition-all hover:border-primary-500/50 ${
              selected?.id === agent.id ? 'border-primary-500/60 shadow-neon' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-3xl">{agent.emoji || roleIcons[agent.role]}</span>
              <span className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${statusColors[agent.status]}`}>
                {agent.status}
              </span>
            </div>
            <p className="font-bold text-gray-200">{agent.name}</p>
            <p className="text-xs text-primary-500 mt-1">{autonomyLabels[agent.autonomy_level] || agent.autonomy_level}</p>
            <div className="mt-1.5 flex items-center gap-1 flex-wrap">
              <span className="px-1.5 py-0.5 bg-bg-800 text-cyan-400 rounded text-[10px] font-mono">⛭ {agent.runtime || 'generic'}</span>
              <span className="px-1.5 py-0.5 bg-bg-800 text-purple-400 rounded text-[10px] font-mono">{agent.provider || 'deepseek'}</span>
            </div>
            {agent.model && <p className="text-[10px] text-gray-600 mt-1 font-mono truncate">{agent.model}</p>}
            <div className="mt-2 flex flex-wrap gap-1">
              {agent.capabilities?.slice(0, 3).map((cap: string) => (
                <span key={cap} className="px-1.5 py-0.5 bg-bg-800 text-gray-500 rounded text-[10px]">
                  {cap}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Consola de ejecución */}
          <div className="hack-card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
              <span className="text-xs text-gray-500">
                {selected.emoji} {selected.name} — execute console
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-cyan-400">⛭ {selected.runtime || 'generic'}</span>
                <span className="text-[10px] font-mono text-purple-400">{selected.provider || 'deepseek'}</span>
                <span className="text-primary-500 animate-blink">▊</span>
              </div>
            </div>
            <div className="p-4">
              <label className="block text-sm font-medium text-primary-400 mb-2">
                $ task para {selected.name}
              </label>
              <textarea
                value={runTask}
                onChange={e => setRunTask(e.target.value)}
                rows={3}
                className="hack-input"
                placeholder={`Ej: Analiza el backlog y sugiere prioridades...`}
              />
              {/* Fase 9: selector de runtime externo (CLI habilitados por el dueño) */}
              <div className="mt-2 flex items-center gap-2">
                <label className="text-[10px] text-gray-600 uppercase tracking-wider whitespace-nowrap">Runtime</label>
                <select
                  value={runRuntime}
                  onChange={e => setRunRuntime(e.target.value)}
                  className="flex-1 px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50"
                  title="Override de runtime: motor embebido o CLI externo (claude_code/codex/opencode/openclaw)"
                >
                  <option value="">Motor embebido (default del agente)</option>
                  {(runtimes || [])
                    .filter(r => r.enabled && r.type !== 'internal')
                    .map(r => (
                      <option key={r.name} value={r.name}>
                        {r.label} {r.online ? '' : '⚠ (no instalado)'}
                      </option>
                    ))}
                </select>
              </div>
              <button
                onClick={handleRun}
                disabled={running || !runTask.trim()}
                className="mt-3 w-full px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all"
              >
                {running ? 'EXECUTING...' : `[ EJECUTAR ${selected.name.toUpperCase()} ]`}
              </button>

              <div className="mt-4 bg-bg-950 border border-bg-800 rounded-lg p-3 min-h-[200px] max-h-[300px] overflow-y-auto">
                <pre className="text-xs text-primary-400 whitespace-pre-wrap font-mono">
                  {runOutput || '$ agent.idle\n\n> Selecciona un agente y dale una tarea para ejecutarlo con DeepSeek.\n> (El SOUL.md del agente se usa como system prompt)'}
                </pre>
              </div>
            </div>
          </div>

          {/* SOUL.md + actividad */}
          <div className="space-y-6">
            <div className="hack-card overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
                <span className="text-xs text-gray-500">// {selected.name.toLowerCase()}/SOUL.md</span>
                <span className="text-xs text-gray-700">{agentFiles?.length || 0} files</span>
              </div>
              <div className="p-4 max-h-[300px] overflow-y-auto">
                {agentFiles && agentFiles.length > 0 ? (
                  <div className="space-y-4">
                    {agentFiles.map((file) => (
                      <div key={file.name}>
                        <p className="text-xs text-primary-500 mb-2"># {file.name}</p>
                        <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono border-l-2 border-bg-700 pl-3">
                          {file.content.slice(0, 1500)}
                          {file.content.length > 1500 ? '\n... (truncado)' : ''}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-600 text-sm">No MD files found for this agent</p>
                )}
              </div>
            </div>

            <div className="hack-card overflow-hidden">
              <div className="px-4 py-2 bg-bg-950 border-b border-bg-700">
                <span className="text-xs text-gray-500">// activity_log</span>
              </div>
              <div className="p-4 max-h-[200px] overflow-y-auto">
                {agentActivity && agentActivity.length > 0 ? (
                  <ul className="space-y-2">
                    {agentActivity.slice(0, 8).map((act: any) => (
                      <li key={act.id} className="text-xs text-gray-500 border-b border-bg-800 pb-2">
                        <span className="text-primary-500">▸</span> {act.description}
                        <span className="block text-gray-700 mt-1">
                          {new Date(act.created_at).toLocaleString()}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-600 text-sm">No activity yet</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
