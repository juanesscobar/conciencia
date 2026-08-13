"""Audit log append-only: todo evento importante de la plataforma.

Reglas:
- Solo se inserta (append-only); nunca update/delete desde la aplicación.
- Cada evento tiene actor, tipo, proyecto/tarea opcionales y metadata JSON.
- correlation_id permite agrupar eventos de una misma operación/workflow.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON, Index
from sqlalchemy.orm import Session

from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_ts", "timestamp"),
        Index("ix_audit_type", "event_type"),
        Index("ix_audit_actor", "actor"),
    )

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor = Column(String(100), nullable=True)          # user id, agent id, "system", "webhook"
    actor_type = Column(String(20), default="user")     # user | agent | system | webhook | api_key
    project_id = Column(String(50), nullable=True)
    task_id = Column(String(50), nullable=True)
    event_type = Column(String(80), nullable=False)     # task_created, approval_granted, deployment_started...
    payload = Column(JSON, default=dict)
    correlation_id = Column(String(50), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "payload": self.payload or {},
            "correlation_id": self.correlation_id,
        }


def audit(
    db: Session,
    *,
    event_type: str,
    actor: str = "system",
    actor_type: str = "system",
    project_id: str | None = None,
    task_id: str | None = None,
    metadata: dict | None = None,
    correlation_id: str | None = None,
    commit: bool = True,
) -> AuditEvent:
    """Registra un evento de auditoría (append-only)."""
    event = AuditEvent(
        actor=actor,
        actor_type=actor_type,
        project_id=project_id,
        task_id=task_id,
        event_type=event_type,
        payload=metadata or {},
        correlation_id=correlation_id or uuid.uuid4().hex[:16],
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event


def list_audit(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    actor: str | None = None,
    event_type: str | None = None,
    project_id: str | None = None,
    correlation_id: str | None = None,
) -> list[AuditEvent]:
    query = db.query(AuditEvent)
    if actor:
        query = query.filter(AuditEvent.actor == actor)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if project_id:
        query = query.filter(AuditEvent.project_id == project_id)
    if correlation_id:
        query = query.filter(AuditEvent.correlation_id == correlation_id)
    return query.order_by(AuditEvent.timestamp.desc()).offset(offset).limit(limit).all()
