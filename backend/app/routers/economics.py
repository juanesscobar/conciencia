"""Economics API — Fase L: economía de misiones inspeccionable (sin billing).

GET /api/v1/economics                    economía global (últimos N días)
GET /api/v1/economics/missions/{id}      economía de una misión
POST /api/v1/economics/external-cost     registrar costo externo (tool) en un run
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services import economics_service

router = APIRouter(prefix="/api/v1/economics", tags=["economics"], dependencies=[Depends(get_current_user)])


class ExternalCostIn(BaseModel):
    mission_run_id: str
    tool: str = Field(..., min_length=1)
    cost_usd: float = Field(..., gt=0)
    detail: Optional[str] = None


@router.get("/")
def platform_economics(days: int = 30, db: Session = Depends(get_db)):
    """Economía global del período: misiones, runs, costos, tokens, outcomes."""
    return economics_service.platform_economics(db, days=max(1, min(days, 365)))


@router.get("/missions/{mission_id}")
def mission_economics(mission_id: str, db: Session = Depends(get_db)):
    """Economía de una misión: runs + agregados por provider/model/runtime."""
    try:
        return economics_service.mission_economics(db, mission_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/external-cost")
def external_cost(req: ExternalCostIn, db: Session = Depends(get_db)):
    """Registra un costo externo (herramienta/servicio) en un MissionRun."""
    try:
        return economics_service.record_external_cost(
            db, mission_run_id=req.mission_run_id, tool=req.tool,
            cost_usd=req.cost_usd, detail=req.detail,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
