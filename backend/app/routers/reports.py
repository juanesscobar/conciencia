from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Project, Task, Sprint, Deliverable
from app.schemas import Deliverable as DeliverableSchema, DeliverableCreate, DeliverableUpdate
from app.integrations.github import github_client
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/api/v1", tags=["reports"])


# ============================================================
# ENTREGABLES (CRUD)
# ============================================================

@router.get("/deliverables", response_model=List[DeliverableSchema])
def list_deliverables(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[UUID] = None,
    sprint_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    status: Optional[str] = None,
):
    query = db.query(Deliverable)
    if project_id:
        query = query.filter(Deliverable.project_id == project_id)
    if sprint_id:
        query = query.filter(Deliverable.sprint_id == sprint_id)
    if task_id:
        query = query.filter(Deliverable.task_id == task_id)
    if status:
        query = query.filter(Deliverable.status == status)
    return query.order_by(Deliverable.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/deliverables", response_model=DeliverableSchema)
def create_deliverable(deliverable: DeliverableCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == deliverable.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_deliverable = Deliverable(**deliverable.model_dump())
    db.add(db_deliverable)
    db.commit()
    db.refresh(db_deliverable)
    return db_deliverable


@router.get("/deliverables/{deliverable_id}", response_model=DeliverableSchema)
def get_deliverable(deliverable_id: UUID, db: Session = Depends(get_db)):
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return deliverable


@router.put("/deliverables/{deliverable_id}", response_model=DeliverableSchema)
def update_deliverable(deliverable_id: UUID, update: DeliverableUpdate, db: Session = Depends(get_db)):
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(deliverable, field, value)
    db.commit()
    db.refresh(deliverable)
    return deliverable


@router.delete("/deliverables/{deliverable_id}")
def delete_deliverable(deliverable_id: UUID, db: Session = Depends(get_db)):
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    db.delete(deliverable)
    db.commit()
    return {"message": "Deliverable deleted"}


# ============================================================
# INFORME DE SPRINT (consolidado)
# ============================================================

@router.get("/reports/sprint/{sprint_id}")
async def sprint_report(sprint_id: UUID, db: Session = Depends(get_db)):
    """Consolida: sprint + tareas por estado + entregables + commits/PRs de GitHub."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    project = db.query(Project).filter(Project.id == sprint.project_id).first()
    tasks = db.query(Task).filter(Task.sprint_id == sprint_id).all()

    # Tareas agrupadas por estado
    status_counts = {}
    for task in tasks:
        status_counts[task.status.value if hasattr(task.status, "value") else str(task.status)] = (
            status_counts.get(task.status.value if hasattr(task.status, "value") else str(task.status), 0) + 1
        )

    done_tasks = [t for t in tasks if getattr(t.status, "value", str(t.status)) == "done"]
    total_hours = sum(float(t.estimated_hours or 0) for t in tasks)
    done_hours = sum(float(t.estimated_hours or 0) for t in done_tasks)

    deliverables = db.query(Deliverable).filter(Deliverable.sprint_id == sprint_id).all()

    # GitHub: commits + PRs mergeados del repo del proyecto
    github_data = {"commits": [], "merged_pulls": [], "error": None}
    if project and project.github_repo:
        try:
            commits = await github_client.get_repo_commits(project.github_repo, per_page=30)
            github_data["commits"] = [
                {
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0][:120],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                    "url": c["html_url"],
                }
                for c in commits
            ]
            pulls = await github_client.get_repo_pulls(project.github_repo, state="closed")
            github_data["merged_pulls"] = [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "merged_at": pr.get("merged_at"),
                    "url": pr["html_url"],
                }
                for pr in pulls
                if pr.get("merged_at")
            ][:20]
        except Exception as e:
            github_data["error"] = str(e)

    return {
        "sprint": {
            "id": sprint.id,
            "name": sprint.name,
            "goal": sprint.goal,
            "status": getattr(sprint.status, "value", str(sprint.status)),
            "start_date": sprint.start_date,
            "end_date": sprint.end_date,
        },
        "project": {
            "id": project.id if project else None,
            "name": project.name if project else None,
            "github_repo": project.github_repo if project else None,
        },
        "tasks": {
            "total": len(tasks),
            "done": len(done_tasks),
            "by_status": status_counts,
            "completion_pct": round(len(done_tasks) / len(tasks) * 100, 1) if tasks else 0,
            "estimated_hours_total": round(total_hours, 1),
            "estimated_hours_done": round(done_hours, 1),
        },
        "deliverables": [
            {
                "id": d.id,
                "title": d.title,
                "description": d.description,
                "type": getattr(d.type, "value", str(d.type)),
                "status": getattr(d.status, "value", str(d.status)),
                "url": d.url,
                "external_id": d.external_id,
                "created_at": d.created_at,
            }
            for d in deliverables
        ],
        "github": github_data,
    }


# ============================================================
# RESUMEN GENERAL DE PROGRESO
# ============================================================

@router.get("/reports/summary")
def overall_summary(db: Session = Depends(get_db)):
    """Resumen global: proyectos, tareas, entregables, actividad reciente."""
    projects = db.query(Project).all()
    tasks = db.query(Task).all()
    deliverables = db.query(Deliverable).all()
    sprints = db.query(Sprint).all()

    task_by_status = {}
    for t in tasks:
        key = getattr(t.status, "value", str(t.status))
        task_by_status[key] = task_by_status.get(key, 0) + 1

    deliv_by_type = {}
    for d in deliverables:
        key = getattr(d.type, "value", str(d.type))
        deliv_by_type[key] = deliv_by_type.get(key, 0) + 1

    active_sprint = db.query(Sprint).filter(Sprint.status == "active").first()

    return {
        "projects": {"total": len(projects), "active": sum(1 for p in projects if getattr(p.status, "value", "") == "active")},
        "tasks": {
            "total": len(tasks),
            "by_status": task_by_status,
            "done": task_by_status.get("done", 0),
            "completion_pct": round(task_by_status.get("done", 0) / len(tasks) * 100, 1) if tasks else 0,
        },
        "deliverables": {"total": len(deliverables), "by_type": deliv_by_type, "final": sum(1 for d in deliverables if getattr(d.status, "value", "") == "final")},
        "sprints": {"total": len(sprints), "active": active_sprint.name if active_sprint else None},
        "generated_at": datetime.utcnow().isoformat(),
    }
