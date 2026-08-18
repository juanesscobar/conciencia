import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, workflowsApi } from '../services/api'
import AgentOffice from '../components/AgentOffice'
import UserMemory from '../components/UserMemory'
import SystemLogs from '../components/SystemLogs'
import { LoadingState, EmptyState, ErrorState } from '../components/StateViews'

interface Metric {
  id: string
  name: string
  value: number
  target: number | null
  unit: string
  category: string
}

interface Activity {
  id: string
  type: string
  description: string
  created_at: string
  project_id: string | null
}

interface Task {
  id: string
  title: string
  status: string
  priority: string
}

interface Agent {
  id: string
  name: string
  emoji: string
  role: string
  status: string
}

interface Project {
  id: string
  name: string
  description: string
  status: string
  priority: string
}

// LEVEL 1 — WHAT MATTERS NOW: System Operational + status crítico (spec §12)
function StatusBar({
  operational,
  agentsTotal,
  agentsWorking,
  activeMissions,
  openTasks,
  approvals,
  failedTasks,
}: {
  operational: boolean
  agentsTotal: number
  agentsWorking: number
  activeMissions: number
  openTasks: number
  approvals: number
  failedTasks: number
}) {
  const status = operational ? (
    <span className="flex items-center gap-2 text-green-400">
      <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse inline-block"></span>
      SYSTEM_OPERATIONAL
    </span>
  ) : (
    <span className="flex items-center gap-2 text-alert-400">
      <span className="w-2 h-2 rounded-full bg-alert-500 inline-block"></span>
      SYSTEM_DEGRADED
    </span>
  )

  return (
    <div className="hack-card p-4 mb-6">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
        <div className="text-sm font-mono">{status}</div>
        <Stat label="ACTIVE_MISSIONS" value={activeMissions} to="/projects" />
        <Stat label="AGENTS_WORKING" value={`${agentsWorking}/${agentsTotal}`} to="/agents" alert={agentsWorking === 0 && agentsTotal > 0} />
        <Stat label="OPEN_TASKS" value={openTasks} to="/tasks" />
        <Stat
          label="APPROVALS"
          value={approvals}
          to="/workflows"
          alert={approvals > 0}
          pulse={approvals > 0}
        />
        <Stat label="FAILED_TASKS" value={failedTasks} to="/tasks" alert={failedTasks > 0} />
      </div>
    </div>
  )
}

function Stat({ label, value, to, alert, pulse }: { label: string; value: string | number; to: string; alert?: boolean; pulse?: boolean }) {
  return (
    <Link
      to={to}
      className={`group flex flex-col ${alert ? 'text-alert-400' : 'text-gray-300'} hover:text-primary-400 transition-colors`}
    >
      <span className="text-[10px] font-medium tracking-wider text-gray-600 group-hover:text-primary-500">
        {label}
      </span>
      <span className={`text-lg font-bold font-mono ${pulse ? 'animate-blink' : ''}`}>{value}</span>
    </Link>
  )
}

export default function Dashboard() {
  const projects = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/api/v1/projects/').then(res => res.data as Project[]),
  })

  const tasks = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: () => api.get('/api/v1/tasks/').then(res => res.data),
  })

  const metrics = useQuery<Metric[]>({
    queryKey: ['metrics'],
    queryFn: () => api.get('/api/v1/metrics/').then(res => res.data),
  })

  const activities = useQuery<Activity[]>({
    queryKey: ['activities'],
    queryFn: () => api.get('/api/v1/activities/').then(res => res.data),
  })

  const agents = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => api.get('/api/v1/agents/').then(res => res.data),
  })

  const pendingApprovals = useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: () => workflowsApi.pendingApprovals().then(res => res.data as unknown[]),
  })

  const queries = [projects, tasks, metrics, activities, agents, pendingApprovals]
  const isLoading = queries.some(q => q.isLoading)
  const hasError = queries.some(q => q.isError)
  const retryAll = () => queries.forEach(q => q.refetch())

  if (isLoading) {
    return <LoadingState label="Booting Mission Control..." />
  }

  if (hasError) {
    return (
      <ErrorState
        message="One or more Control Plane endpoints failed to respond."
        onRetry={retryAll}
      />
    )
  }

  const allProjects = projects.data || []
  const allTasks = tasks.data || []
  const allAgents = agents.data || []
  const approvalsCount = pendingApprovals.data?.length || 0

  const activeMissions = allProjects.filter((p: Project) => p.status === 'active')
  const openTasks = allTasks.filter((t: Task) => t.status !== 'done' && t.status !== 'cancelled').length
  const failedTasks = allTasks.filter((t: Task) => t.status === 'failed').length
  const agentsWorking = allAgents.filter((a: Agent) => a.status === 'working').length

  const recentActivities = (activities.data || []).slice(0, 10)

  return (
    <div>
      {/* HEADER */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// MISSION_CONTROL</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ status --live · control plane overview</p>
        </div>
        <span className="text-xs text-gray-600 font-mono">iron@conciencia:~$ uptime</span>
      </div>

      {/* LEVEL 1 — STATUS */}
      <StatusBar
        operational={!hasError}
        agentsTotal={allAgents.length}
        agentsWorking={agentsWorking}
        activeMissions={activeMissions.length}
        openTasks={openTasks}
        approvals={approvalsCount}
        failedTasks={failedTasks}
      />

      {/* LEVEL 2 — WHAT IS HAPPENING: agentes trabajando */}
      <div className="mb-8">
        <SectionTitle label="AGENTS_WORKING" />
        <AgentOffice />
      </div>

      {/* LEVEL 2 — métricas + actividad */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="hack-card p-6">
          <SectionTitle label="METRICS" />
          {metrics.data && metrics.data.length > 0 ? (
            <div className="space-y-4">
              {metrics.data.map((metric: Metric) => (
                <div key={metric.id}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-gray-300">{metric.name}</span>
                    <span className="text-sm text-primary-500">
                      {metric.value} / {metric.target || 'N/A'} {metric.unit}
                    </span>
                  </div>
                  <div className="w-full bg-bg-800 rounded-full h-2 border border-bg-700">
                    <div
                      className={`h-2 rounded-full ${metric.target && metric.value >= metric.target ? 'bg-primary-500 shadow-neon' : 'bg-neon-500'}`}
                      style={{ width: metric.target ? `${Math.min(100, (metric.value / metric.target) * 100)}%` : `${Math.min(100, metric.value)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600">No metrics available</p>
          )}
        </div>

        <div className="hack-card p-6">
          <SectionTitle label="ACTIVITY_LOG" />
          {recentActivities.length > 0 ? (
            <ul className="space-y-3">
              {recentActivities.map((activity: Activity) => (
                <li key={activity.id} className="border-b border-bg-800 pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    <ActivityIcon type={activity.type} />
                    <span className="text-sm text-gray-300">{activity.description}</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {new Date(activity.created_at).toLocaleString()}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-600">No recent activity</p>
          )}
        </div>
      </div>

      {/* LEVEL 2 — misiones activas + memoria */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 hack-card p-6">
          <SectionTitle label="ACTIVE_MISSIONS" />
          {allProjects.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {allProjects.map((project: Project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="border border-bg-700 rounded-lg p-4 hover:border-primary-500/50 transition-colors"
                >
                  <h3 className="font-medium text-gray-200">{project.name}</h3>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">{project.description}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <StatusBadge status={project.status} />
                    <PriorityBadge priority={project.priority} />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No missions yet"
              message="Create a project to start executing autonomous missions."
              actionLabel="create mission"
              to="/projects"
            />
          )}
        </div>

        {/* 🧠 MEMORIA DE USUARIO */}
        <div>
          <UserMemory />
        </div>
      </div>

      {/* LEVEL 3 — TECHNICAL: logs del sistema */}
      <div className="mb-8 opacity-80">
        <SectionTitle label="TECHNICAL // SYSTEM_LOGS" muted />
        <SystemLogs />
      </div>
    </div>
  )
}

function SectionTitle({ label, muted }: { label: string; muted?: boolean }) {
  return (
    <h2 className={`text-sm font-semibold tracking-wider mb-4 ${muted ? 'text-gray-600' : 'text-primary-400'}`}>
      // {label}
    </h2>
  )
}

function ActivityIcon({ type }: { type: string }) {
  const icons: Record<string, string> = {
    commit: '💾',
    pr: '🔀',
    issue: '🐛',
    task_change: '✓',
    deploy: '▲',
    release: '▣',
    agent_action: '◈',
  }
  return <span>{icons[type] || '▸'}</span>
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
    paused: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
    archived: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
    completed: 'bg-neon-500/10 text-neon-400 border border-neon-500/40',
  }
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${colors[status] || colors.active}`}>
      {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    p0: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
    p1: 'bg-orange-500/10 text-orange-400 border border-orange-500/40',
    p2: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
    p3: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
  }
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${colors[priority] || colors.p3}`}>
      {priority.toUpperCase()}
    </span>
  )
}
