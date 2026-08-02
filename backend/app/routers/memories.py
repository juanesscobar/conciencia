"""
Router de memoria de usuario — cada operador tiene su "memorial" individual.

Endpoints:
  GET    /api/v1/memories          — mis memorias
  POST   /api/v1/memories          — crear memoria
  PUT    /api/v1/memories/{id}     — actualizar
  DELETE /api/v1/memories/{id}     — eliminar
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.models.user_memory import UserMemory
from app.services.auth import get_current_user
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


class MemoryCreate(BaseModel):
    title: str
    content: str
    category: str = "general"


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


class MemoryResponse(BaseModel):
    id: UUID
    title: str
    content: str
    category: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[MemoryResponse])
def get_my_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = None,
):
    query = db.query(UserMemory).filter(UserMemory.user_id == current_user.id)
    if category:
        query = query.filter(UserMemory.category == category)
    return query.order_by(UserMemory.updated_at.desc()).all()


@router.post("/", response_model=MemoryResponse)
def create_memory(
    req: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = UserMemory(
        user_id=current_user.id,
        title=req.title,
        content=req.content,
        category=req.category,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.put("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: UUID,
    req: MemoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = db.query(UserMemory).filter(
        UserMemory.id == memory_id,
        UserMemory.user_id == current_user.id,
    ).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(memory, field, value)
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = db.query(UserMemory).filter(
        UserMemory.id == memory_id,
        UserMemory.user_id == current_user.id,
    ).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    db.delete(memory)
    db.commit()
    return {"message": "Memory deleted"}
