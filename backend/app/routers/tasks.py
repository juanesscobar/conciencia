from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Task
from app.schemas import Task as TaskSchema, TaskCreate, TaskUpdate
from app.models.user import User
from app.services.auth import get_current_user
from uuid import UUID

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=List[TaskSchema])
def get_tasks(db: Session = Depends(get_db), skip: int = 0, limit: int = 100, project_id: UUID = None):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    tasks = query.offset(skip).limit(limit).all()
    return tasks

@router.post("/", response_model=TaskSchema)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/{task_id}", response_model=TaskSchema)
def get_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=TaskSchema)
def update_task(task_id: UUID, task_update: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for field, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    
    # Re-evaluar BLOCKED/READY según dependencias y propagar a dependientes
    from app.services.task_dag import refresh_task_status, propagate
    refresh_task_status(db, task)
    db.commit()
    db.refresh(task)
    try:
        propagate(db, str(task.id))
    except Exception:  # noqa: BLE001
        pass
    return task


# ================== Task DAG (dependencias) ==================


class DependencyCreate(BaseModel):
    depends_on_id: str
    kind: Optional[str] = "finish_to_start"


class DependencyResponse(BaseModel):
    id: str
    task_id: str
    depends_on_id: str
    kind: str

    class Config:
        from_attributes = True


@router.get("/{task_id}/dag")
def get_task_dag(task_id: UUID, db: Session = Depends(get_db)):
    """Vista del DAG de la tarea: dependencias, bloqueos y satisfacción."""
    from app.services.task_dag import task_dag

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_dag(db, str(task.id))


@router.post("/{task_id}/dependencies", response_model=DependencyResponse, status_code=201)
def add_task_dependency(task_id: UUID, req: DependencyCreate, db: Session = Depends(get_db)):
    """Crea dependencia: task_id espera a depends_on_id."""
    from app.services.task_dag import add_dependency, propagate

    try:
        dep = add_dependency(db, str(task_id), req.depends_on_id, req.kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.commit()
    db.refresh(dep)
    propagate(db, str(task_id))
    return dep


@router.delete("/{task_id}/dependencies/{depends_on_id}", status_code=204)
def remove_task_dependency(task_id: UUID, depends_on_id: str, db: Session = Depends(get_db)):
    """Elimina la dependencia task_id → depends_on_id."""
    from app.services.task_dag import remove_dependency, propagate

    remove_dependency(db, str(task_id), depends_on_id)
    propagate(db, str(task_id))
    return None

@router.delete("/{task_id}")
def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}
