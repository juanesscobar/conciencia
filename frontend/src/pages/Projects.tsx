import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { projectsApi, tasksApi, githubApi } from '../services/api'
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

interface Task {
  id: string
  project_id: string
  title: string
  status: string
}

interface GithubRepo {
  name: string
  full_name: string
  description: string | null
  url: string
  stars: number
  forks: number
  language: string | null
  updated_at: string
  created_at: string
}

function fmtRepoDate(d: string): string {
  return new Date(d).toLocaleDateString('es-PY', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

export default function Projects() {
  const [showModal, setShowModal] = useState(false)
  const [repoMsg, setRepoMsg] = useState('')
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => projectsApi.getAll().then(res => res.data),
  })

  const { data: allTasks } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: () => tasksApi.getAll().then(res => res.data),
  })

  // Progreso real por misión: done/total (spec §14 PROGRESS)
  const taskStats = (allTasks || []).reduce<Record<string, { done: number; total: number }>>((acc, t) => {
    const key = String(t.project_id)
    acc[key] = acc[key] || { done: 0, total: 0 }
    acc[key].total += 1
    if (t.status === 'done') acc[key].done += 1
    return acc
  }, {})

  const { data: repos, isLoading: reposLoading } = useQuery<GithubRepo[]>({
    queryKey: ['github-repos'],
    queryFn: () => githubApi.getRepos().then(res => res.data.repos),
  })

  const createProject = useMutation({
    mutationFn: (data: any) => projectsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowModal(false)
    },
  })

  const addFromGithub = useMutation({
    mutationFn: (fullName: string) => projectsApi.fromGithub(fullName),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setRepoMsg(`✓ Proyecto «${res.data.name}» creado desde GitHub`)
      setTimeout(() => setRepoMsg(''), 5000)
    },
    onError: (e: any) => {
      setRepoMsg(`✗ ${e.response?.data?.detail || e.message}`)
      setTimeout(() => setRepoMsg(''), 5000)
    },
  })

  if (isLoading) {
    return <div className="text-primary-400 animate-blink">Loading projects...</div>
  }

  const existingRepos = new Set((projects || []).map(p => p.github_repo).filter(Boolean))

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// MISSIONS</h1>
          <p className="text-sm text-gray-500 mt-1">Unidad de intención autónoma — contenedor de tasks, workflows, agentes y resultados</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon transition-all"
        >
          + NEW_MISSION
        </button>
      </div>

      {/* Repos de GitHub */}
      <div className="bg-bg-900 border border-bg-700 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-primary-400 tracking-wider">// REPOSITORIOS DE GITHUB</h2>
          <span className="text-xs text-gray-500">{repos?.length || 0} repos conectados</span>
        </div>

        {reposLoading ? (
          <p className="text-xs text-gray-600 animate-blink">Cargando repos...</p>
        ) : !repos || repos.length === 0 ? (
          <p className="text-xs text-gray-600">
            No se pudieron cargar los repos. Verificá el token en Configuración → Integraciones → GitHub.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
            {repos.map(repo => {
              const already = existingRepos.has(repo.full_name)
              return (
                <div key={repo.full_name} className="bg-bg-950 border border-bg-700 rounded-lg p-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <a href={repo.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-primary-400 hover:underline truncate">
                        {repo.full_name}
                      </a>
                      {already && <span className="text-[10px] px-1.5 py-0.5 rounded border border-primary-500/40 text-primary-400 whitespace-nowrap">✓ proyecto</span>}
                    </div>
                    {repo.description && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{repo.description}</p>}
                    <div className="flex gap-3 mt-1.5 text-[10px] text-gray-600">
                      {repo.language && <span>⚡ {repo.language}</span>}
                      <span>⭐ {repo.stars}</span>
                      <span>🍴 {repo.forks}</span>
                      <span>🕒 {fmtRepoDate(repo.updated_at)}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => addFromGithub.mutate(repo.full_name)}
                    disabled={already || addFromGithub.isPending}
                    className="text-xs px-2.5 py-1.5 rounded border border-bg-600 text-gray-300 hover:text-primary-300 hover:border-primary-500/50 transition-colors disabled:opacity-30 whitespace-nowrap"
                  >
                    {already ? 'Agregado' : '+ Agregar'}
                  </button>
                </div>
              )
            })}
          </div>
        )}
        {repoMsg && <p className="text-xs text-primary-400 mt-3">{repoMsg}</p>}
      </div>

      {/* Misiones */}
      <div className="hack-card overflow-hidden">
        <table className="min-w-full divide-y divide-bg-800">
          <thead className="bg-bg-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Mission</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Progress</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Priority</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">GitHub</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-bg-800">
            {projects?.map((project) => {
              const stats = taskStats[project.id] || { done: 0, total: 0 }
              const pct = stats.total > 0 ? Math.round((stats.done / stats.total) * 100) : 0
              return (
                <tr key={project.id} className="hover:bg-bg-800 transition-colors">
                  <td className="px-6 py-4">
                    <Link to={`/projects/${project.id}`} className="text-primary-400 hover:text-primary-300 font-medium">
                      {project.name}
                    </Link>
                    <p className="text-sm text-gray-600 line-clamp-1">{project.description}</p>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={project.status} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-bg-800 rounded-full h-1.5 border border-bg-700">
                        <div
                          className={`h-1.5 rounded-full ${pct === 100 ? 'bg-neon-500' : 'bg-primary-500'}`}
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 font-mono">{stats.done}/{stats.total}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <PriorityBadge priority={project.priority} />
                  </td>
                  <td className="px-6 py-4">
                    {project.github_repo ? (
                      <a
                        href={`https://github.com/${project.github_repo}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-gray-400 hover:text-primary-300 hover:underline"
                      >
                        {project.github_repo}
                      </a>
                    ) : (
                      <span className="text-xs text-gray-700">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
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
          <h2 className="text-xl font-bold text-primary-400">// NEW_MISSION</h2>
          <button onClick={onClose} className="text-gray-600 hover:text-alert-400 text-2xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ objective *</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} className="hack-input" placeholder="Mission objective" />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} className="hack-input" placeholder="What should this mission accomplish?" />
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
            <input type="text" value={githubRepo} onChange={e => setGithubRepo(e.target.value)} className="hack-input" placeholder="juanesscobar/Multilimp (optional)" />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ tech_stack</label>
            <input type="text" value={techStack} onChange={e => setTechStack(e.target.value)} className="hack-input" placeholder="Python, FastAPI, React (comma separated)" />
          </div>

          {error && (
            <div className="bg-alert-500/10 border border-alert-500/40 text-alert-400 px-4 py-2 rounded-lg text-sm">
              <span className="text-alert-500">✗</span> {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-bg-700 rounded-lg text-gray-500 hover:bg-bg-800">Cancel</button>
            <button type="submit" disabled={loading} className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all">
              {loading ? 'CREATING...' : '[ LAUNCH MISSION ]'}
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
