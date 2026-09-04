"""Context Packs API (spec §28-30 + Fase J).

Generación: junta Project + tasks + decisions + memories recientes
en una estructura canónica (Context Pack). Export: markdown (prompt
para coding agents) o JSON (canonical).
Fase J (retrieval eficiente): GET /retrieve rankea packs por relevancia al
query; POST /assemble arma contexto acotado (solo lo que entra en max_chars).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from app.routers.auth import get_current_user
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.context_pack import ContextPack
from app.models.decision import Decision
from app.models.project import Project
from app.models.task import Task
from app.models.user_memory import UserMemory
from app.services import context_retrieval

router = APIRouter(prefix="/api/v1/context-packs", tags=["context-packs"], dependencies=[Depends(get_current_user)])

EXPORT_TARGETS = [
    {"id": "claude_code", "label": "Claude Code", "format": "markdown"},
    {"id": "qwen_code", "label": "Qwen Code", "format": "markdown"},
    {"id": "opencode", "label": "OpenCode", "format": "markdown"},
    {"id": "openclaw", "label": "OpenClaw", "format": "markdown"},
    {"id": "chatgpt", "label": "ChatGPT", "format": "markdown"},
    {"id": "json", "label": "JSON (canonical)", "format": "json"},
]


class PackCreate(BaseModel):
    title: str
    project_id: Optional[str] = None
    target: Optional[str] = None


class PackGenerate(BaseModel):
    project_id: Optional[str] = None
    title: Optional[str] = None


class AssembleRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    limit: int = Field(3, ge=1, le=10)
    max_chars: int = Field(6000, ge=1, le=100_000)


def build_context(db: Session, project_id: Optional[str] = None) -> dict:
    """Construye el contexto canónico con datos REALES del sistema."""
    project = db.query(Project).filter(Project.id == project_id).first() if project_id else None

    tasks = []
    if project:
        rows = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).limit(30).all()
        tasks = [
            {"title": t.title, "status": str(t.status.value) if hasattr(t.status, "value") else str(t.status)}
            for t in rows
        ]

    decisions = db.query(Decision).order_by(Decision.number.desc()).limit(12).all()
    decision_refs = [d.to_dict()["ref"] for d in decisions]

    memories = db.query(UserMemory).order_by(UserMemory.created_at.desc()).limit(10).all() \
        if hasattr(UserMemory, "created_at") else []
    memory_lines = []
    for m in memories:
        content = getattr(m, "content", None) or getattr(m, "text", "") or ""
        if content:
            memory_lines.append(str(content)[:300])

    return {
        "project": project.name if project else "Conciencia Platform",
        "project_id": project_id,
        "mission": project.description if project else None,
        "current_task": None,
        "architecture": [
            "Backend: FastAPI + SQLAlchemy",
            "Frontend: React + Vite + Tailwind",
            "Agents: motor DeepSeek/harness multi-proveedor con SOUL.md",
            "Control Plane: missions, agents, workflows, approvals, policies, traces, costs",
        ],
        "decisions": decision_refs,
        "constraints": [
            "No exponer chain-of-thought",
            "Assistant usa el mismo Control Plane (sin arquitectura paralela)",
            "MOCK data nunca como producción",
        ],
        "known_problems": [],
        "open_questions": [],
        "relevant_files": [],
        "recent_activity": [],
        "tasks": tasks,
        "memory_snippets": memory_lines,
    }


@router.get("/targets")
def targets():
    return EXPORT_TARGETS


@router.get("/")
def list_packs(db: Session = Depends(get_db)):
    rows = db.query(ContextPack).order_by(ContextPack.created_at.desc()).all()
    return [p.to_dict() for p in rows]


@router.post("/", status_code=201)
def create_pack(req: PackCreate, db: Session = Depends(get_db)):
    pack = ContextPack(
        title=req.title.strip(),
        project_id=req.project_id,
        target=req.target,
        content=build_context(db, req.project_id),
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack.to_dict()


@router.post("/generate", status_code=201)
def generate_pack(req: PackGenerate, db: Session = Depends(get_db)):
    """Genera un Context Pack desde datos reales (spec §35)."""
    title = req.title or "Context Pack"
    pack = ContextPack(
        title=title.strip(),
        project_id=req.project_id,
        target="json",
        content=build_context(db, req.project_id),
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack.to_dict()


@router.get("/export/{pack_id}")
def export_pack(pack_id: str, target: str = "markdown", db: Session = Depends(get_db)):
    """Exporta un pack como markdown (prompt) o JSON canónico."""
    pack = db.query(ContextPack).filter(ContextPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="ContextPack not found")
    if target == "json":
        return pack.to_dict()
    # markdown: render del contenido canónico como contexto de agente
    lines = [f"# Context Pack: {pack.title}", ""]
    content = pack.content or {}
    if isinstance(content, dict):
        for k, v in content.items():
            lines.append(f"## {k}")
            if isinstance(v, (dict, list)):
                import json
                lines.append(f"```json\n{json.dumps(v, ensure_ascii=False, indent=2)}\n```")
            else:
                lines.append(str(v))
            lines.append("")
    return {"pack_id": pack_id, "title": pack.title, "format": "markdown", "content": "\n".join(lines)}


# ---------- Fase J: retrieval eficiente ----------

@router.get("/retrieve")
def retrieve(query: str, project_id: Optional[str] = None,
             limit: int = Query(3, ge=1, le=10),
             db: Session = Depends(get_db)):
    """ContextPacks rankeados por relevancia al query (Fase J)."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="query requerido")
    return context_retrieval.retrieve_packs(
        db, query=query, project_id=project_id, limit=limit
    )


@router.post("/assemble")
def assemble(req: AssembleRequest, db: Session = Depends(get_db)):
    """Ensambla contexto acotado desde los packs más relevantes (Fase J)."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query requerido")
    return context_retrieval.assemble_context(
        db, query=req.query, project_id=req.project_id,
        limit=req.limit, max_chars=req.max_chars,
    )
