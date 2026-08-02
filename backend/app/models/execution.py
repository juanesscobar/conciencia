from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_id = Column(Uuid, ForeignKey("agents.id"), nullable=False)
    task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    output = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="executions")
    task = relationship("Task", back_populates="executions")
