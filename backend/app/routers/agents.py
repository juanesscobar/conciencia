from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.agent import Agent
from app.models.task import Task
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AgentResponse(BaseModel):
    id: UUID
    name: str
    emoji: str
    role: str
    status: str
    capabilities: List[str]
    autonomy_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentTaskResponse(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/", response_model=List[AgentResponse])
def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/tasks", response_model=List[AgentTaskResponse])
def get_agent_tasks(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    tasks = db.query(Task).filter(Task.assignee_id == agent_id).all()
    return tasks


@router.get("/{agent_id}/activity")
def get_agent_activity(agent_id: UUID, db: Session = Depends(get_db)):
    from app.models.activity import Activity
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    activities = (
        db.query(Activity)
        .filter(Activity.agent_id == agent_id)
        .order_by(Activity.created_at.desc())
        .all()
    )
    return activities
