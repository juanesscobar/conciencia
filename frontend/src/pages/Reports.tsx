import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { deliverablesApi, reportsApi, sprintsApi, projectsApi } from '../services/api'
import { useState } from 'react'

interface Deliverable {
  id: string
  title: string
  description: string | null
  type: string
  status: string
  url: string | null
  external_id: string | null
  project_id: string
  sprint_id: string | null
  task_id: string | null
  created_at: string
}

interface Project {
  id: string
  name: string
}

interface Sprint {
  id: string
  project_id: string
  name: string
  status: string
  start_date: string
  end_date: string
}

interface SprintReport {
  sprint: { id: string; name: string; goal: string | null; status: string; start_date: string; end_date: string }
  project: { id: string | null; name: string | null; github_repo: string | null }
  tasks: { total: number; done: number; by_status: Record<string, number>; completion_pct: number; estimated_hours_total: number; estimated_hours_done: number }
  deliverables: Deliverable[]
  github: { commits: any[]; merged_pulls: any[]; error: string | null }
}

const typeColors: Record<string, string> = {
  report: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/40',
  commit: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  pr: 'bg-purple-500/10 text-purple-400 border border-purple-500/40',
  build: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  doc: 'bg-blue-500/10 text-blue-400 border border-blue-500/40',
  other: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
}

const statusColors: Record<string, string> = {
  draft: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  final: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  rejected: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
}

const taskStatusColors: Record<string, string> = {
  backlog: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
  todo: 'bg-blue-500/10 text-blue-400 border border-blue-500/40',
  in_progress: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  review: 'bg-purple-500/10 text-purple-400 border border-purple-500/40',
  done: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  cancelled: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
}

function fmtDate(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}

export default function Reports() {
  const queryClient = useQueryClient()
  const [filterProject, setFilterProject] = useState('')
  const [filterType, setFilterType] = useState('')
  const [selectedSprint, setSelectedSprint] = useState('')
  const [showModal, setShowModal] = useState(false)

  const { data: projects } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => projectsApi.getAll().then(res => res.data),
  })

  const { data: sprints } = useQuery<Sprint[]>({
    queryKey: ['sprints'],
    queryFn: () => sprintsApi.getAll().then(res => res.data),
  })

  const { data: summary } = useQuery({
    queryKey: ['reports-summary'],
    queryFn: () => reportsApi.summary().then(res => res.data),
  })

  const { data: deliverables, isLoading } = useQuery<Deliverable[]>({
    queryKey: ['deliverables', filterProject, filterType],
    queryFn: () =>
      deliverablesApi
        .getAll({
          project_id: filterProject || undefined,
          type: filterType || undefined,
        })
        .then(res => res.data),
  })

  const { data: sprintReport, isLoading: reportLoading } = useQuery<SprintReport>({
    queryKey: ['sprint-report', selectedSprint],
    queryFn: () => reportsApi.sprint(selectedSprint).then(res => res.data),
    enabled: !!selectedSprint,
  })

  const markFinal = useMutation({
    mutationFn: (id: string) => deliverablesApi.update(id, { status: 'final' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deliverables'] })
      queryClient.invalidateQueries({ queryKey: ['reports-summary'] })
    },
  })

  const removeDeliverable = useMutation({
    mutationFn: (id: string) => deliverablesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deliverables'] })
      queryClient.invalidateQueries({ queryKey: ['reports-summary'] })
    },
  })

  const filtered = deliverables || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// TRABAJO ENTREGADO</h1>
          <p className="text-xs text-gray-600 mt-1">Entregables, commits, PRs e informes por sprint</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon text-sm transition-all"
        >
          + NUEVO_ENTREGABLE
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="hack-card p-4">
          <p className="text-xs text-gray-600 uppercase tracking-wider">Tareas Done</p>
          <p className="text-3xl font-bold text-primary-400 font-mono mt-1">{summary?.tasks?.done ?? '—'}</p>
          <p className="text-xs text-gray-600 mt-1">{summary?.tasks?.completion_pct ?? 0}% completado</p>
        </div>
        <div className="hack-card p-4">
          <p className="text-xs text-gray-600 uppercase tracking-wider">Entregables</p>
          <p className="text-3xl font-bold text-primary-400 font-mono mt-1">{summary?.deliverables?.total ?? '—'}</p>
          <p className="text-xs text-gray-600 mt-1">{summary?.deliverables?.final ?? 0} finales</p>
        </div>
        <div className="hack-card p-4">
          <p className="text-xs text-gray-600 uppercase tracking-wider">Proyectos Activos</p>
          <p className="text-3xl font-bold text-primary-400 font-mono mt-1">{summary?.projects?.active ?? '—'}</p>
          <p className="text-xs text-gray-600 mt-1">de {summary?.projects?.total ?? 0} totales</p>
        </div>
        <div className="hack-card p-4">
          <p className="text-xs text-gray-600 uppercase tracking-wider">Sprint Activo</p>
          <p className="text-lg font-bold text-primary-400 font-mono mt-1 truncate">{summary?.sprints?.active || '—'}</p>
          <p className="text-xs text-gray-600 mt-1">{summary?.sprints?.total ?? 0} sprints totales</p>
        </div>
      </div>

      {/* Sprint report */}
      <div className="hack-card p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
          <h2 className="text-sm font-bold text-primary-400 tracking-wider">// INFORME_SPRINT</h2>
          <select
            value={selectedSprint}
            onChange={e => setSelectedSprint(e.target.value)}
            className="hack-select text-sm md:w-80"
          >
            <option value="">Seleccionar sprint...</option>
            {sprints?.map(s => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.status}) · {fmtDate(s.start_date)} → {fmtDate(s.end_date)}
              </option>
            ))}
          </select>
        </div>

        {reportLoading ? (
          <p className="text-primary-400 animate-blink text-sm">Cargando informe...</p>
        ) : !selectedSprint ? (
          <p className="text-xs text-gray-600">Seleccioná un sprint para ver el informe consolidado (tareas + entregables + commits + PRs).</p>
        ) : sprintReport ? (
          <div className="space-y-5">
            {/* Sprint info */}
            <div className="flex flex-wrap gap-3">
              <span className={`px-2 py-1 text-xs rounded-full font-medium ${taskStatusColors[sprintReport.sprint.status] || taskStatusColors.todo}`}>
                {sprintReport.sprint.status}
              </span>
              <span className="text-xs text-gray-500">
                {fmtDate(sprintReport.sprint.start_date)} → {fmtDate(sprintReport.sprint.end_date)}
              </span>
              {sprintReport.project.name && (
                <span className="text-xs text-gray-500">proyecto: <span className="text-primary-400">{sprintReport.project.name}</span></span>
              )}
            </div>
            {sprintReport.sprint.goal && (
              <p className="text-sm text-gray-400">🎯 {sprintReport.sprint.goal}</p>
            )}

            {/* Progress bar */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-500">Progreso del sprint</span>
                <span className="text-primary-400 font-mono">{sprintReport.tasks.completion_pct}% · {sprintReport.tasks.done}/{sprintReport.tasks.total} tareas · {sprintReport.tasks.estimated_hours_done}/{sprintReport.tasks.estimated_hours_total}h</span>
              </div>
              <div className="h-2 bg-bg-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 shadow-neon transition-all"
                  style={{ width: `${sprintReport.tasks.completion_pct}%` }}
                ></div>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {/* Entregables del sprint */}
              <div className="md:col-span-1">
                <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-2">// ENTREGABLES ({sprintReport.deliverables.length})</h3>
                {sprintReport.deliverables.length === 0 ? (
                  <p className="text-xs text-gray-600">Sin entregables registrados.</p>
                ) : (
                  <div className="space-y-2">
                    {sprintReport.deliverables.map(d => (
                      <div key={d.id} className="border border-bg-700 rounded-lg p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm text-gray-200 font-medium truncate">{d.title}</p>
                          <span className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${typeColors[d.type] || typeColors.other}`}>{d.type}</span>
                        </div>
                        {d.url && (
                          <a href={d.url} target="_blank" rel="noreferrer" className="text-xs text-primary-500 hover:underline block mt-1 truncate">
                            {d.url.replace('https://', '')}
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Commits */}
              <div className="md:col-span-1">
                <h3 className="text-xs font-bold text-primary-400 tracking-wider mb-2">// COMMITS ({sprintReport.github.commits.length})</h3>
                {sprintReport.github.error ? (
                  <p className="text-xs text-alert-400">GitHub: {sprintReport.github.error.slice(0, 80)}</p>
                ) : sprintReport.github.commits.length === 0 ? (
                  <p className="text-xs text-gray-600">Sin commits.</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {sprintReport.github.commits.slice(0, 15).map((c, i) => (
                      <div key={i} className="border border-bg-700 rounded-lg p-2">
                        <p className="text-xs text-gray-200 font-mono truncate">
                          <span className="text-primary-400">{c.sha}</span> {c.message}
                        </p>
                        <p className="text-[10px] text-gray-600">{c.author} · {fmtDate(c.date)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* PRs mergeados */}
              <div className="md:col-span-1">
                <h3 className="text-xs font-bold text-purple-400 tracking-wider mb-2">// PRs MERGEADOS ({sprintReport.github.merged_pulls.length})</h3>
                {sprintReport.github.error ? (
                  <p className="text-xs text-alert-400">GitHub: {sprintReport.github.error.slice(0, 80)}</p>
                ) : sprintReport.github.merged_pulls.length === 0 ? (
                  <p className="text-xs text-gray-600">Sin PRs mergeados.</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                    {sprintReport.github.merged_pulls.map(pr => (
                      <div key={pr.number} className="border border-bg-700 rounded-lg p-2">
                        <p className="text-xs text-gray-200 truncate">
                          <span className="text-purple-400">#{pr.number}</span> {pr.title}
                        </p>
                        <p className="text-[10px] text-gray-600">merged {fmtDate(pr.merged_at)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-alert-400">No se pudo cargar el informe.</p>
        )}
      </div>

      {/* All deliverables table */}
      <div className="hack-card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-bg-800">
          <h2 className="text-sm font-bold text-primary-400 tracking-wider">// ENTREGABLES_REGISTRADOS</h2>
          <div className="flex gap-2">
            <select value={filterProject} onChange={e => setFilterProject(e.target.value)} className="hack-select text-sm">
              <option value="">All Projects</option>
              {projects?.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <select value={filterType} onChange={e => setFilterType(e.target.value)} className="hack-select text-sm">
              <option value="">All Types</option>
              <option value="report">Report</option>
              <option value="commit">Commit</option>
              <option value="pr">PR</option>
              <option value="build">Build</option>
              <option value="doc">Doc</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-bg-800">
            <thead className="bg-bg-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Título</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Tipo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Link</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Fecha</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-primary-400 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bg-800">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-primary-400 animate-blink">Cargando...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-600">Sin entregables registrados. Creá el primero.</td></tr>
              ) : (
                filtered.map(d => (
                  <tr key={d.id} className="hover:bg-bg-800 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-200 text-sm">{d.title}</p>
                      {d.description && <p className="text-xs text-gray-600 truncate max-w-xs">{d.description}</p>}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full font-medium ${typeColors[d.type] || typeColors.other}`}>{d.type}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full font-medium ${statusColors[d.status] || statusColors.draft}`}>{d.status}</span>
                    </td>
                    <td className="px-6 py-4">
                      {d.url ? (
                        <a href={d.url} target="_blank" rel="noreferrer" className="text-xs text-primary-500 hover:underline font-mono truncate block max-w-[180px]">
                          {d.external_id ? `#${d.external_id}` : 'link ↗'}
                        </a>
                      ) : <span className="text-xs text-gray-700">—</span>}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">{fmtDate(d.created_at)}</td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        {d.status !== 'final' && (
                          <button
                            onClick={() => markFinal.mutate(d.id)}
                            className="text-xs text-primary-400 hover:text-primary-300 border border-primary-500/40 rounded px-2 py-1"
                          >
                            ✓ final
                          </button>
                        )}
                        <button
                          onClick={() => { if (confirm(`¿Eliminar entregable "${d.title}"?`)) removeDeliverable.mutate(d.id) }}
                          className="text-xs text-alert-400 hover:text-alert-300 border border-alert-500/40 rounded px-2 py-1"
                        >
                          ✗
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <DeliverableModal
          projects={projects || []}
          sprints={sprints || []}
          onClose={() => setShowModal(false)}
          onCreated={() => {
            queryClient.invalidateQueries({ queryKey: ['deliverables'] })
            queryClient.invalidateQueries({ queryKey: ['reports-summary'] })
            queryClient.invalidateQueries({ queryKey: ['sprint-report'] })
            setShowModal(false)
          }}
        />
      )}
    </div>
  )
}

function DeliverableModal({ projects, sprints, onClose, onCreated }: {
  projects: Project[]
  sprints: Sprint[]
  onClose: () => void
  onCreated: () => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [projectId, setProjectId] = useState(projects[0]?.id || '')
  const [sprintId, setSprintId] = useState('')
  const [type, setType] = useState('report')
  const [url, setUrl] = useState('')
  const [externalId, setExternalId] = useState('')
  const [error, setError] = useState('')

  const createDeliverable = useMutation({
    mutationFn: (data: any) => deliverablesApi.create(data),
    onSuccess: onCreated,
    onError: (e: any) => setError(e?.response?.data?.detail || 'Error al crear'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) { setError('El título es requerido'); return }
    if (!projectId) { setError('Seleccioná un proyecto'); return }
    createDeliverable.mutate({
      project_id: projectId,
      sprint_id: sprintId || null,
      title: title.trim(),
      description: description.trim() || null,
      type,
      status: 'draft',
      url: url.trim() || null,
      external_id: externalId.trim() || null,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="hack-card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto border-primary-500/30 shadow-neon">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-primary-400">// NUEVO_ENTREGABLE</h2>
          <button onClick={onClose} className="text-gray-600 hover:text-alert-400 text-2xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ título *</label>
            <input type="text" value={title} onChange={e => setTitle(e.target.value)} className="hack-input" placeholder="Informe semanal, build v1.2, ..." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ proyecto *</label>
              <select value={projectId} onChange={e => setProjectId(e.target.value)} className="hack-select w-full">
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ sprint</label>
              <select value={sprintId} onChange={e => setSprintId(e.target.value)} className="hack-select w-full">
                <option value="">— Sin sprint —</option>
                {sprints.filter(s => !projectId || s.project_id === projectId).map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ tipo</label>
            <select value={type} onChange={e => setType(e.target.value)} className="hack-select w-full">
              <option value="report">Report / Informe</option>
              <option value="commit">Commit</option>
              <option value="pr">Pull Request</option>
              <option value="build">Build / Release</option>
              <option value="doc">Documentación</option>
              <option value="other">Otro</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-primary-400 mb-1">$ descripción</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} className="hack-input" placeholder="Qué se entregó..." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ url (link)</label>
              <input type="text" value={url} onChange={e => setUrl(e.target.value)} className="hack-input" placeholder="https://github.com/..." />
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-400 mb-1">$ ref externa</label>
              <input type="text" value={externalId} onChange={e => setExternalId(e.target.value)} className="hack-input" placeholder="SHA / #PR / v1.2" />
            </div>
          </div>

          {error && (
            <div className="bg-alert-500/10 border border-alert-500/40 text-alert-400 px-4 py-2 rounded-lg text-sm">
              <span className="text-alert-500">✗</span> {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-bg-700 rounded-lg text-gray-500 hover:bg-bg-800">Cancel</button>
            <button type="submit" disabled={createDeliverable.isPending} className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all">
              {createDeliverable.isPending ? 'CREANDO...' : '[ CREAR ]'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
