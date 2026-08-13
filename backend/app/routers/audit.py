"""Audit router — API de consulta del audit log (append-only)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.audit import AuditEvent, audit, list_audit
from app.models.user import User
from app.services.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/audit", tags=["audit"], dependencies=[Depends(get_current_user)])


class AuditCreate(BaseModel):
    event_type: str
    actor: Optional[str] = None
    actor_type: str = "user"
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    payload: Optional[dict] = None
    correlation_id: Optional[str] = None


class AuditResponse(BaseModel):
    id: str
    timestamp: Optional[str] = None
    actor: Optional[str] = None
    actor_type: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    event_type: str
    payload: dict
    correlation_id: Optional[str] = None


@router.get("/", response_model=List[AuditResponse])
def get_audit(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    actor: Optional[str] = None,
    event_type: Optional[str] = None,
    project_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Consulta el audit log (solo lectura; append-only)."""
    events = list_audit(
        db, limit=limit, offset=offset, actor=actor, event_type=event_type,
        project_id=project_id, correlation_id=correlation_id,
    )
    return [AuditResponse(**e.to_dict()) for e in events]


@router.post("/", response_model=AuditResponse, status_code=201)
def create_audit_event(req: AuditCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Registra un evento de auditoría manual (para integraciones externas)."""
    event = audit(
        db,
        event_type=req.event_type,
        actor=req.actor or str(user.id),
        actor_type=req.actor_type,
        project_id=req.project_id,
        task_id=req.task_id,
        metadata=req.payload,
        correlation_id=req.correlation_id,
    )
    return AuditResponse(**event.to_dict())
