from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, JSON, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class ActivityType(str, enum.Enum):
    COMMIT = "commit"
    PR = "pr"
    DEPLOY = "deploy"
    RELEASE = "release"
    COMMENT = "comment"
    TASK_CHANGE = "task_change"
    AGENT_ACTION = "agent_action"

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"))
    agent_id = Column(Uuid, ForeignKey("agents.id"))
    type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text, nullable=False)
    extra_data = Column(JSON, default=dict)
    external_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="activities")
    agent = relationship("Agent", back_populates="activities")
