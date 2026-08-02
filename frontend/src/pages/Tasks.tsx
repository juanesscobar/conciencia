import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { tasksApi, projectsApi } from '../services/api'
import { useState } from 'react'

interface Task {
  id: string
  title: string
  description: string | null
  status: string
  priority: string
  type: string
  project_id: string
  assignee: string | null
  due_date: string | null
  created_at: string
}

interface Project {
  id: string
  name: string
}

const statusColors: Record<string, string> = {
  backlog: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
  todo: 'bg-blue-500/10 text-blue-400 border border-blue-500/40',
  in_progress: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  review: 'bg-purple-500/10 text-purple-400 border border-purple-500/40',
  done: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  cancelled: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
}

const priorityColors: Record<string, string> = {
  critical: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
  high: 'bg-orange-500/10 text-orange-400 border border-orange-500/40',
  medium: 'bg-blue-500/10 text-blue-400 border border-blue-500/40',
  low: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
}

export default function Tasks() {
  const [filterProject, setFilterProject] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const { data: projects } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => projectsApi.getAll().then(res => res.data),
  })

  const { data: tasks, isLoading } = useQuery<Task[]>({
    queryKey: ['tasks', filterProject],
    queryFn: () => tasksApi.getAll(filterProject || undefined).then(res => res.data),
  })

  const createTask = useMutation({
    mutationFn: (data: any) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setShowModal(false)
    },
  })

  if (isLoading) {
    return <div className="text-primary-400 animate-blink">Loading tasks...</div>
  }

  const filtered = tasks?.filter(t => !filterStatus || t.status === filterStatus) || []

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// TASKS</h1>
        <div className="flex gap-3">
          <select
            value={filterProject}
            onChange={e => setFilterProject(e.target.value)}
            className="hack-select text-sm"
          >
            <option value="">All Projects</option>
            {projects?.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="hack-select text-sm"
          >
            <option value="">All Status</option>
            <option value="backlog">Backlog</option>
            <option value="todo">Todo</option>
            <option value="in_progress">In Progress</option>
            <option value="review">Review</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon text-sm transition-all"
          >
            + NEW_TASK
          </button>
        </div>
      </div>

      <div className="hack-card overflow-hidden">
        <table className="min-w-full divide-y divide-bg-800">
          <thead className="bg-bg-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Title</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Priority</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Assignee</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-bg-800">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-600">No tasks found</td>
              </tr>
            ) : (
              filtered.map((task) => (
                <tr key={task.id} className="hover:bg-bg-800 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-200">{task.title}</div>
                    {task.description && (
                      <div className="text-sm text-gray-600 truncate max-w-xs">{task.description}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-full font-medium ${statusColors[task.status]}`}>
                      {task.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-full font-medium ${priorityColors[task.priority]}`}>
                      {task.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 capitalize">{task.type}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{task.assignee || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(task.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <TaskModal
          projects={projects || []}
          onClose={() => setShowModal(false)}
          onSubmit={(data) => createTask.mutate(data)}
          loading={createTask.isPending}
        />
      )}
    </div>
  )
}

function TaskModal({ projects, onClose, onSubmit, loading }: {
  projects: Project[]
  onClose: () => void
  onSubmit: (data: any) => void
  loading: boolean
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [projectId, setProjectId] = useState(projects[0]?.id || '')
  const [status, setStatus] = useState('todo')
  const [priority, setPriority] = useState('medium')
  const [type, setType] = useState('feature')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      setError('Title is required')
      return
    }
    if (!projectId) {
      setError('Select a project')
      return
    }
    onSubmit({
      project_id: projectId,
      title: title.trim(),
      description: description.trim() || null,
      status,
      priority,
      type,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="hack-card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto border-primary-500/30 shadow-neon">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-primary-400">// NEW_TASK</h2>
          <button onClick={onClose} className="text-gray-600 hover:text-alert-400 text-2xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ title *</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="hack-input"
              placeholder="Task title"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ project *</label>
            <select
              value={projectId}
              onChange={e => setProjectId(e.target.value)}
              className="hack-select w-full"
            >
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              className="hack-input"
              placeholder="Describe the task..."
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ status</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className="hack-select w-full">
                <option value="backlog">Backlog</option>
                <option value="todo">Todo</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="done">Done</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className="hack-select w-full">
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ type</label>
              <select value={type} onChange={e => setType(e.target.value)} className="hack-select w-full">
                <option value="feature">Feature</option>
                <option value="bug">Bug</option>
                <option value="research">Research</option>
                <option value="content">Content</option>
                <option value="ops">Ops</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="bg-alert-500/10 border border-alert-500/40 text-alert-400 px-4 py-2 rounded-lg text-sm">
              <span className="text-alert-500">✗</span> {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-bg-700 rounded-lg text-gray-500 hover:bg-bg-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all"
            >
              {loading ? 'CREATING...' : '[ CREATE ]'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
