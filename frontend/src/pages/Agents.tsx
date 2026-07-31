import { useQuery } from '@tanstack/react-query'
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
  created_at: string
}

const statusColors: Record<string, string> = {
  working: 'bg-green-100 text-green-800',
  idle: 'bg-yellow-100 text-yellow-800',
  paused: 'bg-gray-100 text-gray-800',
  error: 'bg-red-100 text-red-800',
}

const autonomyLabels: Record<string, string> = {
  full: '🤖 Full Autonomy',
  preview: '👁️ Preview Required',
  approval: '✅ Needs Approval',
}

export default function Agents() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { data: agents, isLoading } = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => agentsApi.getAll().then(res => res.data),
  })

  const { data: agentTasks } = useQuery({
    queryKey: ['agent-tasks', selectedId],
    queryFn: () => agentsApi.getTasks(selectedId!).then(res => res.data),
    enabled: !!selectedId,
  })

  if (isLoading) {
    return <div className="text-gray-500">Loading agents...</div>
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Agents</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents?.map((agent) => (
          <div
            key={agent.id}
            onClick={() => setSelectedId(selectedId === agent.id ? null : agent.id)}
            className={`bg-white rounded-lg shadow p-6 cursor-pointer transition-all hover:shadow-md ${
              selectedId === agent.id ? 'ring-2 ring-primary-500' : ''
            }`}
          >
            <div className="flex items-center">
              <span className="text-3xl mr-3">{agent.emoji}</span>
              <div>
                <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                <p className="text-sm text-gray-500 capitalize">{agent.role}</p>
              </div>
            </div>

            <div className="mt-3 flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${statusColors[agent.status] || 'bg-gray-100 text-gray-800'}`}>
                {agent.status}
              </span>
              <span className="text-xs text-gray-400">{autonomyLabels[agent.autonomy_level] || agent.autonomy_level}</span>
            </div>

            {agent.capabilities?.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {agent.capabilities.map((cap: string) => (
                  <span key={cap} className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">
                    {cap.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}

            {selectedId === agent.id && agentTasks && agentTasks.length > 0 && (
              <div className="mt-4 border-t pt-3">
                <p className="text-xs font-medium text-gray-500 mb-2">Current Tasks:</p>
                {agentTasks.slice(0, 3).map((t: any) => (
                  <div key={t.id} className="text-xs text-gray-600 truncate">
                    {t.title}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
