import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import AgentOffice from '../components/AgentOffice'
import UserMemory from '../components/UserMemory'
import DeepSeekSettings from '../components/DeepSeekSettings'

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

export default function Dashboard() {
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/api/v1/projects/').then(res => res.data)
  })

  const { data: tasks } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: () => api.get('/api/v1/tasks/').then(res => res.data)
  })

  const { data: metrics } = useQuery<Metric[]>({
    queryKey: ['metrics'],
    queryFn: () => api.get('/api/v1/metrics/').then(res => res.data)
  })

  const { data: activities } = useQuery<Activity[]>({
    queryKey: ['activities'],
    queryFn: () => api.get('/api/v1/activities/').then(res => res.data)
  })

  if (projectsLoading) {
    return <div className="text-primary-400 animate-blink">Loading system...</div>
  }

  const activeProjects = projects?.filter((p: any) => p.status === 'active').length || 0
  const openTasks = tasks?.filter((t: Task) => t.status !== 'done' && t.status !== 'cancelled').length || 0
  const completedTasks = tasks?.filter((t: Task) => t.status === 'done').length || 0
  const totalTasks = tasks?.length || 0

  const recentActivities = activities?.slice(0, 10) || []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// DASHBOARD</h1>
        <span className="text-xs text-gray-600 font-mono">$ uptime --live</span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard title="ACTIVE_PROJECTS" value={activeProjects} icon="▣" color="green" />
        <StatCard title="TOTAL_TASKS" value={totalTasks} icon="☑" color="cyan" />
        <StatCard title="COMPLETED" value={completedTasks} icon="✓" color="purple" />
        <StatCard title="OPEN_TASKS" value={openTasks} icon="◌" color="orange" />
      </div>

      {/* ⚙️ CONFIGURACIÓN DEL MOTOR IA */}
      <div className="mb-8">
        <DeepSeekSettings />
      </div>

      {/* 🏢 OFICINA VIRTUAL - Agentes trabajando */}
      <div className="mb-8">
        <AgentOffice />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="hack-card p-6">
          <h2 className="text-lg font-semibold text-primary-400 mb-4">// METRICS</h2>
          {metrics && metrics.length > 0 ? (
            <div className="space-y-4">
              {metrics.map((metric: Metric) => (
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
          <h2 className="text-lg font-semibold text-primary-400 mb-4">// ACTIVITY_LOG</h2>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 hack-card p-6">
          <h2 className="text-lg font-semibold text-primary-400 mb-4">// PROJECT_OVERVIEW</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {projects?.map((project: any) => (
              <div key={project.id} className="border border-bg-700 rounded-lg p-4 hover:border-primary-500/50 transition-colors">
                <h3 className="font-medium text-gray-200">{project.name}</h3>
                <p className="text-sm text-gray-600 mt-1">{project.description}</p>
                <div className="mt-2 flex items-center gap-2">
                  <StatusBadge status={project.status} />
                  <PriorityBadge priority={project.priority} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 🧠 MEMORIA DE USUARIO */}
        <div>
          <UserMemory />
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon, color }: { title: string, value: number, icon: string, color: 'green' | 'cyan' | 'purple' | 'orange' }) {
  const colors = {
    green: 'text-primary-400 border-primary-500/40',
    cyan: 'text-neon-400 border-neon-500/40',
    purple: 'text-purple-400 border-purple-500/40',
    orange: 'text-orange-400 border-orange-500/40',
  }

  return (
    <div className="hack-card p-6 hover:border-primary-500/30 transition-colors">
      <div className="flex items-center">
        <div className={`w-12 h-12 rounded-lg bg-bg-800 border ${colors[color]} flex items-center justify-center text-2xl`}>
          {icon}
        </div>
        <div className="ml-4">
          <p className="text-xs font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-200">{value}</p>
        </div>
      </div>
    </div>
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
