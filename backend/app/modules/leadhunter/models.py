"""SQLAlchemy models for Lead Hunter module."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Enum, ForeignKey, Table
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
    normalized_name = Column(String, nullable=True, index=True)  # dedupe v2: normalize_company()
    normalized_domain = Column(String, nullable=True, index=True)  # dedupe v2: domain_of(website)
    normalized_phone = Column(String, nullable=True, index=True)  # dedupe v2: norm_phone() (últimos 8 dígitos)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # Clasificación
    source = Column(String, nullable=False, default="manual", index=True)  # manual, conciencia, referral, web, linkedin, overpass...
    industry = Column(String, nullable=True)      # cooperativa, salud, distribuidora, comercio, industria...
    segment = Column(String, nullable=True)       # pyme, mediana, corporativo
    region = Column(String, nullable=True, index=True)  # ciudad/departamento (ej: Asunción, San Lorenzo)
    status = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    score = Column(Integer, nullable=False, default=0)  # 0-100

    # Notas y datos extra
    notes = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)  # payload del webhook / respuestas de diagnóstico
    job_id = Column(String, nullable=True, index=True)  # job de prospección que lo creó

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("LeadEvent", back_populates="lead", cascade="all, delete-orphan", order_by="LeadEvent.created_at.desc()")
    proposals = relationship("LeadProposal", back_populates="lead", cascade="all, delete-orphan", order_by="LeadProposal.created_at.desc()")

    @property
    def online_presence(self) -> dict:
        """Presencia online del lead: qué canales digitales tiene."""
        return {
            "website": bool(self.website),
            "email": bool(self.email),
            "phone": bool(self.phone),
            "social": bool((self.meta or {}).get("social")) if isinstance(self.meta, dict) else False,
        }

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "company": self.company,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "source": self.source,
            "industry": self.industry,
            "segment": self.segment,
            "region": self.region,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "score": self.score,
            "notes": self.notes,
            "metadata": self.meta,
            "online_presence": self.online_presence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return d


class LeadEvent(Base):
    """Timeline de acciones sobre un lead (contactado, propuesta, nota...)."""

    __tablename__ = "lead_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # created, contacted, qualified, proposal_generated, proposal_sent, won, lost, note, imported, enriched
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "event_type": self.event_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LeadProposal(Base):
    """Propuesta comercial generada (IA o manual) para un lead."""

    __tablename__ = "lead_proposals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft | sent
    model = Column(String, nullable=True)  # proveedor/modelo que la generó
    meta = Column(JSON, nullable=True)  # sections del squad, agentes, canal de envío
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="proposals")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "model": self.model,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class LeadHuntRun(Base):
    """Registro de cada corrida de descubrimiento (qué fuente, cuántos leads)."""

    __tablename__ = "lead_hunt_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=True, index=True)  # job padre (LeadHunterJob)
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


class LeadHunterJobStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LeadHunterJob(Base):
    """Job de prospección con criterios: se ejecuta async y permite cancel/retry."""

    __tablename__ = "lead_hunter_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    project_id = Column(String, nullable=True)  # opcional: vínculo a un proyecto MC
    status = Column(Enum(LeadHunterJobStatus), nullable=False, default=LeadHunterJobStatus.PENDING, index=True)
    criteria = Column(JSON, nullable=True)  # {source, limit, industry, region, segment...}
    progress = Column(String, nullable=True)  # searching | extracting | validating | scoring | done
    results_count = Column(Integer, nullable=False, default=0)
    duplicates_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)  # detalle de resultados por fuente
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    runs = relationship("LeadHuntRun", primaryjoin="foreign(LeadHuntRun.job_id)==LeadHunterJob.id", viewonly=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "criteria": self.criteria,
            "progress": self.progress,
            "results_count": self.results_count,
            "duplicates_count": self.duplicates_count,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# Tabla asociativa: leads que pertenecen a cada lista guardada
lead_list_members = Table(
    "lead_list_members",
    Base.metadata,
    Column("list_id", String, ForeignKey("lead_lists.id", ondelete="CASCADE"), primary_key=True),
    Column("lead_id", String, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
)


class LeadList(Base):
    """Lista guardada de leads (ej: "Distribuidoras Gran Asunción", "Seguimiento marzo")."""

    __tablename__ = "lead_lists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("Lead", secondary=lead_list_members, lazy="selectin")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "lead_count": len(self.leads) if self.leads else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LeadSavedSearch(Base):
    """Búsqueda guardada: snapshot de los filtros de la tabla de leads."""

    __tablename__ = "lead_saved_searches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    filters = Column(JSON, nullable=False, default=dict)  # {search, status, source, region, segment, industry, online, age_days, min_score, sort}
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "filters": self.filters or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
