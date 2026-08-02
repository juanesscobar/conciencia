from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.agent import Agent
from app.models.task import Task
from app.models.execution import AgentExecution, ExecutionStatus
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
import os

AGENTS_DIR = os.getenv("AGENTS_DIR", "/app/agents")

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentResponse(BaseModel):
    id: UUID
    name: str
    emoji: str
    role: str
    status: str
    capabilities: List[str]
    autonomy_level: str
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
    simulated: bool = False


@router.get("/", response_model=List[AgentResponse])
def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return agents


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

    agent_dir = os.path.join(AGENTS_DIR, agent.role)
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
    """Ejecuta el agente contra DeepSeek usando su SOUL.md como system prompt."""
    from app.services.llm import run_agent as llm_run

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

    # Leer archivos del agente (SOUL.md, AGENTS.md, etc.)
    agent_dir = os.path.join(AGENTS_DIR, agent.role)
    system_prompt_parts = []
    if os.path.isdir(agent_dir):
        for fname in sorted(os.listdir(agent_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(agent_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        system_prompt_parts.append(
                            f"===== {fname} =====\n{f.read()}\n"
                        )
                except Exception:
                    continue

    if not system_prompt_parts:
        # Fallback: usar personality/system_prompt de la DB
        base = agent.system_prompt or agent.personality or ""
        system_prompt_parts = [f"===== SOUL.md (DB) =====\n{base}\n"]

    system_prompt = "\n".join(system_prompt_parts)

    # Registrar ejecución (task_id puede ser None)
    execution = AgentExecution(
        agent_id=agent.id,
        task_id=req.task_id,  # None si no hay tarea asociada
        status=ExecutionStatus.RUNNING,
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # Cambiar status del agente
    from app.models.agent import AgentStatus
    agent.status = AgentStatus.WORKING
    db.commit()

    try:
        result = llm_run(agent.name, system_prompt, task_text, req.context)

        if result.get("error"):
            execution.status = ExecutionStatus.FAILED
            execution.error_message = result["error"]
            execution.completed_at = datetime.utcnow()
            db.commit()
            agent.status = AgentStatus.ERROR
            db.commit()
            return RunResponse(
                execution_id=execution.id,
                agent_id=agent.id,
                agent_name=agent.name,
                status="failed",
                error=result["error"],
                simulated=False,
            )

        execution.status = ExecutionStatus.COMPLETED
        execution.output = result.get("output")
        execution.completed_at = datetime.utcnow()
        db.commit()
        agent.status = AgentStatus.IDLE
        db.commit()

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
            output=result.get("output"),
            model=result.get("model"),
            simulated=result.get("simulated", False),
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
            simulated=False,
        )
