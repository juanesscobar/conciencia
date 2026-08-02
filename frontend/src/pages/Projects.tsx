import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { useState } from 'react'

interface Project {
  id: string
  name: string
  description: string
  status: string
  priority: string
  category: string
  github_repo: string
  created_at: string
}

export default function Projects() {
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => api.get('/api/v1/projects/').then(res => res.data)
  })

  const createProject = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/projects/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowModal(false)
    },
  })

  if (isLoading) {
    return <div className="text-primary-400 animate-blink">Loading projects...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// PROJECTS</h1>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon transition-all"
        >
          + NEW_PROJECT
        </button>
      </div>

      <div className="hack-card overflow-hidden">
        <table className="min-w-full divide-y divide-bg-800">
          <thead className="bg-bg-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">
                Category
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-bg-800">
            {projects?.map((project) => (
              <tr key={project.id} className="hover:bg-bg-800 transition-colors">
                <td className="px-6 py-4">
                  <Link to={`/projects/${project.id}`} className="text-primary-400 hover:text-primary-300 font-medium">
                    {project.name}
                  </Link>
                  <p className="text-sm text-gray-600">{project.description}</p>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={project.status} />
                </td>
                <td className="px-6 py-4">
                  <PriorityBadge priority={project.priority} />
                </td>
                <td className="px-6 py-4 text-sm text-gray-500 capitalize">
                  {project.category}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <ProjectModal
          onClose={() => setShowModal(false)}
          onSubmit={(data) => createProject.mutate(data)}
          loading={createProject.isPending}
        />
      )}
    </div>
  )
}

function ProjectModal({ onClose, onSubmit, loading }: {
  onClose: () => void
  onSubmit: (data: any) => void
  loading: boolean
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('active')
  const [priority, setPriority] = useState('p1')
  const [category, setCategory] = useState('core')
  const [githubRepo, setGithubRepo] = useState('')
  const [techStack, setTechStack] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    onSubmit({
      name: name.trim(),
      description: description.trim() || null,
      status,
      priority,
      category,
      github_repo: githubRepo.trim() || null,
      tech_stack: techStack.split(',').map(t => t.trim()).filter(Boolean),
    })
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="hack-card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto border-primary-500/30 shadow-neon">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-primary-400">// NEW_PROJECT</h2>
          <button onClick={onClose} className="text-gray-600 hover:text-alert-400 text-2xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ name *</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="hack-input"
              placeholder="Project name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              className="hack-input"
              placeholder="What is this project about?"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ status</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className="hack-select w-full">
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="archived">Archived</option>
                <option value="completed">Completed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className="hack-select w-full">
                <option value="p0">P0 - Critical</option>
                <option value="p1">P1 - High</option>
                <option value="p2">P2 - Medium</option>
                <option value="p3">P3 - Low</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ category</label>
              <select value={category} onChange={e => setCategory(e.target.value)} className="hack-select w-full">
                <option value="core">Core</option>
                <option value="legacy">Legacy</option>
                <option value="portfolio">Portfolio</option>
                <option value="hardware">Hardware</option>
                <option value="education">Education</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ github_repo</label>
            <input
              type="text"
              value={githubRepo}
              onChange={e => setGithubRepo(e.target.value)}
              className="hack-input"
              placeholder="juanesscobar/Multilimp (optional)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ tech_stack</label>
            <input
              type="text"
              value={techStack}
              onChange={e => setTechStack(e.target.value)}
              className="hack-input"
              placeholder="Python, FastAPI, React (comma separated)"
            />
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

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
    paused: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
    archived: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
    completed: 'bg-neon-500/10 text-neon-400 border border-neon-500/40',
  }

  return (
    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${colors[status] || colors.active}`}>
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
    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${colors[priority] || colors.p3}`}>
      {priority.toUpperCase()}
    </span>
  )
}
