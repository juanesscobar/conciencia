from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Float, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class MetricCategory(str, enum.Enum):
    INDUSTRY = "industry"
    PERSONAL = "personal"
    CUSTOM = "custom"

class MetricPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"))
    agent_id = Column(Uuid, ForeignKey("agents.id"))
    category = Column(Enum(MetricCategory), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    target = Column(Float)
    unit = Column(String(50))
    period = Column(Enum(MetricPeriod), default=MetricPeriod.DAILY)
    source = Column(String(100))
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="metrics")
