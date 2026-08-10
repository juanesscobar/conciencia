"""SQLAlchemy models for Lead Hunter module."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class LeadStatus(str, PyEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class Lead(Base):
    """Cliente potencial: empresa, contacto, fuente, score y pipeline."""

    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Datos de contacto
    company = Column(String, nullable=False, index=True)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # Clasificación
    source = Column(String, nullable=False, default="manual", index=True)  # manual, conciencia, referral, web, linkedin, other
    industry = Column(String, nullable=True)      # cooperativa, salud, distribuidora, comercio, industria...
    segment = Column(String, nullable=True)       # pyme, mediana, corporativo
    status = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    score = Column(Integer, nullable=False, default=0)  # 0-100

    # Notas y datos extra
    notes = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)  # payload del webhook / respuestas de diagnóstico

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "source": self.source,
            "industry": self.industry,
            "segment": self.segment,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "score": self.score,
            "notes": self.notes,
            "metadata": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LeadHuntRun(Base):
    """Registro de cada corrida de descubrimiento (qué fuente, cuántos leads)."""

    __tablename__ = "lead_hunt_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="running")  # running | completed | error
    found = Column(Integer, nullable=False, default=0)
    added = Column(Integer, nullable=False, default=0)
    duplicates = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "status": self.status,
            "found": self.found,
            "added": self.added,
            "duplicates": self.duplicates,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
