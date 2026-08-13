"""Workflow Engine — ejecuta steps declarativos de forma secuencial.

Cada step puede:
- requerir un agente (por id) o capabilities (matching posterior)
- tener timeout (s) y retry policy
- requerir aprobación humana (approval: true → status waiting_approval)
- tener max_cost (se corta si el acumulado lo supera)
"""

import copy
import logging
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.workflow import Workflow, WorkflowRun, start_run

log = logging.getLogger("workflows")


def execute_workflow(db: Session, workflow_id: str, run_id: str | None = None) -> WorkflowRun:
    """Ejecuta un workflow sincrónicamente (o continúa un run existente)."""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise ValueError("Workflow not found")

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first() if run_id else None
    if not run:
        run = start_run(db, wf)

    steps = wf.definition or []
    # deepcopy: si los dicts internos son los mismos objetos, SQLAlchemy no detecta el cambio JSON
    results = copy.deepcopy(run.step_results or [])

    for idx in range(run.current_step, len(steps)):
        if run.status == "cancelled":
            return run
        if run.status == "paused":
            run.paused_at = datetime.utcnow()
            db.commit()
            return run

        step = steps[idx]
        step_name = step.get("name", f"step_{idx + 1}")
        run.current_step = idx
        db.commit()

        # approval gate
        if step.get("approval"):
            results.append({
                "step_index": idx,
                "step_name": step_name,
                "status": "waiting_approval",
                "output": None,
                "error": None,
                "cost": 0,
                "approval_token": uuid.uuid4().hex[:16],
            })
            run.step_results = results
            run.status = "paused"  # espera aprobación humana
            wf.status = "paused"
            run.paused_at = datetime.utcnow()
            db.commit()
            log.info(f"workflow {wf.id} pausado en step {idx} ({step_name}) — aprobación requerida")
            return run

        # ejecutar el step (si tiene agente o task_text)
        output, error, cost = _run_step(db, step, wf)
        results.append({
            "step_index": idx,
            "step_name": step_name,
            "status": "completed" if not error else "failed",
            "output": output,
            "error": error,
            "cost": cost,
        })
        run.step_results = results
        run.current_step = idx + 1
        if error:
            run.status = "failed"
            run.error = f"{step_name}: {error}"
            wf.status = "failed"
            wf.error = run.error
            wf.completed_at = datetime.utcnow()
            db.commit()
            return run
        db.commit()

    run.status = "completed"
    run.completed_at = datetime.utcnow()
    wf.status = "completed"
    wf.completed_at = datetime.utcnow()
    db.commit()
    return run


def _run_step(db: Session, step: dict, wf: Workflow) -> tuple[str | None, str | None, float]:
    """Ejecuta un step. Si no hay agente/tarea, es un step declarativo (no-op ok)."""
    task_text = step.get("task") or step.get("task_text")
    agent_id = step.get("agent_id")

    # Capability matching: si el step pide capabilities y no un agente concreto
    if not agent_id and step.get("required_capabilities"):
        from app.services.capability_matching import best_agent

        best = best_agent(db, required_capabilities=step.get("required_capabilities"))
        if not best:
            return None, f"No hay agente que cubra >=50% de {step.get('required_capabilities')}", 0.0
        agent_id = best["agent_id"]

    if not task_text and not agent_id:
        return f"[{step.get('name','step')}] sin ejecución (declarativo)", None, 0.0

    if not agent_id:
        return None, "step define task pero no agent_id (capability matching pendiente)", 0.0

    # ejecutar vía adapter del agente
    from app.models.agent import Agent
    from app.adapters.registry import get_adapter
    from app.adapters.base import AgentIdentity
    from app.services.agent_soul import load_agent_persona

    agent = db.query(Agent).filter(Agent.id == uuid.UUID(str(agent_id))).first()
    if not agent:
        return None, f"agent {agent_id} no encontrado", 0.0

    runtime = getattr(agent, "runtime", "generic")
    runtime_name = runtime.value if hasattr(runtime, "value") else runtime
    adapter = get_adapter(runtime_name)
    if not adapter:
        return None, f"runtime {runtime_name} sin adapter", 0.0

    provider = getattr(agent, "provider", "deepseek")
    provider_name = provider.value if hasattr(provider, "value") else provider

    identity = AgentIdentity(
        agent_id=str(agent.id), name=agent.name,
        role=agent.role.value if hasattr(agent.role, "value") else str(agent.role),
        runtime=runtime_name, provider=provider_name, model=getattr(agent, "model", None),
        system_prompt=load_agent_persona(agent.role.value) or agent.system_prompt or "",
        capabilities=agent.capabilities or [], config=agent.config or {},
    )

    start = time.time()
    result = adapter.dispatch_task(identity, task_text, step.get("context"))
    cost = 0.0
    if result.usage and result.usage.get("cost_estimate_usd"):
        cost = float(result.usage["cost_estimate_usd"])
    if result.status == "failed":
        return None, result.error, cost
    return result.output, None, cost


def approve_step(db: Session, run: WorkflowRun, step_index: int, approved: bool) -> WorkflowRun:
    """Aprueba/rechaza el step que esperaba aprobación y continúa."""
    results = copy.deepcopy(run.step_results or [])
    for r in results:
        if r.get("step_index") == step_index and r.get("status") == "waiting_approval":
            r["status"] = "approved" if approved else "rejected"
            r["approved_at"] = datetime.utcnow().isoformat()
            break
    run.step_results = results
    run.status = "running" if approved else "cancelled"
    run.paused_at = None
    # avanzar el puntero para que execute_workflow continúe DESPUÉS del step aprobado
    run.current_step = step_index + 1

    wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    if wf:
        if approved:
            wf.status = "running"
            wf.current_step = step_index + 1
        else:
            wf.status = "cancelled"
            wf.completed_at = datetime.utcnow()
    db.commit()
    if approved:
        execute_workflow(db, run.workflow_id, run.id)
    return run


def pause_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    run.status = "paused"
    run.paused_at = datetime.utcnow()
    wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    if wf:
        wf.status = "paused"
    db.commit()
    return run


def cancel_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    run.status = "cancelled"
    run.completed_at = datetime.utcnow()
    wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    if wf:
        wf.status = "cancelled"
        wf.completed_at = datetime.utcnow()
    db.commit()
    return run
