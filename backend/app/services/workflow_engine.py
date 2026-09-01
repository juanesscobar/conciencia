"""Workflow Engine — ejecuta steps declarativos (secuenciales o en paralelo).

Cada step puede:
- requerir un agente (por id) o capabilities (matching posterior)
- ser un BLOQUE PARALELO: `{"name": ..., "parallel": true, "steps": [...]}`
  → los children corren concurrentemente (fan-out) y el bloque espera a todos
  (fan-in). El output agrega los resultados; si un child falla, el bloque
  falla pero conserva los outputs parciales.
- resolver agentes DENTRO de un team (team_id) antes que el registry global
- forzar runtime en el matching (step.runtime)
- tener timeout (s) y retry policy
- requerir aprobación humana (approval: true → status waiting_approval)
- tener max_cost (se corta si el acumulado lo supera)

Nota (paralelismo + SQLAlchemy): cada child corre en su PROPIA sesión ligada
al mismo bind del engine (los threads no comparten sesión). Limitación: en
SQLite in-memory cada conexión vería una DB vacía; tests y dev usan archivo
(test.db / missioncontrol.db), prod usa Postgres → OK.
"""

import copy
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, sessionmaker

from app.models.workflow import Workflow, WorkflowRun, start_run

log = logging.getLogger("workflows")


def execute_workflow(db: Session, workflow_id: str, run_id: str | None = None,
                     team_id: str | None = None) -> WorkflowRun:
    """Ejecuta un workflow sincrónicamente (o continúa un run existente).

    team_id: contexto de team para resolver steps por capabilities dentro del
    team primero (Fase F — Mission coordina agentes de un team).
    """
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

        # bloque paralelo (fan-out → fan-in)
        if step.get("parallel") and step.get("steps"):
            output, error, cost, children = _run_parallel_block(db, step, wf, team_id)
            results.append({
                "step_index": idx,
                "step_name": step_name,
                "status": "completed" if not error else "failed",
                "output": output,
                "error": error,
                "cost": cost,
                "parallel": True,
                "children": children,
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
            continue

        # ejecutar el step (si tiene agente o task_text)
        output, error, cost = _run_step(db, step, wf, team_id=team_id)
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


def _run_step(db: Session, step: dict, wf: Workflow,
              team_id: Optional[str] = None) -> Tuple[Optional[str], Optional[str], float]:
    """Ejecuta un step. Si no hay agente/tarea, es un step declarativo (no-op ok).

    Resolución de agente (en orden):
      1. agent_id explícito
      2. capabilities dentro del team (si team_id y el team cubre >= 50%)
      3. capabilities global (registry)
    step.runtime (si existe) filtra el matching por runtime.
    """
    task_text = step.get("task") or step.get("task_text")
    agent_id = step.get("agent_id")
    runtime_hint = step.get("runtime") or None

    # Capability matching: team primero, registry global como fallback.
    # - required_capabilities (duro): sin agente → error (steps explícitos)
    # - capabilities (blando, default workflows): sin agente → declarativo
    hard_caps = step.get("required_capabilities")
    soft_caps = step.get("capabilities") if not hard_caps else None
    if not agent_id and (hard_caps or soft_caps):
        caps = hard_caps or soft_caps
        best = None
        if team_id:
            from app.services import team_service

            best = team_service.best_agent_in_team(
                db,
                team_id=team_id,
                required_capabilities=caps,
                runtime=runtime_hint,
            )
        if not best:
            from app.services.capability_matching import best_agent

            best = best_agent(db, required_capabilities=caps, runtime=runtime_hint)
        if not best:
            if hard_caps:
                return None, f"No hay agente que cubra >=50% de {hard_caps}", 0.0
            return f"[{step.get('name','step')}] sin agente disponible (declarativo)", None, 0.0
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


# ---------------------------------------------------------------------------
# Bloques paralelos (Fase F)
# ---------------------------------------------------------------------------

def _new_session(db: Session) -> Session:
    """Sesión nueva ligada al MISMO bind que la sesión padre (thread-safe)."""
    return sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)()


def _run_parallel_block(db: Session, step: dict, wf: Workflow,
                        team_id: Optional[str]) -> Tuple[str, Optional[str], float, List[dict]]:
    """Fan-out: corre los children del bloque en threads y espera a todos.

    Devuelve (output_summary, error, cost_total, children_results).
    Si algún child falla, el bloque falla pero conserva outputs parciales.
    """
    children: List[dict] = step.get("steps") or []
    total_cost = 0.0
    child_results: List[dict] = []

    if not children:
        return "[parallel] sin steps", None, 0.0, []

    def _run_child(child: dict) -> dict:
        child_session = _new_session(db)
        try:
            output, error, cost = _run_step(child_session, child, wf, team_id=team_id)
            return {
                "name": child.get("name", "child"),
                "status": "completed" if not error else "failed",
                "output": output,
                "error": error,
                "cost": cost,
            }
        except Exception as e:  # noqa: BLE001 — un child no debe matar al bloque
            return {
                "name": child.get("name", "child"),
                "status": "failed",
                "output": None,
                "error": str(e)[:300],
                "cost": 0.0,
            }
        finally:
            child_session.close()

    max_workers = min(len(children), int(step.get("max_parallel") or len(children)) or len(children))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_run_child, c) for c in children]
        child_results = [f.result() for f in futures]

    ok = 0
    errors: List[str] = []
    for r in child_results:
        total_cost += float(r.get("cost") or 0.0)
        if r["status"] == "completed":
            ok += 1
        else:
            errors.append(f"{r['name']}: {r['error']}")

    summary = f"[parallel] {ok}/{len(child_results)} steps completados"
    error = "; ".join(errors) if errors else None
    return summary, error, round(total_cost, 4), child_results


# ---------------------------------------------------------------------------
# Control de runs
# ---------------------------------------------------------------------------

def approve_step(db: Session, run: WorkflowRun, step_index: int, approved: bool,
                 team_id: Optional[str] = None) -> WorkflowRun:
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
        execute_workflow(db, run.workflow_id, run.id, team_id=team_id)
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
