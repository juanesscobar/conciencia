"""Workflows declarativos — orquestan steps con agente, capabilities, timeout,
retry, approval requerida y costo máximo.

Estado: draft → running → paused → completed / failed / cancelled
Cada step: pending → running → waiting_approval → approved/rejected → completed/failed
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.orm import Session

from app.database import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(200), nullable=False)
    project_id = Column(String(50), nullable=True)
    definition = Column(JSON, nullable=False, default=list)   # [ {step...} ]
    status = Column(String(20), default="draft")              # draft|running|paused|completed|failed|cancelled
    current_step = Column(Integer, default=0)
    error = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "definition": self.definition,
            "status": self.status,
            "current_step": self.current_step,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class WorkflowRun(Base):
    """Ejecución concreta de un workflow: estado por step y resultados."""
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    workflow_id = Column(String, nullable=False, index=True)
    status = Column(String(20), default="running")
    step_results = Column(JSON, default=list)     # [{step_index, step_name, status, output, error, cost}]
    current_step = Column(Integer, default=0)
    paused_at = Column(DateTime, nullable=True)
    error = Column(String(500), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "step_results": self.step_results or [],
            "current_step": self.current_step,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def create_workflow(db: Session, *, name: str, project_id: str | None, definition: list) -> Workflow:
    wf = Workflow(name=name, project_id=project_id, definition=definition)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


def start_run(db: Session, workflow: Workflow) -> WorkflowRun:
    run = WorkflowRun(workflow_id=workflow.id, status="running")
    db.add(run)
    workflow.status = "running"
    workflow.started_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run
