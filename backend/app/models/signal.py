"""Signal + Evidence — hallazgos trazables de misiones (master prompt §I).

Una Signal es un hallazgo extraído de una misión (insight, riesgo, oportunidad,
decisión...) con trazabilidad completa: de qué misión/run/step/agente salió y
qué Evidence lo respalda (quote del output, URL, dato, resultado de tool).

Trazabilidad:
  Signal.mission_id → Mission
  Signal.workflow_run_id / mission_run_id → ejecución concreta
  Signal.source_step / agent_id → dónde se generó
  Evidence.signal_id → respaldo (kind: output/quote/url/data/tool_result)
  Mission.evidence_ids → agrega los ids de evidence para vista global

Extracción automática: los outputs de los steps pueden incluir marcadores
  SIGNAL: <type>| <título>| <resumen>        (type: insight|risk|opportunity|decision|lead|finding)
  EVIDENCE: <contenido>                       (0..N líneas después de la signal)
→ al completarse una misión se generan Signals con Evidence (DoD Phase I).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base

SIGNAL_TYPES = ["insight", "risk", "opportunity", "decision", "lead", "finding"]
SIGNAL_STATUSES = ["new", "acknowledged", "dismissed"]
EVIDENCE_KINDS = ["output", "quote", "url", "data", "tool_result"]


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id = Column(Uuid, ForeignKey("missions.id"), nullable=False, index=True)
    type = Column(String(30), default="finding")          # SIGNAL_TYPES
    title = Column(String(200), nullable=False)
    summary = Column(Text)
    status = Column(String(20), default="new")            # SIGNAL_STATUSES

    # Trazabilidad de origen
    workflow_run_id = Column(String(50), nullable=True)
    mission_run_id = Column(Uuid, nullable=True)
    source_step = Column(String(100), nullable=True)
    agent_id = Column(Uuid, nullable=True)
    agent_name = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", backref="signals")
    evidences = relationship("Evidence", back_populates="signal", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "mission_id": str(self.mission_id),
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "workflow_run_id": self.workflow_run_id,
            "mission_run_id": str(self.mission_run_id) if self.mission_run_id else None,
            "source_step": self.source_step,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "agent_name": self.agent_name,
            "evidence": [e.to_dict() for e in self.evidences],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    signal_id = Column(Uuid, ForeignKey("signals.id"), nullable=False, index=True)
    kind = Column(String(30), default="quote")            # EVIDENCE_KINDS
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)           # step/agent/URL/archivo
    created_at = Column(DateTime, default=datetime.utcnow)

    signal = relationship("Signal", back_populates="evidences")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "signal_id": str(self.signal_id),
            "kind": self.kind,
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
