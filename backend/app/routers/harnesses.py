"""Harnesses API — Fase G: contratos versionados y reutilizables de ejecución.

POST   /api/v1/harnesses/              crear (draft)
GET    /api/v1/harnesses/              listar (?status=active)
GET    /api/v1/harnesses/{id}          detalle (spec + historial)
PATCH  /api/v1/harnesses/{id}          actualizar spec/campos (+new_version → versiona)
POST   /api/v1/harnesses/{id}/activate status=active
POST   /api/v1/harnesses/{id}/archive  status=archived
POST   /api/v1/harnesses/{id}/validate probar un output contra el contrato
DELETE /api/v1/harnesses/{id}          eliminar
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.harness import Harness, HARNESS_STATUSES
from app.services import harness_service

router = APIRouter(prefix="/api/v1/harnesses", tags=["harnesses"], dependencies=[Depends(get_current_user)])


# ---------- Schemas ----------

class HarnessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    version: str = "1.0.0"
    spec: Optional[dict] = None


class HarnessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    spec: Optional[dict] = None
    new_version: Optional[str] = None
    changes: Optional[str] = None


class HarnessResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    description: Optional[str] = None
    spec: dict = {}
    status: str
    versions: list = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class OutputProbe(BaseModel):
    output: str = Field(..., description="Output real del agente a validar contra el contrato")


class ProbeResponse(BaseModel):
    ok: bool
    errors: list


def _to_response(h: Harness) -> HarnessResponse:
    return HarnessResponse(**h.to_dict())


# ---------- Endpoints ----------

@router.post("/", response_model=HarnessResponse, status_code=201)
def create_harness(req: HarnessCreate, db: Session = Depends(get_db)):
    try:
        h = harness_service.create_harness(
            db, name=req.name, description=req.description,
            spec=req.spec, version=req.version,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(h)


@router.get("/", response_model=List[HarnessResponse])
def list_harnesses(status: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        harnesses = harness_service.list_harnesses(db, status=status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_to_response(h) for h in harnesses]


@router.get("/{harness_id}", response_model=HarnessResponse)
def get_harness(harness_id: str, db: Session = Depends(get_db)):
    h = harness_service.get_harness(db, harness_id)
    if not h:
        raise HTTPException(status_code=404, detail="Harness not found")
    return _to_response(h)


@router.patch("/{harness_id}", response_model=HarnessResponse)
def update_harness(harness_id: str, req: HarnessUpdate, db: Session = Depends(get_db)):
    h = harness_service.get_harness(db, harness_id)
    if not h:
        raise HTTPException(status_code=404, detail="Harness not found")
    try:
        h = harness_service.update_harness(
            db, h,
            patch=req.model_dump(exclude_none=True, exclude={"new_version", "changes"}),
            new_version=req.new_version,
            changes=req.changes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(h)


@router.post("/{harness_id}/activate", response_model=HarnessResponse)
def activate_harness(harness_id: str, db: Session = Depends(get_db)):
    h = harness_service.get_harness(db, harness_id)
    if not h:
        raise HTTPException(status_code=404, detail="Harness not found")
    return _to_response(harness_service.set_status(db, h, "active"))


@router.post("/{harness_id}/archive", response_model=HarnessResponse)
def archive_harness(harness_id: str, db: Session = Depends(get_db)):
    h = harness_service.get_harness(db, harness_id)
    if not h:
        raise HTTPException(status_code=404, detail="Harness not found")
    return _to_response(harness_service.set_status(db, h, "archived"))


@router.post("/{harness_id}/validate", response_model=ProbeResponse)
def probe_output(harness_id: str, req: OutputProbe, db: Session = Depends(get_db)):
    h = harness_service.get_harness(db, harness_id)
    if not h:
        raise HTTPException(status_code=404, detail="Harness not found")
    ok, errors = harness_service.validate_output(h, req.output)
    return ProbeResponse(ok=ok, errors=errors)


@router.delete("/{harness_id}", status_code=204)
def delete_harness(harness_id: str, db: Session = Depends(get_db)):
    h = harness_service.get_harness(db, harness_id)
    if not h:
        raise HTTPException(status_code=404, detail="Harness not found")
    harness_service.delete_harness(db, h)
