from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.agent import Agent
from app.models.task import Task
from app.models.execution import AgentExecution, ExecutionStatus
from app.services.auth import get_current_user
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
import os


router = APIRouter(prefix="/api/v1/agents", tags=["agents"], dependencies=[Depends(get_current_user)])


def _default_agents_dir() -> str:
    """Resuelve el directorio de identidad de los agentes: repo local en dev, /app en Docker."""
    local = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "agents",
    )
    if os.path.isdir(local):
        return local
    return "/app/agents"


AGENTS_DIR = os.getenv("AGENTS_DIR") or _default_agents_dir()


class AgentResponse(BaseModel):
    id: UUID
    name: str
    emoji: str
    role: str
    status: str
    capabilities: List[str]
    autonomy_level: str
    runtime: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    workspace: Optional[str] = None
    health_status: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    version: Optional[str] = None
    availability: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentTaskResponse(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AgentFile(BaseModel):
    name: str
    content: str


class RunRequest(BaseModel):
    task_id: Optional[UUID] = None
    task_text: Optional[str] = None
    context: Optional[str] = None


class RunResponse(BaseModel):
    execution_id: UUID
    agent_id: UUID
    agent_name: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    runtime: Optional[str] = None
    provider: Optional[str] = None
    usage: Optional[dict] = None
    duration_ms: Optional[int] = None
    simulated: bool = False


@router.get("/", response_model=List[AgentResponse])
def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return agents


@router.get("/runtimes", response_model=List[dict])
def list_runtimes():
    """Runtimes de agentes disponibles (generic, openclaw...) con sus capacidades."""
    from app.adapters.registry import list_runtimes

    return list_runtimes()


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/files", response_model=List[AgentFile])
def get_agent_files(agent_id: UUID, db: Session = Depends(get_db)):
    """Devuelve SOUL.md, AGENTS.md, etc. del agente desde el filesystem."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_dir = os.path.join(AGENTS_DIR, agent.role.value)
    if not os.path.isdir(agent_dir):
        return []

    files = []
    for fname in sorted(os.listdir(agent_dir)):
        if fname.endswith(".md"):
            fpath = os.path.join(agent_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    files.append(AgentFile(name=fname, content=f.read()))
            except Exception:
                continue
    return files


@router.get("/{agent_id}/tasks", response_model=List[AgentTaskResponse])
def get_agent_tasks(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    tasks = db.query(Task).filter(Task.assignee_id == agent_id).all()
    return tasks


@router.get("/{agent_id}/activity")
def get_agent_activity(agent_id: UUID, db: Session = Depends(get_db)):
    from app.models.activity import Activity
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    activities = (
        db.query(Activity)
        .filter(Activity.agent_id == agent_id)
        .order_by(Activity.created_at.desc())
        .all()
    )
    return activities


@router.post("/{agent_id}/run", response_model=RunResponse)
def run_agent(agent_id: UUID, req: RunRequest, db: Session = Depends(get_db)):
    """Ejecuta el agente a través de su ADAPTER de runtime (generic|openclaw|...).

    El harness es token-efficient: recorta system prompt/contexto/tarea a presupuestos
    y registra usage + costo estimado en la ejecución.
    """
    from app.adapters.registry import get_adapter
    from app.adapters.base import AgentIdentity
    from app.services.agent_soul import load_agent_persona

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Resolver el texto de la tarea
    task_text = req.task_text
    if not task_text and req.task_id:
        task = db.query(Task).filter(Task.id == req.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task_text = f"{task.title}\n{task.description or ''}"

    if not task_text:
        raise HTTPException(status_code=400, detail="task_text or task_id required")

    runtime = getattr(agent, "runtime", None)
    runtime_name = runtime.value if hasattr(runtime, "value") else (runtime or "generic")
    provider_name = getattr(agent, "provider", None)
    provider_name = provider_name.value if hasattr(provider_name, "value") else (provider_name or "deepseek")
    model = getattr(agent, "model", None) or None

    adapter = get_adapter(runtime_name)
    if not adapter:
        raise HTTPException(
            status_code=400,
            detail=f"Runtime '{runtime_name}' no tiene adapter registrado. Disponibles: generic, openclaw",
        )

    # Leer SOUL.md (el adapter generic lo recorta a presupuesto de tokens)
    system_prompt = load_agent_persona(agent.role.value)
    if not system_prompt:
        system_prompt = agent.system_prompt or agent.personality or ""

    identity = AgentIdentity(
        agent_id=str(agent.id),
        name=agent.name,
        role=agent.role.value if hasattr(agent.role, "value") else str(agent.role),
        runtime=runtime_name,
        provider=provider_name,
        model=model,
        workspace=getattr(agent, "workspace", None),
        system_prompt=system_prompt,
        capabilities=agent.capabilities or [],
        config=agent.config or {},
    )

    # Registrar ejecución (task_id puede ser None)
    execution = AgentExecution(
        agent_id=agent.id,
        task_id=req.task_id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    from app.models.audit import audit
    audit(db, event_type="task_started", actor=agent.name, actor_type="agent",
          task_id=str(req.task_id) if req.task_id else None,
          metadata={"agent": agent.name, "runtime": runtime_name, "provider": provider_name, "model": model})

    from app.models.agent import AgentStatus
    agent.status = AgentStatus.WORKING
    db.commit()

    try:
        result = adapter.dispatch_task(identity, task_text, req.context)

        if not result.ok or result.status == "failed":
            execution.status = ExecutionStatus.FAILED
            execution.error_message = result.error
            execution.completed_at = datetime.utcnow()
            db.commit()
            agent.status = AgentStatus.ERROR
            db.commit()
            from app.models.audit import audit
            audit(db, event_type="task_failed", actor=agent.name, actor_type="agent",
                  task_id=str(req.task_id) if req.task_id else None,
                  metadata={"agent": agent.name, "error": (result.error or "")[:200]})
            return RunResponse(
                execution_id=execution.id,
                agent_id=agent.id,
                agent_name=agent.name,
                status="failed",
                error=result.error,
                runtime=runtime_name,
                provider=result.provider or provider_name,
                model=result.model or model,
                simulated=result.simulated,
            )

        execution.status = ExecutionStatus.COMPLETED
        execution.output = result.output
        execution.completed_at = datetime.utcnow()
        db.commit()
        agent.status = AgentStatus.IDLE
        agent.last_heartbeat = datetime.utcnow()
        agent.health_status = "online"
        db.commit()

        from app.models.audit import audit
        audit(db, event_type="task_completed", actor=agent.name, actor_type="agent",
              task_id=str(req.task_id) if req.task_id else None,
              metadata={"agent": agent.name, "runtime": runtime_name, "provider": provider_name,
                        "model": result.model or model, "duration_ms": result.duration_ms,
                        "usage": result.usage})

        # Registrar actividad
        try:
            from app.models.activity import Activity
            activity = Activity(
                type="agent_action",
                description=f"🤖 {agent.name} ejecutó tarea: {task_text[:80]}",
                agent_id=agent.id,
            )
            db.add(activity)
            db.commit()
        except Exception:
            pass

        return RunResponse(
            execution_id=execution.id,
            agent_id=agent.id,
            agent_name=agent.name,
            status="completed",
            output=result.output,
            model=result.model or model,
            runtime=runtime_name,
            provider=result.provider or provider_name,
            usage=result.usage,
            duration_ms=result.duration_ms,
            simulated=result.simulated,
        )
    except Exception as e:
        execution.status = ExecutionStatus.FAILED
        execution.error_message = str(e)
        execution.completed_at = datetime.utcnow()
        db.commit()
        agent.status = AgentStatus.ERROR
        db.commit()
        return RunResponse(
            execution_id=execution.id,
            agent_id=agent.id,
            agent_name=agent.name,
            status="failed",
            error=str(e),
            runtime=runtime_name,
            provider=provider_name,
            simulated=False,
        )

