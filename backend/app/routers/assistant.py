"""Ask Conciencia (spec §31-39) - Natural Language Interface -> Control Plane.

El Assistant NO tiene arquitectura propia: consulta los mismos endpoints
(agents, tasks, approvals, costs, traces) y responde con el LLM del harness.
Sugiere acciones que la UI ejecuta por los flujos normales (con policies/approval).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import SessionLocal
from app.services import llm
from app.models.audit import AuditEvent

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

SYSTEM_PROMPT = """Sos CONCIENCIA, el Command Center del Control Plane de una plataforma de trabajo autónomo con agentes de IA.

Respondés preguntas sobre el sistema usando SOLO los datos que te paso (JSON de estado). Reglas:
- OBSERVE: qué está corriendo, qué falló, cuánto se gastó, qué necesita aprobación.
- EXPLAIN: por qué pasó algo, basándote en traces/policies.
- ACT: si el usuario pide una acción, respondé con acciones sugeridas (nunca ejecutes nada vos).
- Nunca inventes datos. Si no sabés, decilo.
- Respuesta corta (máx 120 palabras), en el idioma del usuario, estilo terminal conciso.
- Formato: primero la respuesta, después "ACCIONES:" con líneas tipo "ir /approvals" o "aprobar <id>" si corresponde."""


class AskRequest(BaseModel):
    query: str
    context: Optional[dict] = None  # {route, entity_type, entity_id, entity_name}


def _db() -> SessionLocal:
    return SessionLocal()


def _collect_state() -> dict:
    """Snapshot real del Control Plane (mismos datos que la UI)."""
    from app.models.agent import Agent
    from app.models.task import Task
    from app.models.workflow import WorkflowRun
    from app.models.cost_record import CostRecord
    from app.models.project import Project
    from sqlalchemy import func

    db = _db()
    try:
        agents = db.query(Agent).all()
        tasks = db.query(Task).all()
        pending = db.query(WorkflowRun).filter(WorkflowRun.status == "running").count()
        projects = db.query(Project).count()
        today_cost = db.query(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)) \
            .filter(CostRecord.timestamp >= func.date("now", "start of day")).scalar() or 0.0
        failed = [t.title for t in tasks if str(getattr(t.status, "value", t.status)) == "failed"][:5]
        working = [a.name for a in agents if str(getattr(a.status, "value", a.status)) == "working"]

        return {
            "projects": projects,
            "agents_total": len(agents),
            "agents_working": working,
            "tasks_total": len(tasks),
            "tasks_open": sum(1 for t in tasks if str(getattr(t.status, "value", t.status)) not in ("done", "cancelled")),
            "approvals_pending": pending,
            "failed_tasks": failed,
            "cost_today_usd": round(today_cost, 4),
            "llm_configured": llm.is_configured(),
        }
    finally:
        db.close()


def _audit(query: str, answer: str):
    try:
        db = _db()
        try:
            db.add(AuditEvent(
                actor="assistant",
                actor_type="system",
                event_type="assistant_query",
                payload={"query": query[:500], "answer_len": len(answer)},
            ))
            db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        pass


@router.post("/ask")
def ask(req: AskRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query vacía")

    state = _collect_state()
    ctx = req.context or {}
    ctx_line = ""
    if ctx.get("entity_name"):
        ctx_line = f"\nEl usuario está viendo: {ctx.get('entity_type', 'pantalla')} = {ctx.get('entity_name')}. Interpretá la pregunta en ese contexto."

    task = f"""ESTADO DEL SISTEMA (real): {state}
CONTEXTO UI: {ctx_line}

Pregunta del usuario: {req.query}"""

    result = llm.run_agent(
        agent_name="assistant",
        system_prompt=SYSTEM_PROMPT,
        task=task,
    )

    answer = result.get("output") or "No pude responder (LLM no disponible). Revisá la configuración en Settings → LLM Harness."
    _audit(req.query, answer)

    return {
        "answer": answer,
        "simulated": result.get("simulated", False),
        "model": result.get("model"),
        "provider": result.get("provider"),
        "state": state,
    }
