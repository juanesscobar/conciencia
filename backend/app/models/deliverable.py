from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum


class DeliverableType(str, enum.Enum):
    REPORT = "report"          # Informe / documento
    COMMIT = "commit"          # Commit entregado
    PR = "pr"                  # Pull request
    BUILD = "build"            # Build / release
    DOC = "doc"                # Documentación
    OTHER = "other"


class DeliverableStatus(str, enum.Enum):
    DRAFT = "draft"
    FINAL = "final"
    REJECTED = "rejected"


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=False)
    sprint_id = Column(Uuid, ForeignKey("sprints.id"), nullable=True)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(Enum(DeliverableType), default=DeliverableType.REPORT)
    status = Column(Enum(DeliverableStatus), default=DeliverableStatus.DRAFT)
    url = Column(String(512), nullable=True)          # Link al artefacto (PR, commit, doc)
    external_id = Column(String(255), nullable=True)  # SHA de commit / número de PR
    author_type = Column(String(10), default="agent")  # agent, user, system
    author_id = Column(Uuid, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", backref="deliverables")
    sprint = relationship("Sprint", backref="deliverables")
    task = relationship("Task", backref="deliverables")
