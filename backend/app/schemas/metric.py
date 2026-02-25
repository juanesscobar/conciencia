from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class MetricBase(BaseModel):
    name: str
    value: float
    target: Optional[float] = None
    unit: Optional[str] = None
    category: str
    period: str = "daily"
    source: Optional[str] = None

class MetricCreate(MetricBase):
    project_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None

class Metric(MetricBase):
    id: UUID
    project_id: Optional[UUID]
    agent_id: Optional[UUID]
    recorded_at: datetime
    
    class Config:
        from_attributes = True
