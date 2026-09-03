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
        {
            "name": "discovery",
            "parallel": True,
            "max_parallel": 2,
            "steps": [
                {"name": "discover-leads", "capabilities": ["leads.read", "search.execute"], "timeout": 600, "retry": 2},
                {"name": "enrich-websites", "capabilities": ["website_fetch"], "timeout": 600, "retry": 2},
            ],
        },
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
    team_id: Optional[str] = None,
    harness_id: Optional[str] = None,
    context_pack_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    runtime: str = "generic",
    budget: Optional[dict] = None,
    approval_policy: Optional[dict] = None,
    success_criteria: Optional[List[str]] = None,
) -> Mission:
    if type not in MISSION_TYPES:
        raise ValueError(f"Tipo de misión inválido: {type}. Válidos: {', '.join(MISSION_TYPES)}")

    # Fase F: si la misión apunta a un team → runtime default del team y
    # agent_ids se pueblan con los miembros (a menos que vengan explícitos).
    team_members: List[str] = []
    if team_id:
        from app.services import team_service

        team = team_service.get_team(db, team_id)
        if not team:
            raise ValueError(f"Team no encontrado: {team_id}")
        if team.status != "active":
            raise ValueError(f"Team '{team.name}' no está activo (status: {team.status})")
        if not runtime or runtime == "generic":
            runtime = team.default_runtime or "generic"
        team_members = [str(m) for m in (team.member_ids or [])]

    # Fase G: validar harness existente y activo
    if harness_id:
        from app.services import harness_service

        harness = harness_service.get_harness(db, harness_id)
        if not harness:
            raise ValueError(f"Harness no encontrado: {harness_id}")
        if harness.status != "active":
            raise ValueError(f"Harness '{harness.name}' no está activo (status: {harness.status})")

    if context_pack_id:
        from app.models.context_pack import ContextPack

        pack = db.query(ContextPack).filter(ContextPack.id == context_pack_id).first()
        if not pack:
            raise ValueError(f"Context Pack no encontrado: {context_pack_id}")
        if (pack.project_id or project_id) and str(pack.project_id or "") != str(project_id or ""):
            raise ValueError(
                f"Context Pack {context_pack_id} no pertenece al proyecto de la misión"
            )

    # Fase K: la misión puede referenciar un workflow existente (custom)
    if workflow_id:
        from app.models.workflow import Workflow

        wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not wf:
            raise ValueError(f"Workflow no encontrado: {workflow_id}")

    mission = Mission(
        name=name,
        objective=objective,
        description=description,
        type=type,
        status="draft",
        project_id=project_id,
        requester_id=requester_id,
        agent_ids=agent_ids or team_members or [],
        team_id=team_id,
        harness_id=harness_id,
        context_pack_id=context_pack_id,
        workflow_id=workflow_id,
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
    if mission.status in ("running", "waiting_approval"):
        raise ValueError(
            f"La misión ya tiene una ejecución activa (status={mission.status})"
        )
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
        mission_ctx = _mission_context(db, mission)
        wf_run = workflow_engine.execute_workflow(
            db, wf.id, team_id=mission.team_id,
            harness_id=mission.harness_id, mission_ctx=mission_ctx,
            agent_pool=[str(a) for a in (mission.agent_ids or [])] or None,
        )
        _sync_mission_run(db, mission, run, wf_run, mission_ctx)

        # Fase I: extraer Signals (marcadores SIGNAL:/EVIDENCE:) al completar
        if run.status == "completed":
            try:
                from app.services import signal_service

                signal_service.extract_from_mission(db, mission, mission_run=run)
            except Exception:  # noqa: BLE001 — la extracción nunca rompe el run
                log.warning("signal extraction failed", exc_info=True)
        # Fase K: promover evidencia WebMCP (steps webmcp) a Signal+Evidence
        # (también mientras espera aprobación — la evidencia ya está en step_results)
        if run.status in ("completed", "waiting_approval"):
            try:
                from app.services.webmcp import promote_step_evidence

                promote_step_evidence(db, mission, wf_run)
            except Exception:  # noqa: BLE001
                log.warning("webmcp evidence promotion failed", exc_info=True)
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

    workflow_engine.approve_step(
        db, wf_run, step_index, approved,
        team_id=mission.team_id,
        harness_id=mission.harness_id,
        mission_ctx=_mission_context(db, mission),
        agent_pool=[str(a) for a in (mission.agent_ids or [])] or None,
    )
    # approve_step ya re-ejecuta el workflow internamente si approved
    db.refresh(wf_run)
    mission_ctx = _mission_context(db, mission)
    _sync_mission_run(db, mission, run, wf_run, mission_ctx)
    if run.status == "completed":
        from app.services import signal_service
        from app.services.webmcp import promote_step_evidence

        signal_service.extract_from_mission(db, mission, mission_run=run)
        promote_step_evidence(db, mission, wf_run)
    db.refresh(run)
    return run


def list_missions(db: Session, status: Optional[str] = None, type: Optional[str] = None, limit: int = 50) -> List[Mission]:
    q = db.query(Mission).order_by(Mission.created_at.desc())
    if status:
        q = q.filter(Mission.status == status)
    if type:
        q = q.filter(Mission.type == type)
    return q.limit(limit).all()


def _event_to_log(e: dict) -> str:
    """Evento estructurado → línea legible de log."""
    parts = [f"[{e.get('type')}]"]
    if e.get("step"):
        parts.append(f"step={e.get('step')}")
    if e.get("agent_name"):
        parts.append(f"agent={e.get('agent_name')}")
    if e.get("runtime"):
        parts.append(f"runtime={e.get('runtime')}")
    if e.get("tokens") and (e.get("tokens") or {}).get("total"):
        parts.append(f"tokens={e['tokens']['total']}")
    if e.get("cost") is not None:
        parts.append(f"cost=${e.get('cost')}")
    if e.get("error"):
        parts.append(f"error={str(e['error'])[:120]}")
    return " ".join(parts)


def _step_tokens(step: dict) -> list:
    """Tokens de un step (incluye children de bloques paralelos)."""
    out = []
    if step.get("tokens"):
        out.append(step["tokens"])
    for child in step.get("children") or []:
        if child.get("tokens"):
            out.append(child["tokens"])
    return out


def _sync_mission_run(db: Session, mission: Mission, run: MissionRun,
                      wf_run: WorkflowRun, mission_ctx: dict) -> None:
    """Sincroniza estado y agregados desde el WorkflowRun canónico."""
    run.workflow_run_id = wf_run.id
    run.status = "waiting_approval" if wf_run.status == "paused" else wf_run.status
    run.logs = [
        {
            "ts": e.get("ts"),
            "level": "error" if e.get("type") in ("step_failed", "workflow_failed") else "info",
            "message": _event_to_log(e),
        }
        for e in (wf_run.events or [])
    ]
    packs_used = mission_ctx.get("context_packs") or []
    if packs_used:
        run.logs.insert(0, {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": "info",
            "message": "[context_packs] " + ", ".join(p.get("title", "?") for p in packs_used),
        })

    totals = {"prompt": 0, "completion": 0, "total": 0}
    for step in (wf_run.step_results or []):
        for tokens in _step_tokens(step):
            for key in totals:
                totals[key] += tokens.get(key) or 0
    run.tokens = totals
    llm_cost = round(sum(float(step.get("cost") or 0.0) for step in (wf_run.step_results or [])), 4)
    run.cost_usd = {"llm": llm_cost, "tools": 0.0, "total": llm_cost}
    run.error = wf_run.error

    if run.status == "waiting_approval":
        mission.status = "waiting_approval"
        run.completed_at = None
    elif run.status in ("completed", "failed", "cancelled"):
        mission.status = run.status
        completed_at = wf_run.completed_at or datetime.utcnow()
        mission.completed_at = completed_at
        run.completed_at = completed_at
    else:
        mission.status = "running"
    db.commit()


def _mission_context(db: Session, mission: Mission) -> dict:
    """Contexto para templates del harness: objective/description/project/context_pack."""
    from app.services import harness_service

    project_name = None
    project_id = str(mission.project_id) if mission.project_id else None
    if mission.project_id:
        from app.models.project import Project

        proj = db.query(Project).filter(Project.id == uuid.UUID(str(mission.project_id))).first()
        if proj:
            project_name = proj.name
    return harness_service.build_mission_context(
        db,
        objective=mission.objective,
        description=mission.description,
        project_name=project_name,
        project_id=project_id,
        context_pack_id=mission.context_pack_id,
    )
