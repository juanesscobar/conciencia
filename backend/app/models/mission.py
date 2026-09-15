"""Mission — unidad central de trabajo orquestado (master prompt §4).

Una Mission es UNA unidad de trabajo tecnológico con objetivo, contexto,
agentes, workflow, runtime, presupuesto, criterios de éxito, evidencia y
outcome. NO reemplaza Task/Workflow/AgentExecution: los REFERENCIA.

Nota de diseño: type/status usan String (no Enum de Postgres) para evitar
migrations ALTER TYPE en prod (lección: enum agentrole mordió en deploy).
La validación de valores se hace en Pydantic/schema.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base

# Tipos de misión (master prompt §5) — extensibles, validados en schema
MISSION_TYPES = [
    "research", "software-development", "code-review", "debugging",
    "architecture", "testing", "devops", "deployment", "technical-audit",
    "agent-design", "workflow-design", "automation", "integration",
    "data-analysis", "product-research", "competitive-research",
    "technical-discovery", "lead-research", "technical-proposal",
]

# Estados del ciclo de vida
MISSION_STATUSES = [
    "draft", "planned", "ready", "running", "paused",
    "waiting_approval", "completed", "failed", "cancelled",
]


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    objective = Column(Text, nullable=False)

    type = Column(String(50), default="research")        # MISSION_TYPES
    status = Column(String(20), default="draft")          # MISSION_STATUSES

    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=True)
    requester_id = Column(Uuid, ForeignKey("users.id"), nullable=True)
    context_pack_id = Column(String(50), nullable=True)   # ContextPack usa String hex
    workflow_id = Column(String(50), nullable=True)       # Workflow usa String hex
    team_id = Column(String(50), nullable=True)           # Fase F: Team como string (mismo patrón que workflow_id)
    harness_id = Column(String(50), nullable=True)        # Fase G: Harness versionado como string

    # Agentes seleccionados (ids UUID como strings), runtime, presupuesto
    agent_ids = Column(JSON, default=list)
    runtime = Column(String(50), default="generic")       # AGENT_RUNTIMES
    budget = Column(JSON, default=dict)                   # {cost_limit, token_limit, runtime_limit}
    approval_policy = Column(JSON, default=dict)          # {require_approval: bool, approvers: []}

    # Criterios de éxito / evidencia / outcome
    success_criteria = Column(JSON, default=list)
    evidence_ids = Column(JSON, default=list)
    outcome = Column(JSON, default=dict)                  # {summary, metrics, artifacts}

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="missions")
    runs = relationship("MissionRun", back_populates="mission", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "objective": self.objective,
            "type": self.type,
            "status": self.status,
            "project_id": str(self.project_id) if self.project_id else None,
            "requester_id": str(self.requester_id) if self.requester_id else None,
            "context_pack_id": self.context_pack_id,
            "workflow_id": self.workflow_id,
            "team_id": self.team_id,
            "harness_id": self.harness_id,
            "agent_ids": self.agent_ids or [],
            "runtime": self.runtime,
            "budget": self.budget or {},
            "approval_policy": self.approval_policy or {},
            "success_criteria": self.success_criteria or [],
            "evidence_ids": self.evidence_ids or [],
            "outcome": self.outcome or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class MissionRun(Base):
    """Ejecución concreta de una Mission — snapshot de estado, logs y costos.

    Reusa la lógica de WorkflowRun/AgentExecution; esta tabla es la vista
    de misión para observabilidad CLI (run list / run watch).
    """
    __tablename__ = "mission_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id = Column(Uuid, ForeignKey("missions.id"), nullable=False, index=True)
    workflow_run_id = Column(String(50), nullable=True)   # WorkflowRun usa String hex

    status = Column(String(20), default="pending")        # pending|running|waiting_approval|completed|failed|cancelled
    logs = Column(JSON, default=list)                     # [{ts, level, message}]
    tokens = Column(JSON, default=dict)                   # {prompt, completion, total}
    cost_usd = Column(JSON, default=dict)                 # {llm, tools, total}
    external_costs = Column(JSON, default=list)           # Fase L: [{tool, cost_usd, detail, ts}]
    error = Column(Text)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    mission = relationship("Mission", back_populates="runs")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "mission_id": str(self.mission_id),
            "workflow_run_id": self.workflow_run_id,
            "status": self.status,
            "logs": self.logs or [],
            "tokens": self.tokens or {},
            "cost_usd": self.cost_usd or {},
            "external_costs": self.external_costs or [],
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
