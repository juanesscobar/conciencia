"""MissionService — orquesta Missions reusando workflow_engine y AgentExecution.

Principio (master prompt §3/§6): NO duplicar capacidades existentes.
Una Mission referencia un Workflow (definición declarativa) y produce
MissionRuns que envuelven WorkflowRun/AgentExecution para observabilidad.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.mission import Mission, MissionRun, MISSION_TYPES, MISSION_STATUSES
from app.models.workflow import Workflow, WorkflowRun
from app.services import workflow_engine

log = logging.getLogger("missions")

# Tipo de misión → workflow por defecto (steps declarativos, reusados por workflow_engine)
DEFAULT_WORKFLOWS = {
    "research": [
        {"name": "research", "agent": None, "capabilities": ["research"], "timeout": 300, "retry": 1},
        {"name": "synthesis", "agent": None, "capabilities": ["research"], "timeout": 300, "retry": 1},
        {"name": "approval", "approval": True, "capabilities": [], "timeout": 0},
    ],
    "software-development": [
        {"name": "plan", "agent": None, "capabilities": ["planning"], "timeout": 300, "retry": 1},
        {"name": "approval", "approval": True, "capabilities": [], "timeout": 0},
        {"name": "implement", "agent": None, "capabilities": ["code"], "timeout": 900, "retry": 2},
        {"name": "test", "agent": None, "capabilities": ["testing"], "timeout": 600, "retry": 2},
    ],
    "code-review": [
        {"name": "review", "agent": None, "capabilities": ["code_review"], "timeout": 600, "retry": 1},
        {"name": "report", "agent": None, "capabilities": ["reporting"], "timeout": 300, "retry": 1},
    ],
    "technical-audit": [
        {"name": "audit", "agent": None, "capabilities": ["research"], "timeout": 600, "retry": 1},
        {"name": "approval", "approval": True, "capabilities": [], "timeout": 0},
        {"name": "report", "agent": None, "capabilities": ["reporting"], "timeout": 300, "retry": 1},
    ],
    "lead-research": [
        {"name": "discovery", "agent": None, "capabilities": ["leads.read", "search.execute"], "timeout": 600, "retry": 2},
        {"name": "enrich", "agent": None, "capabilities": ["website_fetch"], "timeout": 600, "retry": 2},
        {"name": "classify", "agent": None, "capabilities": ["classification"], "timeout": 300, "retry": 1},
        {"name": "approval", "approval": True, "capabilities": [], "timeout": 0},
    ],
}


def create_mission(
    db: Session,
    *,
    name: str,
    objective: str,
    description: Optional[str] = None,
    type: str = "research",
    project_id: Optional[str] = None,
    requester_id: Optional[str] = None,
    agent_ids: Optional[List[str]] = None,
    runtime: str = "generic",
    budget: Optional[dict] = None,
    approval_policy: Optional[dict] = None,
    success_criteria: Optional[List[str]] = None,
) -> Mission:
    if type not in MISSION_TYPES:
        raise ValueError(f"Tipo de misión inválido: {type}. Válidos: {', '.join(MISSION_TYPES)}")
    mission = Mission(
        name=name,
        objective=objective,
        description=description,
        type=type,
        status="draft",
        project_id=project_id,
        requester_id=requester_id,
        agent_ids=agent_ids or [],
        runtime=runtime,
        budget=budget or {},
        approval_policy=approval_policy or {},
        success_criteria=success_criteria or [],
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def plan_mission(db: Session, mission: Mission) -> Mission:
    """Genera el workflow por defecto para el tipo de misión (si no tiene uno)."""
    if mission.workflow_id:
        return mission
    steps = DEFAULT_WORKFLOWS.get(mission.type)
    if not steps:
        raise ValueError(f"No hay workflow por defecto para tipo '{mission.type}'")
    wf = Workflow(name=f"{mission.name} · {mission.type}", project_id=str(mission.project_id) if mission.project_id else None, definition=steps)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    mission.workflow_id = wf.id
    mission.status = "planned"
    db.commit()
    db.refresh(mission)
    return mission


def run_mission(db: Session, mission: Mission) -> MissionRun:
    """Ejecuta la misión: crea MissionRun + corre el workflow (sincrónico)."""
    if not mission.workflow_id:
        plan_mission(db, mission)

    wf = db.query(Workflow).filter(Workflow.id == mission.workflow_id).first()
    if not wf:
        raise ValueError(f"Workflow no encontrado: {mission.workflow_id}")

    run = MissionRun(mission_id=mission.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    mission.status = "running"
    mission.started_at = datetime.utcnow()
    db.commit()

    try:
        wf_run = workflow_engine.execute_workflow(db, wf.id)
        run.workflow_run_id = wf_run.id
        # El engine usa "paused" para approval gates → exponer como waiting_approval
        run.status = "waiting_approval" if wf_run.status == "paused" else wf_run.status
        # Snapshot de costos desde step_results (workflow_engine acumula cost por step)
        total_cost = 0.0
        for step in (wf_run.step_results or []):
            total_cost += float(step.get("cost") or 0.0)
        run.cost_usd = {"llm": round(total_cost, 4), "tools": 0.0, "total": round(total_cost, 4)}
        if run.status == "completed":
            mission.status = "completed"
            mission.completed_at = datetime.utcnow()
        elif run.status == "waiting_approval":
            mission.status = "waiting_approval"
        else:
            mission.status = "failed"
            run.error = wf_run.error
        db.commit()
    except Exception as e:  # noqa: BLE001 — registro y estado failed
        log.exception("Mission run failed")
        run.status = "failed"
        run.error = str(e)
        mission.status = "failed"
        db.commit()

    db.refresh(run)
    db.refresh(mission)
    return run


def approve_mission_step(db: Session, mission_id: str, step_index: int, approved: bool = True) -> MissionRun:
    """Aprueba/rechaza el step waiting_approval actual del workflow de la misión."""
    mission = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not mission:
        raise ValueError("Mission no encontrada")
    if not mission.workflow_id:
        raise ValueError("La misión no tiene workflow")
    wf = db.query(Workflow).filter(Workflow.id == mission.workflow_id).first()
    if not wf:
        raise ValueError("Workflow no encontrado")
    # Último run activo
    run = (
        db.query(MissionRun)
        .filter(MissionRun.mission_id == mission.id)
        .order_by(MissionRun.started_at.desc())
        .first()
    )
    if not run or not run.workflow_run_id:
        raise ValueError("La misión no tiene runs activos")
    wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == run.workflow_run_id).first()
    if not wf_run:
        raise ValueError("WorkflowRun no encontrado")

    workflow_engine.approve_step(db, wf_run, step_index, approved)
    # approve_step ya re-ejecuta el workflow internamente si approved
    db.refresh(wf_run)
    run.status = "waiting_approval" if wf_run.status == "paused" else wf_run.status
    if run.status == "completed":
        mission.status = "completed"
        mission.completed_at = datetime.utcnow()
    elif run.status == "cancelled":
        mission.status = "cancelled"
    elif run.status == "failed":
        mission.status = "failed"
    else:
        mission.status = "waiting_approval" if run.status == "waiting_approval" else "running"
    db.commit()
    db.refresh(run)
    return run


def list_missions(db: Session, status: Optional[str] = None, type: Optional[str] = None, limit: int = 50) -> List[Mission]:
    q = db.query(Mission).order_by(Mission.created_at.desc())
    if status:
        q = q.filter(Mission.status == status)
    if type:
        q = q.filter(Mission.type == type)
    return q.limit(limit).all()
