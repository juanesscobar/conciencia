from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class DeliverableBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "report"
    status: str = "draft"
    url: Optional[str] = None
    external_id: Optional[str] = None
    author_type: Optional[str] = "agent"
    author_id: Optional[UUID] = None


class DeliverableCreate(DeliverableBase):
    project_id: UUID
    sprint_id: Optional[UUID] = None
    task_id: Optional[UUID] = None


class DeliverableUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None
    external_id: Optional[str] = None
    sprint_id: Optional[UUID] = None
    task_id: Optional[UUID] = None


class Deliverable(DeliverableBase):
    id: UUID
    project_id: UUID
    sprint_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
