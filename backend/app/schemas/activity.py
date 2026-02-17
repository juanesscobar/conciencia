from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ActivityBase(BaseModel):
    type: str
    description: str
    metadata: dict = {}
    external_url: Optional[str] = None

class ActivityCreate(ActivityBase):
    project_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None

class Activity(ActivityBase):
    id: UUID
    project_id: Optional[UUID]
    agent_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True
