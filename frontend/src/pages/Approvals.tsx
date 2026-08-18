import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { workflowsApi } from '../services/api'
import { EmptyState, LoadingState, ErrorState } from '../components/StateViews'

interface Run {
  id: string
  workflow_id: string
  workflow_name?: string
  status: string
  current_step: number
  step_results?: any[]
  started_at?: string
  error?: string
}

export default function Approvals() {
  const queryClient = useQueryClient()

  const { data: runs, isLoading, isError, refetch } = useQuery<Run[]>({
    queryKey: ['approvals'],
    queryFn: () => workflowsApi.pendingApprovals().then(res => res.data),
    refetchInterval: 8000,
  })

  const decide = useMutation({
    mutationFn: ({ runId, approved }: { runId: string; approved: boolean }) =>
      workflowsApi.approve(runId, approved),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['approvals'] }),
    onError: (e: any) => alert(e.response?.data?.detail || 'Error al procesar la aprobación'),
  })

  if (isLoading) return <LoadingState label="Fetching pending approvals..." />
  if (isError) return <ErrorState message="No se pudo consultar approvals pendientes." onRetry={() => refetch()} />

  const pending = (runs || []).filter(r => r.status === 'running')

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// APPROVALS</h1>
          <p className="text-xs text-gray-600 font-mono mt-1">$ human-in-the-loop · policy gates</p>
        </div>
        <span className="text-xs font-mono text-gray-500">
          {pending.length > 0 ? (
            <span className="text-yellow-400 animate-blink">⚠ {pending.length} pending</span>
          ) : (
            <span className="text-primary-400">✓ 0 pending</span>
          )}
        </span>
      </div>

      {pending.length === 0 ? (
        <EmptyState
          title="No pending approvals"
          message="No hay acciones de agentes esperando tu decisión. El flujo Policy → Approval → Execution → Audit está despejado."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {pending.map((run) => {
            const step = run.step_results?.[run.current_step] || run.step_results?.[run.step_results.length - 1]
            return (
              <div key={run.id} className="hack-card p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-200">
                      {run.workflow_name || 'Workflow'}
                    </h3>
                    <p className="text-xs text-gray-600 font-mono mt-1">run {run.id.slice(0, 8)}</p>
                  </div>
                  <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/40 animate-pulse-glow">
                    WAITING_APPROVAL
                  </span>
                </div>

                <div className="bg-bg-950/60 border border-bg-800 rounded-lg p-3 mb-4 text-xs">
                  <p className="text-gray-500">
                    <span className="text-primary-400">STEP {run.current_step + 1}</span> ·{' '}
                    {step?.step_name || 'pending'}
                  </p>
                  {step?.error && <p className="text-alert-400 mt-1 font-mono">{step.error}</p>}
                  {run.started_at && (
                    <p className="text-gray-600 mt-1">
                      started {new Date(run.started_at).toLocaleString()}
                    </p>
                  )}
                </div>

                <div className="flex gap-2 justify-end">
                  <Link
                    to="/workflows"
                    className="px-3 py-2 text-xs rounded-lg border border-bg-600 text-gray-400 hover:text-primary-300 transition-colors"
                  >
                    Ver workflow
                  </Link>
                  <button
                    onClick={() => decide.mutate({ runId: run.id, approved: false })}
                    disabled={decide.isPending}
                    className="px-4 py-2 text-xs rounded-lg border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 transition-colors disabled:opacity-40"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => decide.mutate({ runId: run.id, approved: true })}
                    disabled={decide.isPending}
                    className="px-4 py-2 text-xs rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/40 hover:bg-primary-500/20 transition-all disabled:opacity-40"
                  >
                    Approve
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
