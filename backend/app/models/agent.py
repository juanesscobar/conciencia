from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class AgentRole(str, enum.Enum):
    DEV = "dev"
    OPS = "ops"
    QA = "qa"
    PM = "pm"
    RD = "rd"
    COMMS = "comms"
    FIN = "fin"
    ADMIN = "admin"

class AutonomyLevel(str, enum.Enum):
    FULL = "full"
    PREVIEW = "preview"
    APPROVAL = "approval"

class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    emoji = Column(String(10))
    role = Column(Enum(AgentRole), nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.ACTIVE)
    personality = Column(Text)
    capabilities = Column(JSON, default=list)
    autonomy_level = Column(Enum(AutonomyLevel), default=AutonomyLevel.PREVIEW)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    activities = relationship("Activity", back_populates="agent")
