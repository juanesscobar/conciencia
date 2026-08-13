import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { workflowsApi, agentsApi } from '../services/api'
import { useState } from 'react'

interface StepResult {
  step_index: number
  step_name: string
  status: string
  output: string | null
  error: string | null
  cost: number
  approved_at?: string
}

interface WorkflowRun {
  id: string
  workflow_id: string
  workflow_name?: string
  status: string
  step_results: StepResult[]
  current_step: number
  error: string | null
  started_at: string | null
  completed_at: string | null
}

interface WorkflowStep {
  name: string
  agent_id?: string | null
  required_capabilities?: string[] | null
  task?: string | null
  approval?: boolean
}

interface Workflow {
  id: string
  name: string
  project_id: string | null
  definition: WorkflowStep[]
  status: string
  current_step: number
  error: string | null
  created_at: string | null
}

interface Agent {
  id: string
  name: string
  role: string
}

const wfStatusColors: Record<string, string> = {
  draft: 'bg-gray-500/10 text-gray-400 border border-gray-500/40',
  running: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/40',
  paused: 'bg-orange-500/10 text-orange-400 border border-orange-500/40',
  completed: 'bg-primary-500/10 text-primary-400 border border-primary-500/40',
  failed: 'bg-alert-500/10 text-alert-400 border border-alert-500/40',
  cancelled: 'bg-gray-500/10 text-gray-500 border border-gray-600/40',
}

const stepIcons: Record<string, string> = {
  completed: '✓',
  approved: '✓',
  failed: '✗',
  rejected: '✗',
  waiting_approval: '⏸',
}

const stepColors: Record<string, string> = {
  completed: 'text-primary-400',
  approved: 'text-primary-400',
  failed: 'text-alert-400',
  rejected: 'text-alert-400',
  waiting_approval: 'text-orange-400 animate-blink',
}

export default function Workflows() {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const { data: workflows, isLoading } = useQuery<Workflow[]>({
    queryKey: ['workflows'],
    queryFn: () => workflowsApi.getAll().then(res => res.data),
  })

  const { data: pending } = useQuery<WorkflowRun[]>({
    queryKey: ['workflows-pending'],
    queryFn: () => workflowsApi.pendingApprovals().then(res => res.data),
    refetchInterval: 5000,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['workflows'] })
    queryClient.invalidateQueries({ queryKey: ['workflows-pending'] })
    queryClient.invalidateQueries({ queryKey: ['workflow-runs'] })
  }

  const runWf = useMutation({
    mutationFn: (id: string) => workflowsApi.run(id),
    onSuccess: invalidate,
  })

  const approveRun = useMutation({
    mutationFn: ({ runId, approved }: { runId: string; approved: boolean }) =>
      workflowsApi.approve(runId, approved),
    onSuccess: invalidate,
  })

  const cancelRun = useMutation({
    mutationFn: (runId: string) => workflowsApi.cancel(runId),
    onSuccess: invalidate,
  })

  const createWf = useMutation({
    mutationFn: (data: any) => workflowsApi.create(data),
    onSuccess: () => {
      invalidate()
      setShowModal(false)
    },
  })

  if (isLoading) {
    return <div className="text-primary-400 animate-blink">Loading workflows...</div>
  }

  const waitingSteps = (run: WorkflowRun) =>
    run.step_results.filter(r => r.status === 'waiting_approval')

  return (
    <div>
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// WORKFLOWS</h1>
          <p className="text-xs text-gray-600 mt-1">
            {workflows?.length || 0} workflows · orquestación declarativa con aprobación humana
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600/90 text-bg-950 font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon text-sm transition-all"
        >
          + NEW_WORKFLOW
        </button>
      </div>

      {pending && pending.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-bold text-orange-400 tracking-wider mb-3">
            ⏳ APPROVAL GATES — {pending.length} esperando decisión
          </h2>
          <div className="space-y-3">
            {pending.map(run => (
              <div key={run.id} className="hack-card p-4 border-orange-500/40">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      {run.workflow_name || run.workflow_id}
                    </p>
                    {waitingSteps(run).map(s => (
                      <p key={s.step_index} className="text-xs text-orange-400 mt-1">
                        ⏸ step {s.step_index + 1}: {s.step_name}
                      </p>
                    ))}
                    {run.started_at && (
                      <p className="text-[10px] text-gray-600 mt-1">
                        iniciado {new Date(run.started_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => approveRun.mutate({ runId: run.id, approved: true })}
                      disabled={approveRun.isPending}
                      className="px-3 py-1.5 bg-primary-600/90 text-bg-950 text-xs font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all"
                    >
                      ✓ APPROVE
                    </button>
                    <button
                      onClick={() => approveRun.mutate({ runId: run.id, approved: false })}
                      disabled={approveRun.isPending}
                      className="px-3 py-1.5 bg-alert-500/20 text-alert-400 border border-alert-500/40 text-xs font-bold rounded-lg hover:bg-alert-500/30 disabled:opacity-50 transition-all"
                    >
                      ✗ REJECT
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        {workflows?.length === 0 && (
          <div className="hack-card p-6 text-center text-gray-600">
            No workflows yet — creá uno con steps declarativos
          </div>
        )}
        {workflows?.map(wf => (
          <div key={wf.id} className="hack-card overflow-hidden">
            <div
              className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer hover:bg-bg-800 transition-colors"
              onClick={() => setExpanded(expanded === wf.id ? null : wf.id)}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-primary-500">{expanded === wf.id ? '▼' : '▶'}</span>
                <div className="min-w-0">
                  <p className="font-medium text-gray-200 truncate">{wf.name}</p>
                  <p className="text-xs text-gray-600">
                    {wf.definition?.length || 0} steps
                    {wf.definition?.some(s => s.approval) && ' · con approval gates'}
                    {wf.created_at && ` · ${new Date(wf.created_at).toLocaleDateString()}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`px-2 py-1 text-xs rounded-full font-medium ${wfStatusColors[wf.status] || wfStatusColors.draft}`}>
                  {wf.status.replace(/_/g, ' ')}
                </span>
                {['draft', 'completed', 'failed', 'cancelled'].includes(wf.status) && (
                  <button
                    onClick={e => {
                      e.stopPropagation()
                      runWf.mutate(wf.id)
                    }}
                    disabled={runWf.isPending}
                    className="px-3 py-1 bg-primary-600/90 text-bg-950 text-xs font-bold rounded-lg hover:bg-primary-500 hover:shadow-neon disabled:opacity-50 transition-all"
                  >
                    ▶ RUN
                  </button>
                )}
              </div>
            </div>
            {wf.error && (
              <div className="px-4 pb-2 text-xs text-alert-400">✗ {wf.error}</div>
            )}
            {expanded === wf.id && (
              <RunHistory
                workflowId={wf.id}
                onApprove={(runId, approved) => approveRun.mutate({ runId, approved })}
                onCancel={runId => cancelRun.mutate(runId)}
                busy={approveRun.isPending || cancelRun.isPending}
              />
            )}
          </div>
        ))}
      </div>

      {showModal && (
        <WorkflowModal
          onClose={() => setShowModal(false)}
          onSubmit={data => createWf.mutate(data)}
          loading={createWf.isPending}
        />
      )}
    </div>
  )
}

function RunHistory({ workflowId, onApprove, onCancel, busy }: {
  workflowId: string
  onApprove: (runId: string, approved: boolean) => void
  onCancel: (runId: string) => void
  busy: boolean
}) {
  const { data: runs } = useQuery<WorkflowRun[]>({
    queryKey: ['workflow-runs', workflowId],
    queryFn: () => workflowsApi.getRuns(workflowId).then(res => res.data),
    refetchInterval: 5000,
  })

  if (!runs || runs.length === 0) {
    return <div className="px-4 pb-4 text-xs text-gray-600">Sin ejecuciones todavía</div>
  }

  return (
    <div className="px-4 pb-4 space-y-3 border-t border-bg-800 pt-3">
      {runs.map(run => (
        <div key={run.id} className="bg-bg-950/60 rounded-lg p-3 border border-bg-800">
          <div className="flex items-center justify-between mb-2">
            <span className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${wfStatusColors[run.status] || wfStatusColors.draft}`}>
              {run.status.replace(/_/g, ' ')}
            </span>
            <div className="flex items-center gap-2">
              {run.started_at && (
                <span className="text-[10px] text-gray-600">
                  {new Date(run.started_at).toLocaleString()}
                </span>
              )}
              {run.status === 'paused' && (
                <button
                  onClick={() => onCancel(run.id)}
                  disabled={busy}
                  className="px-2 py-0.5 text-[10px] text-alert-400 border border-alert-500/40 rounded hover:bg-alert-500/20 disabled:opacity-50"
                >
                  CANCEL
                </button>
              )}
            </div>
          </div>
          <div className="space-y-1">
            {run.step_results.map(step => (
              <div key={step.step_index} className="flex items-start gap-2 text-xs">
                <span className={`${stepColors[step.status] || 'text-gray-500'} font-mono`}>
                  {stepIcons[step.status] || '…'}
                </span>
                <span className="text-gray-400">
                  {step.step_name}
                  <span className="text-gray-600"> — {step.status.replace(/_/g, ' ')}</span>
                  {step.cost > 0 && <span className="text-primary-500"> · ${step.cost.toFixed(4)}</span>}
                </span>
                {step.status === 'waiting_approval' && (
                  <span className="flex gap-1 ml-auto">
                    <button
                      onClick={() => onApprove(run.id, true)}
                      disabled={busy}
                      className="px-2 py-0.5 text-[10px] font-bold bg-primary-600/90 text-bg-950 rounded hover:bg-primary-500 disabled:opacity-50"
                    >
                      ✓
                    </button>
                    <button
                      onClick={() => onApprove(run.id, false)}
                      disabled={busy}
                      className="px-2 py-0.5 text-[10px] font-bold text-alert-400 border border-alert-500/40 rounded hover:bg-alert-500/20 disabled:opacity-50"
                    >
                      ✗
                    </button>
                  </span>
                )}
              </div>
            ))}
            {run.error && <div className="text-xs text-alert-400 pl-5">✗ {run.error}</div>}
            {run.step_results.length === 0 && (
              <div className="text-xs text-gray-600">Run iniciado, sin steps ejecutados</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function WorkflowModal({ onClose, onSubmit, loading }: {
  onClose: () => void
  onSubmit: (data: any) => void
  loading: boolean
}) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [steps, setSteps] = useState<Array<{
    name: string
    task: string
    agent_id: string
    capabilities: string
    approval: boolean
  }>>([{ name: '', task: '', agent_id: '', capabilities: '', approval: false }])

  const { data: agents } = useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: () => agentsApi.getAll().then(res => res.data),
  })

  const updateStep = (i: number, patch: Partial<typeof steps[number]>) => {
    setSteps(steps.map((s, idx) => (idx === i ? { ...s, ...patch } : s)))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Name is required')
      return
    }
    const valid = steps.filter(s => s.name.trim())
    if (valid.length === 0) {
      setError('At least one step with name')
      return
    }
    onSubmit({
      name: name.trim(),
      steps: valid.map(s => ({
        name: s.name.trim(),
        task: s.task.trim() || null,
        agent_id: s.agent_id || null,
        required_capabilities: s.capabilities.trim()
          ? s.capabilities.split(',').map(c => c.trim()).filter(Boolean)
          : null,
        approval: s.approval,
      })),
    })
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="hack-card w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto border-primary-500/30 shadow-neon">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-primary-400">// NEW_WORKFLOW</h2>
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
              placeholder="deploy-pipeline"
            />
          </div>

          <div className="space-y-3">
            <label className="block text-sm font-medium text-primary-400">$ steps *</label>
            {steps.map((step, i) => (
              <div key={i} className="bg-bg-950/60 border border-bg-800 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 font-mono">step_{i + 1}</span>
                  {steps.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setSteps(steps.filter((_, idx) => idx !== i))}
                      className="text-xs text-gray-600 hover:text-alert-400"
                    >
                      remove
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={step.name}
                    onChange={e => updateStep(i, { name: e.target.value })}
                    className="hack-input text-sm"
                    placeholder="step name *"
                  />
                  <select
                    value={step.agent_id}
                    onChange={e => updateStep(i, { agent_id: e.target.value })}
                    className="hack-select text-sm"
                  >
                    <option value="">auto (por capabilities)</option>
                    {agents?.map(a => (
                      <option key={a.id} value={a.id}>{a.name} ({a.role})</option>
                    ))}
                  </select>
                </div>
                <input
                  type="text"
                  value={step.task}
                  onChange={e => updateStep(i, { task: e.target.value })}
                  className="hack-input text-sm"
                  placeholder="tarea a ejecutar (opcional)"
                />
                <input
                  type="text"
                  value={step.capabilities}
                  onChange={e => updateStep(i, { capabilities: e.target.value })}
                  className="hack-input text-sm"
                  placeholder="capabilities requeridas: code_review, testing"
                />
                <label className="flex items-center gap-2 text-xs text-gray-400">
                  <input
                    type="checkbox"
                    checked={step.approval}
                    onChange={e => updateStep(i, { approval: e.target.checked })}
                    className="accent-orange-500"
                  />
                  ⏸ approval gate (pausa y espera aprobación humana antes de continuar)
                </label>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setSteps([...steps, { name: '', task: '', agent_id: '', capabilities: '', approval: false }])}
              className="text-xs text-primary-400 hover:text-primary-300"
            >
              + add step
            </button>
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
