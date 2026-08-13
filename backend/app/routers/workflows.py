"""Workflow router — crear workflows declarativos y ejecutarlos."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.workflow import Workflow, WorkflowRun, create_workflow
from app.models.user import User
from app.services.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"], dependencies=[Depends(get_current_user)])


class StepDef(BaseModel):
    name: str
    agent_id: Optional[str] = None
    required_capabilities: Optional[List[str]] = None
    task: Optional[str] = None
    context: Optional[str] = None
    approval: bool = False
    timeout: Optional[int] = None
    retries: int = 0
    max_cost: Optional[float] = None


class WorkflowCreate(BaseModel):
    name: str
    project_id: Optional[str] = None
    steps: List[StepDef]


class WorkflowResponse(BaseModel):
    id: str
    name: str
    project_id: Optional[str] = None
    definition: list = []
    status: str
    current_step: int
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class RunResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: Optional[str] = None
    status: str
    step_results: list
    current_step: int
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ApprovalRequest(BaseModel):
    approved: bool


@router.post("/", response_model=WorkflowResponse, status_code=201)
def create_wf(req: WorkflowCreate, db: Session = Depends(get_db)):
    definition = [s.model_dump() for s in req.steps]
    wf = create_workflow(db, name=req.name, project_id=req.project_id, definition=definition)
    return WorkflowResponse(**wf.to_dict())


@router.get("/", response_model=List[WorkflowResponse])
def list_wf(db: Session = Depends(get_db)):
    wfs = db.query(Workflow).order_by(Workflow.created_at.desc()).limit(50).all()
    return [WorkflowResponse(**w.to_dict()) for w in wfs]


@router.get("/{wf_id}", response_model=WorkflowResponse)
def get_wf(wf_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse(**wf.to_dict())


@router.get("/{wf_id}/runs", response_model=List[RunResponse])
def list_runs(wf_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workflow_id == wf_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(20)
        .all()
    )
    return [RunResponse(**r.to_dict()) for r in runs]


@router.post("/{wf_id}/run", response_model=RunResponse)
def run_wf(wf_id: str, db: Session = Depends(get_db)):
    from app.services.workflow_engine import execute_workflow

    wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status in ("running", "paused"):
        raise HTTPException(status_code=409, detail="Workflow ya está corriendo o pausado con aprobación pendiente")
    try:
        run = execute_workflow(db, wf.id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)[:300])
    return RunResponse(**run.to_dict())


@router.get("/runs/pending", response_model=List[RunResponse])
def pending_approvals(db: Session = Depends(get_db)):
    """Runs pausados esperando aprobación humana (cola de approval gates)."""
    runs = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.status == "paused")
        .order_by(WorkflowRun.started_at.desc())
        .limit(50)
        .all()
    )
    names = {
        w.id: w.name
        for w in db.query(Workflow).filter(Workflow.id.in_([r.workflow_id for r in runs])).all()
    }
    return [RunResponse(**r.to_dict(), workflow_name=names.get(r.workflow_id)) for r in runs]


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(**run.to_dict())


@router.post("/runs/{run_id}/approve", response_model=RunResponse)
def approve_run(run_id: str, req: ApprovalRequest, db: Session = Depends(get_db)):
    from app.services.workflow_engine import approve_step

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run = approve_step(db, run, run.current_step, req.approved)
    return RunResponse(**run.to_dict())


@router.post("/runs/{run_id}/pause", response_model=RunResponse)
def pause_run(run_id: str, db: Session = Depends(get_db)):
    from app.services.workflow_engine import pause_run as _pause

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run = _pause(db, run)
    return RunResponse(**run.to_dict())


@router.post("/runs/{run_id}/cancel", response_model=RunResponse)
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    from app.services.workflow_engine import cancel_run as _cancel

    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run = _cancel(db, run)
    return RunResponse(**run.to_dict())
