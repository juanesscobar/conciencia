from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import get_current_user
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Sprint, Project
from uuid import UUID
from datetime import date

router = APIRouter(prefix="/api/v1/sprints", tags=["sprints"], dependencies=[Depends(get_current_user)])


class SprintOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    goal: Optional[str] = None
    status: str
    start_date: date
    end_date: date
    created_at: object

    class Config:
        from_attributes = True


class SprintCreate(BaseModel):
    project_id: UUID
    name: str
    goal: Optional[str] = None
    status: str = "planning"
    start_date: date
    end_date: date


@router.get("/", response_model=List[SprintOut])
def list_sprints(db: Session = Depends(get_db), project_id: Optional[UUID] = None):
    query = db.query(Sprint)
    if project_id:
        query = query.filter(Sprint.project_id == project_id)
    return query.order_by(Sprint.start_date.desc()).all()


@router.post("/", response_model=SprintOut)
def create_sprint(sprint: SprintCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == sprint.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_sprint = Sprint(**sprint.model_dump())
    db.add(db_sprint)
    db.commit()
    db.refresh(db_sprint)
    return db_sprint


@router.get("/{sprint_id}", response_model=SprintOut)
def get_sprint(sprint_id: UUID, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint
