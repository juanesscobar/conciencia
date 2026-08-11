from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Project, Activity
from app.models.activity import ActivityType
from app.schemas import Project as ProjectSchema, ProjectCreate, ProjectUpdate
from app.models.user import User
from app.services.auth import get_current_user
from uuid import UUID

router = APIRouter(prefix="/api/v1/projects", tags=["projects"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=List[ProjectSchema])
def get_projects(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects


@router.post("/", response_model=ProjectSchema)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    # Dedupe por repo de GitHub si viene
    if project.github_repo:
        existing = db.query(Project).filter(Project.github_repo == project.github_repo).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Ya existe el proyecto '{existing.name}' con ese repo")
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    try:
        db.add(Activity(
            project_id=db_project.id,
            type=ActivityType.PROJECT_CREATED,
            description=f"Proyecto creado: {db_project.name}",
        ))
        db.commit()
    except Exception:
        pass
    return db_project


@router.post("/from-github", response_model=ProjectSchema)
def create_project_from_github(
    full_name: str,
    db: Session = Depends(get_db),
):
    """Crea un proyecto a partir de un repo de GitHub (full_name: 'owner/repo')."""
    full_name = full_name.strip().lstrip("@")
    if "/" not in full_name:
        raise HTTPException(status_code=400, detail="full_name debe ser 'owner/repo'")

    existing = db.query(Project).filter(Project.github_repo == full_name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe el proyecto '{existing.name}'")

    name = full_name.split("/")[-1].replace("-", " ").replace("_", " ").title()
    db_project = Project(
        name=name,
        description=f"Proyecto creado desde el repo de GitHub {full_name}",
        github_repo=full_name,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    try:
        db.add(Activity(
            project_id=db_project.id,
            type=ActivityType.PROJECT_CREATED,
            description=f"Proyecto creado desde GitHub: {full_name}",
        ))
        db.commit()
    except Exception:
        pass
    return db_project


@router.post("/from-lead/{lead_id}", response_model=ProjectSchema)
def create_project_from_lead(lead_id: str, db: Session = Depends(get_db)):
    """Convierte un lead generado en proyecto: nombre, notas y vínculo en el timeline del lead."""
    from app.modules.leadhunter.models import Lead
    from app.modules.leadhunter.discovery import add_event

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    existing = db.query(Project).filter(Project.name == lead.company).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe el proyecto '{existing.name}' para este lead")

    db_project = Project(
        name=lead.company,
        description=(
            f"Proyecto generado desde lead ({lead.industry or 'sin sector'} · {lead.region or 'sin región'}).\n"
            f"{lead.notes or ''}"
        ).strip(),
        github_repo=lead.website or None,
    )
    if lead.industry:
        db_project.tech_stack = [lead.industry]
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    db.refresh(db_project)

    try:
        db.add(Activity(
            project_id=db_project.id,
            type=ActivityType.LEAD_CONVERTED,
            description=f"Proyecto creado desde el lead: {lead.company}",
        ))
        db.commit()
    except Exception:
        pass

    # Timeline del lead
    try:
        add_event(db, lead.id, "project_created", f"Lead convertido en proyecto '{db_project.name}' ({db_project.id})")
        db.commit()
    except Exception:
        pass

    return db_project


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectSchema)
def update_project(project_id: UUID, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@router.get("/{project_id}/activity")
def get_project_activity(project_id: UUID, db: Session = Depends(get_db)):
    from app.models import Activity
    activities = db.query(Activity).filter(Activity.project_id == project_id).order_by(Activity.created_at.desc()).all()
    return activities
