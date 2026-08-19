"""Context Packs API (spec §28-30): generar desde datos reales + exportar.

Generación: junta Project + tasks + decisions + memories recientes
en una estructura canónica (Context Pack). Export: markdown (prompt
para coding agents) o JSON (canonical).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.context_pack import ContextPack
from app.models.decision import Decision
from app.models.project import Project
from app.models.task import Task
from app.models.user_memory import UserMemory

router = APIRouter(prefix="/api/v1/context-packs", tags=["context-packs"])

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


def _db() -> SessionLocal():
    return SessionLocal()


def build_context(project_id: Optional[str] = None) -> dict:
    """Construye el contexto canónico con datos REALES del sistema."""
    db = _db()
    try:
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
    finally:
        db.close()


@router.get("/targets")
def targets():
    return EXPORT_TARGETS


@router.get("/")
def list_packs():
    db = _db()
    try:
        rows = db.query(ContextPack).order_by(ContextPack.created_at.desc()).all()
        return [p.to_dict() for p in rows]
    finally:
        db.close()


@router.post("/", status_code=201)
def create_pack(req: PackCreate):
    db = _db()
    try:
        pack = ContextPack(
            title=req.title.strip(),
            project_id=req.project_id,
            target=req.target,
            content=build_context(req.project_id),
        )
        db.add(pack)
        db.commit()
        db.refresh(pack)
        return pack.to_dict()
    finally:
        db.close()


@router.post("/generate", status_code=201)
def generate_pack(req: PackGenerate):
    """Genera un Context Pack desde datos reales (spec §35)."""
    db = _db()
    try:
        title = req.title or "Context Pack"
        pack = ContextPack(
            title=title.strip(),
            project_id=req.project_id,
            source="assistant",
            content=build_context(req.project_id),
        )
        db.add(pack)
        db.commit()
        db.refresh(pack)
        return pack.to_dict()
    finally:
        db.close()


@router.get("/{pack_id}")
def get_pack(pack_id: str):
    db = _db()
    try:
        pack = db.query(ContextPack).filter(ContextPack.id == pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="Context Pack no encontrado")
        return pack.to_dict()
    finally:
        db.close()


@router.delete("/{pack_id}")
def delete_pack(pack_id: str):
    db = _db()
    try:
        pack = db.query(ContextPack).filter(ContextPack.id == pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="Context Pack no encontrado")
        db.delete(pack)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


def _to_markdown(pack: ContextPack) -> str:
    c = pack.content or {}
    lines = [
        f"# CONTEXT PACK: {pack.title}",
        "",
        f"**Project:** {c.get('project', '-')}",
        f"**Mission:** {c.get('mission') or '-'}",
        "",
        "## Architecture",
    ]
    for a in c.get("architecture") or []:
        lines.append(f"- {a}")
    if c.get("decisions"):
        lines += ["", "## Relevant Decisions"]
        for d in c["decisions"]:
            lines.append(f"- {d}")
    if c.get("constraints"):
        lines += ["", "## Constraints"]
        for cst in c["constraints"]:
            lines.append(f"- {cst}")
    if c.get("tasks"):
        lines += ["", "## Tasks"]
        for t in c["tasks"]:
            lines.append(f"- [{t.get('status', '?')}] {t.get('title', '')}")
    if c.get("memory_snippets"):
        lines += ["", "## Memory"]
        for m in c["memory_snippets"]:
            lines.append(f"- {m}")
    lines += [
        "",
        "## Open Questions",
        *(f"- {q}" for q in (c.get("open_questions") or [])),
        "",
        "## Known Problems",
        *(f"- {p}" for p in (c.get("known_problems") or [])),
        "",
        "_Generated by Conciencia Control Plane. El prompt NO es la memoria: el contexto canónico vive en Conciencia._",
    ]
    return "\n".join(lines)


@router.get("/{pack_id}/export")
def export_pack(pack_id: str, format: str = "markdown"):
    db = _db()
    try:
        pack = db.query(ContextPack).filter(ContextPack.id == pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="Context Pack no encontrado")
        if format == "json":
            return pack.to_dict()
        if format in ("markdown", "md", "prompt"):
            return {"format": "markdown", "content": _to_markdown(pack)}
        raise HTTPException(status_code=400, detail="Formato inválido (markdown|json)")
    finally:
        db.close()
