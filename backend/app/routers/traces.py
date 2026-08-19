"""Traces - timeline unificado de ejecución (spec §23).

Combina: agent_executions + workflow runs + audit events.
NO expone chain-of-thought: solo acciones, tools, resultados y outcomes.
"""

from datetime import datetime

from fastapi import APIRouter

from app.database import SessionLocal
from app.models.execution import AgentExecution
from app.models.audit import AuditEvent
from app.models.workflow import WorkflowRun

router = APIRouter(prefix="/api/v1/traces", tags=["traces"])


def _db() -> SessionLocal():
    return SessionLocal()


@router.get("/")
def traces(limit: int = 60):
    db = _db()
    try:
        limit = min(limit, 200)
        items = []

        # Agent executions
        execs = db.query(AgentExecution).order_by(AgentExecution.created_at.desc()).limit(limit).all()
        for e in execs:
            items.append({
                "ts": (e.created_at or datetime.utcnow()).isoformat(),
                "kind": "execution",
                "actor": str(e.agent_id),
                "status": str(e.status.value) if hasattr(e.status, "value") else str(e.status),
                "summary": (e.error_message or e.output or "")[:200] if (e.error_message or e.output) else "agent execution",
                "error": e.error_message,
            })

        # Workflow runs (step traces)
        runs = db.query(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(limit).all()
        for r in runs:
            items.append({
                "ts": (r.started_at or datetime.utcnow()).isoformat(),
                "kind": "workflow",
                "actor": f"workflow:{r.workflow_id[:8]}",
                "status": r.status,
                "summary": f"run {r.id[:8]} · step {r.current_step + 1} · {_step_summary(r)}",
                "error": r.error,
            })

        # Audit events
        audits = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
        for a in audits:
            items.append({
                "ts": (a.timestamp or datetime.utcnow()).isoformat(),
                "kind": "audit",
                "actor": f"{a.actor_type}:{a.actor}",
                "status": "recorded",
                "summary": f"{a.event_type}" + (f" · {a.payload}" if a.payload else ""),
                "error": None,
            })

        items.sort(key=lambda x: x["ts"], reverse=True)
        return items[:limit]
    finally:
        db.close()


def _step_summary(run) -> str:
    results = run.step_results or []
    if not results:
        return "sin steps registrados"
    last = results[-1] if isinstance(results, list) else results
    if isinstance(last, dict):
        name = last.get("step_name", f"step {last.get('step_index', '?')}")
        st = last.get("status", "?")
        err = last.get("error")
        return f"{name} [{st}]" + (f" · {err}" if err else "")
    return str(last)[:120]
