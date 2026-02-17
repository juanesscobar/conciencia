from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from uuid import UUID

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "backlog"
    priority: str = "medium"
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    github_issue: Optional[str] = None
    github_pr: Optional[str] = None

class TaskCreate(TaskBase):
    project_id: UUID

class TaskUpdate(TaskBase):
    title: Optional[str] = None
    project_id: Optional[UUID] = None

class Task(TaskBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
