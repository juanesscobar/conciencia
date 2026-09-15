from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Enum, Float, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    COMPLETED = "completed"

class ProjectPriority(str, enum.Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"

class ProjectCategory(str, enum.Enum):
    CORE = "core"
    LEGACY = "legacy"
    PORTFOLIO = "portfolio"
    HARDWARE = "hardware"
    EDUCATION = "education"

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    priority = Column(Enum(ProjectPriority), default=ProjectPriority.P1)
    category = Column(Enum(ProjectCategory), default=ProjectCategory.CORE)
    github_repo = Column(String(255))
    tech_stack = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="project")
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="project", cascade="all, delete-orphan")
