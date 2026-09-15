"""Signals API — Fase I: hallazgos de misión trazables con evidencia.

POST   /api/v1/signals/                crear signal (manual, con mission_id + evidences opcionales)
GET    /api/v1/signals/                listar (?mission_id=&type=&status=)
GET    /api/v1/signals/{id}            detalle con evidence
POST   /api/v1/signals/extract         extracción automática desde step outputs de una misión
PATCH  /api/v1/signals/{id}            cambiar status (new|acknowledged|dismissed)
POST   /api/v1/signals/{id}/evidence   agregar evidence
DELETE /api/v1/signals/{id}            eliminar
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.signal import Signal, Evidence, SIGNAL_TYPES
from app.models.mission import Mission
from app.services import signal_service

router = APIRouter(prefix="/api/v1/signals", tags=["signals"], dependencies=[Depends(get_current_user)])


# ---------- Schemas ----------

class EvidenceIn(BaseModel):
    kind: str = "quote"
    content: str = Field(..., min_length=1)
    source: Optional[str] = None


class SignalCreate(BaseModel):
    mission_id: str
    title: str = Field(..., min_length=1, max_length=200)
    type: str = "finding"
    summary: Optional[str] = None
    source_step: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    evidences: Optional[List[EvidenceIn]] = None


class SignalUpdate(BaseModel):
    status: str


class ExtractRequest(BaseModel):
    mission_id: str


class SignalResponse(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID
    type: str
    title: str
    summary: Optional[str] = None
    status: str
    workflow_run_id: Optional[str] = None
    mission_run_id: Optional[str] = None
    source_step: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    evidence: list = []
    created_at: Optional[str] = None


def _to_response(s: Signal) -> SignalResponse:
    return SignalResponse(**s.to_dict())


# ---------- Endpoints ----------

@router.post("/", response_model=SignalResponse, status_code=201)
def create_signal(req: SignalCreate, db: Session = Depends(get_db)):
    try:
        s = signal_service.create_signal(
            db,
            mission_id=req.mission_id,
            title=req.title,
            type=req.type,
            summary=req.summary,
            source_step=req.source_step,
            agent_id=req.agent_id,
            agent_name=req.agent_name,
            evidences=[e.model_dump() for e in req.evidences] if req.evidences else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(s)


@router.post("/extract", response_model=List[SignalResponse])
def extract_signals(req: ExtractRequest, db: Session = Depends(get_db)):
    """Extrae Signals (marcadores SIGNAL:/EVIDENCE:) de los outputs de la misión."""
    mission = db.query(Mission).filter(Mission.id == uuid.UUID(str(req.mission_id))).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission no encontrada")
    created = signal_service.extract_from_mission(db, mission)
    return [_to_response(s) for s in created]


@router.get("/", response_model=List[SignalResponse])
def list_signals(mission_id: Optional[str] = None, type: Optional[str] = None,
                 status: Optional[str] = None, limit: int = 50,
                 db: Session = Depends(get_db)):
    try:
        signals = signal_service.list_signals(db, mission_id=mission_id, type=type,
                                              status=status, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_to_response(s) for s in signals]


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    s = signal_service.get_signal(db, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _to_response(s)


@router.patch("/{signal_id}", response_model=SignalResponse)
def update_signal(signal_id: str, req: SignalUpdate, db: Session = Depends(get_db)):
    s = signal_service.get_signal(db, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    try:
        s = signal_service.update_signal_status(db, s, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(s)


@router.post("/{signal_id}/evidence", response_model=SignalResponse)
def add_evidence(signal_id: str, req: EvidenceIn, db: Session = Depends(get_db)):
    s = signal_service.get_signal(db, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    try:
        signal_service.add_evidence(db, s, kind=req.kind, content=req.content, source=req.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(s)


@router.delete("/{signal_id}", status_code=204)
def delete_signal(signal_id: str, db: Session = Depends(get_db)):
    s = signal_service.get_signal(db, signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    signal_service.delete_signal(db, s)
