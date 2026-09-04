"""Missions API — CRUD + plan + run + approve (Fase B del master prompt)."""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.mission import Mission, MissionRun, MISSION_TYPES, MISSION_STATUSES
from app.services import mission_service

router = APIRouter(prefix="/api/v1/missions", tags=["missions"], dependencies=[Depends(get_current_user)])


# ---------- Schemas ----------

class MissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    objective: str = Field(..., min_length=1)
    description: Optional[str] = None
    type: str = "research"
    project_id: Optional[str] = None
    requester_id: Optional[str] = None
    agent_ids: Optional[List[str]] = None
    team_id: Optional[str] = None
    harness_id: Optional[str] = None
    context_pack_id: Optional[str] = None
    workflow_id: Optional[str] = None
    runtime: str = "generic"
    budget: Optional[dict] = None
    approval_policy: Optional[dict] = None
    success_criteria: Optional[List[str]] = None


class MissionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    objective: str
    type: str
    status: str
    project_id: Optional[str] = None
    requester_id: Optional[str] = None
    context_pack_id: Optional[str] = None
    workflow_id: Optional[str] = None
    team_id: Optional[str] = None
    harness_id: Optional[str] = None
    agent_ids: List[str] = []
    runtime: str
    budget: dict = {}
    approval_policy: dict = {}
    success_criteria: List[str] = []
    evidence_ids: List[str] = []
    outcome: dict = {}
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MissionRunResponse(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    workflow_run_id: Optional[str] = None
    status: str
    logs: List[dict] = []
    tokens: dict = {}
    cost_usd: dict = {}
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    step_index: int
    approved: bool = True


# ---------- Endpoints ----------

@router.get("/types", response_model=List[str])
def mission_types():
    return MISSION_TYPES


@router.get("/statuses", response_model=List[str])
def mission_statuses():
    return MISSION_STATUSES


@router.get("/", response_model=List[MissionResponse])
def list_missions(status: Optional[str] = None, type: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    return mission_service.list_missions(db, status=status, type=type, limit=limit)


@router.post("/", response_model=MissionResponse, status_code=201)
def create_mission(req: MissionCreate, db: Session = Depends(get_db)):
    try:
        m = mission_service.create_mission(
            db,
            name=req.name,
            objective=req.objective,
            description=req.description,
            type=req.type,
            project_id=req.project_id,
            requester_id=req.requester_id,
            agent_ids=req.agent_ids,
            team_id=req.team_id,
            harness_id=req.harness_id,
            context_pack_id=req.context_pack_id,
            workflow_id=req.workflow_id,
            runtime=req.runtime,
            budget=req.budget,
            approval_policy=req.approval_policy,
            success_criteria=req.success_criteria,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return m


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: str, db: Session = Depends(get_db)):
    m = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mission no encontrada")
    return m


@router.delete("/{mission_id}", status_code=204)
def delete_mission(mission_id: str, db: Session = Depends(get_db)):
    m = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mission no encontrada")
    db.delete(m)
    db.commit()
    return None


@router.post("/{mission_id}/plan", response_model=MissionResponse)
def plan_mission(mission_id: str, db: Session = Depends(get_db)):
    m = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mission no encontrada")
    try:
        return mission_service.plan_mission(db, m)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/run", response_model=MissionRunResponse)
def run_mission(mission_id: str, db: Session = Depends(get_db)):
    m = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mission no encontrada")
    try:
        return mission_service.run_mission(db, m)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/approve", response_model=MissionRunResponse)
def approve_mission(mission_id: str, req: ApproveRequest, db: Session = Depends(get_db)):
    try:
        return mission_service.approve_mission_step(db, mission_id, req.step_index, req.approved)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{mission_id}/runs", response_model=List[MissionRunResponse])
def list_runs(mission_id: str, db: Session = Depends(get_db)):
    return db.query(MissionRun).filter(MissionRun.mission_id == uuid.UUID(str(mission_id))).order_by(MissionRun.started_at.desc()).all()
