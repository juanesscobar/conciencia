"""Ask API — texto natural → propuesta de misión (master prompt §9)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services import ask_service
from app.models.mission import Mission

router = APIRouter(prefix="/api/v1/ask", tags=["ask"], dependencies=[Depends(get_current_user)])


class AskRequest(BaseModel):
    text: str


class AskProposal(BaseModel):
    text: str
    mission_type: str
    name: str
    objective: str
    runtime: str
    agents: list
    team: Optional[dict] = None
    workflow: list
    cost_estimate: dict
    success_criteria: list


class AskConfirm(BaseModel):
    proposal: AskProposal
    confirmed: bool = True


@router.post("/", response_model=AskProposal)
def ask( req: AskRequest, db: Session = Depends(get_db)):
    """Convierte texto natural en propuesta de misión (sin crear nada)."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text requerido")
    return ask_service.build_proposal(db, req.text)


@router.post("/create", response_model=dict)
def ask_create(req: AskConfirm, db: Session = Depends(get_db)):
    """Crea la misión si la propuesta fue confirmada."""
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="Propuesta no confirmada")
    mission = ask_service.create_from_proposal(db, req.proposal.model_dump())
    return {"id": str(mission.id), "status": mission.status, "mission": mission.to_dict()}
