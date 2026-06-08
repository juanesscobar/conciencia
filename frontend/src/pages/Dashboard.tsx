import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import AgentOffice from '../components/AgentOffice'

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
    return <div>Loading...</div>
  }

  const activeProjects = projects?.filter((p: any) => p.status === 'active').length || 0
  const openTasks = tasks?.filter((t: Task) => t.status !== 'done' && t.status !== 'cancelled').length || 0
  const completedTasks = tasks?.filter((t: Task) => t.status === 'done').length || 0
  const totalTasks = tasks?.length || 0

  const recentActivities = activities?.slice(0, 10) || []

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard title="Active Projects" value={activeProjects} icon="📁" color="blue" />
        <StatCard title="Total Tasks" value={totalTasks} icon="✅" color="green" />
        <StatCard title="Completed" value={completedTasks} icon="🎯" color="purple" />
        <StatCard title="Open Tasks" value={openTasks} icon="🔄" color="orange" />
      </div>

      {/* 🏢 OFICINA VIRTUAL - Agentes trabajando */}
      <div className="mb-8">
        <AgentOffice />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Metrics</h2>
          {metrics && metrics.length > 0 ? (
            <div className="space-y-4">
              {metrics.map((metric: Metric) => (
                <div key={metric.id}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm font-medium text-gray-700">{metric.name}</span>
                    <span className="text-sm text-gray-500">
                      {metric.value} / {metric.target || 'N/A'} {metric.unit}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${metric.target && metric.value >= metric.target ? 'bg-green-500' : 'bg-blue-500'}`}
                      style={{ width: metric.target ? `${Math.min(100, (metric.value / metric.target) * 100)}%` : `${Math.min(100, metric.value)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No metrics available</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
          {recentActivities.length > 0 ? (
            <ul className="space-y-3">
              {recentActivities.map((activity: Activity) => (
                <li key={activity.id} className="border-b pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    <ActivityIcon type={activity.type} />
                    <span className="text-sm text-gray-700">{activity.description}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(activity.created_at).toLocaleString()}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">No recent activity</p>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Project Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {projects?.map((project: any) => (
            <div key={project.id} className="border rounded-lg p-4">
              <h3 className="font-medium text-gray-900">{project.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{project.description}</p>
              <div className="mt-2 flex items-center gap-2">
                <StatusBadge status={project.status} />
                <PriorityBadge priority={project.priority} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon, color }: { title: string, value: number, icon: string, color: 'blue' | 'green' | 'purple' | 'orange' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`w-12 h-12 rounded-lg ${colors[color]} flex items-center justify-center text-2xl`}>
          {icon}
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
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
    task_change: '✅',
    deploy: '🚀',
    release: '📦',
    agent_action: '🤖',
  }
  return <span>{icons[type] || '📌'}</span>
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    paused: 'bg-yellow-100 text-yellow-800',
    archived: 'bg-gray-100 text-gray-800',
    completed: 'bg-blue-100 text-blue-800',
  }
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${colors[status] || colors.active}`}>
      {status}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    p0: 'bg-red-100 text-red-800',
    p1: 'bg-orange-100 text-orange-800',
    p2: 'bg-yellow-100 text-yellow-800',
    p3: 'bg-gray-100 text-gray-800',
  }
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${colors[priority] || colors.p3}`}>
      {priority.toUpperCase()}
    </span>
  )
}
