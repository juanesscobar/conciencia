"""Read-only workspace home assembled from existing first-class state."""

from pathlib import Path

from app.models.mission import Mission
from app.models.project import Project
from app.services.capability_readiness import execution_overview


def discover_current_project(cwd: str | Path | None = None) -> dict | None:
    """Find nearest .conciencia project metadata without requiring one."""
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


def workspace_home(db, cwd: str | Path | None = None) -> dict:
    """Build navigation context without duplicating project or mission state."""
    recent_projects = db.query(Project).order_by(Project.updated_at.desc()).limit(4).all()
    recent_missions = db.query(Mission).order_by(Mission.created_at.desc()).limit(3).all()
    active = db.query(Mission).filter(Mission.status.in_(["running", "waiting_approval"])).count()
    approvals = db.query(Mission).filter(Mission.status == "waiting_approval").count()
    return {
        "workspace": "Local Workspace",
        "current_project": discover_current_project(cwd),
        "recent_projects": [
            {"id": str(project.id), "name": project.name, "status": project.status.value}
            for project in recent_projects
        ],
        "recent_missions": [
            {"id": str(mission.id), "name": mission.name, "status": mission.status}
            for mission in recent_missions
        ],
        "active_missions": active,
        "pending_approvals": approvals,
        "execution": execution_overview(db),
    }
