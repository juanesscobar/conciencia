from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, JSON, Date, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum


class SprintStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    goal = Column(Text, nullable=True)
    status = Column(Enum(SprintStatus), default=SprintStatus.PLANNING)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    goals = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", backref="sprints")
    tasks = relationship("Task", back_populates="sprint")
