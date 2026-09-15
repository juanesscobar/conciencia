"""Read-only Workspace Home assembled from canonical local services."""

from __future__ import annotations

from pathlib import Path
import re

from app.models.activity import Activity
from app.models.mission import Mission, MissionRun
from app.models.project import Project
from app.services.capability_readiness import execution_overview, runtime_readiness


def discover_current_project(cwd: str | Path | None = None) -> dict | None:
    """Find nearest project metadata; its absence never disables the workspace."""
    start = Path(cwd or Path.cwd()).resolve()
    for directory in (start, *start.parents):
        metadata = directory / ".conciencia" / "project.yaml"
        if not metadata.is_file():
            continue
        name = directory.name
        for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("name:"):
                name = line.partition(":")[2].strip() or name
                break
        return {"name": name, "path": str(directory), "metadata": str(metadata)}
    return None


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _project_for_context(db, context: dict | None):
    if not context:
        return None
    wanted = _normalized(context["name"])
    matches = [project for project in db.query(Project).all() if _normalized(project.name) == wanted]
    return matches[0] if len(matches) == 1 else None


def _iso(value):
    return value.isoformat() if value else None


def _project_row(db, project: Project) -> dict:
    active = db.query(Mission).filter(Mission.project_id == project.id, Mission.status.in_(["draft", "planned", "ready", "running", "waiting_approval"])).count()
    attention = db.query(Mission).filter(Mission.project_id == project.id, Mission.status.in_(["failed", "waiting_approval"])).count()
    latest_activity = db.query(Activity).filter(Activity.project_id == project.id).order_by(Activity.created_at.desc()).first()
    return {"name": project.name, "description": project.description or "description unavailable", "status": getattr(project.status, "value", str(project.status)), "last_activity": _iso(latest_activity.created_at if latest_activity else project.updated_at), "active_missions": active, "attention": attention > 0}


def _workforce(db) -> list[dict]:
    from app.core.agent_runtime import get_runtime_configs

    labels = {"codex": "Codex", "claude_code": "Claude Code", "openclaw": "OpenClaw", "generic": "Generic", "mcp": "MCP"}
    configs = {config.name: config for config in get_runtime_configs(db)}
    rows = []
    for name in ("codex", "claude_code", "openclaw", "generic", "mcp"):
        config = configs.get(name)
        if not config:
            continue
        readiness = runtime_readiness(db, name, config=config)
        detail = readiness.get("provider", {}) if name == "generic" else {}
        rows.append({"name": name, "label": labels[name], "state": readiness["state"], "ready": readiness["ready"], "detected": readiness.get("detected", False), "enabled": readiness["enabled"], "provider": detail.get("provider") or None})
    return rows


def workspace_home(db, cwd: str | Path | None = None) -> dict:
    """Aggregate bounded local state. This does not execute agents or network calls."""
    location = Path(cwd or Path.cwd()).resolve()
    context = discover_current_project(location)
    project = _project_for_context(db, context)
    projects = db.query(Project).order_by(Project.updated_at.desc()).limit(5).all()
    active_missions = db.query(Mission).filter(Mission.status.in_(["running", "waiting_approval", "failed", "draft"])).order_by(Mission.created_at.desc()).limit(5).all()
    running_runs = db.query(MissionRun).filter(MissionRun.status.in_(["running", "waiting_approval", "failed"])).order_by(MissionRun.started_at.desc()).limit(5).all()
    from app.services.work_service import collect_work_items
    from app.services.connection_service import list_connections
    from app.services.recommendation_service import recommendations

    recent_work = collect_work_items(db, cwd=str(location))[:5]
    active_count = db.query(Mission).filter(Mission.status.in_(["running", "waiting_approval", "failed", "draft"])).count()
    pending_count = db.query(Mission).filter(Mission.status == "waiting_approval").count()
    project_rows = [_project_row(db, item) for item in projects]
    recent_missions = [
        {"id": str(item.id), "name": item.name, "status": item.status, "type": item.type}
        for item in active_missions
    ]
    return {
        "workspace": "Local Workspace",
        "current": {"kind": "project" if context else "global", "name": project.name if project else (context["name"] if context else "Global workspace"), "registered": bool(project), "path": str(location)},
        "current_project": {"id": str(project.id), "name": project.name} if project else None,
        "active_missions": active_count,
        "pending_approvals": pending_count,
        "execution": execution_overview(db),
        "projects": project_rows,
        "recent_projects": project_rows,
        "recent_missions": recent_missions,
        "workforce": _workforce(db),
        "active_work": ([{"kind": "mission", "name": item.name, "status": item.status} for item in active_missions] + [{"kind": "run", "name": item.error or "Mission run", "status": item.status} for item in running_runs])[:5],
        "recent_work": [{"type": item.type, "title": item.title, "timestamp": _iso(item.timestamp)} for item in recent_work],
        "connections": list_connections(db),
        "recommendations": recommendations(db, cwd=location),
    }
