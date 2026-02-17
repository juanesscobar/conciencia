from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    priority: str = "p1"
    category: str = "core"
    github_repo: Optional[str] = None
    tech_stack: List[str] = []

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    name: Optional[str] = None

class Project(ProjectBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProjectList(BaseModel):
    items: List[Project]
    total: int
