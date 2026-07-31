from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, JSON, Numeric, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskType(str, enum.Enum):
    FEATURE = "feature"
    BUG = "bug"
    RESEARCH = "research"
    CONTENT = "content"
    OPS = "ops"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=False)
    sprint_id = Column(Uuid, ForeignKey("sprints.id"), nullable=True)
    parent_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.BACKLOG)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    type = Column(Enum(TaskType), default=TaskType.FEATURE)
    
    assignee_type = Column(String(10))  # agent, user
    assignee_id = Column(Uuid, ForeignKey("agents.id"), nullable=True)
    
    due_date = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    estimated_hours = Column(Numeric(5, 2))
    actual_hours = Column(Numeric(5, 2))
    
    github_issue = Column(String(255))
    github_pr = Column(String(255))
    
    custom_fields = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assigned_agent = relationship("Agent", back_populates="tasks", foreign_keys="Task.assignee_id")
    executions = relationship("AgentExecution", back_populates="task")
    subtasks = relationship("Task", backref="parent", remote_side="Task.id")
    sprint = relationship("Sprint", back_populates="tasks")
