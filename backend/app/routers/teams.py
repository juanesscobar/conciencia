"""Teams API — Fase F: agrupar agentes especializados y enrutar misiones.

POST   /api/v1/teams/                    crear team
GET    /api/v1/teams/                    listar (filtro ?status=)
GET    /api/v1/teams/match               teams que cubren capabilities (?capabilities=a,b,c)
GET    /api/v1/teams/{id}                detalle
PATCH  /api/v1/teams/{id}                actualizar (name/description/purpose/status/runtime/config)
DELETE /api/v1/teams/{id}                eliminar
POST   /api/v1/teams/{id}/members        agregar miembro {"agent_id": ...}
DELETE /api/v1/teams/{id}/members/{agent_id}  quitar miembro
GET    /api/v1/teams/{id}/members        miembros con detalle
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.agent import Agent
from app.models.team import Team, TEAM_STATUSES
from app.services import team_service

router = APIRouter(prefix="/api/v1/teams", tags=["teams"], dependencies=[Depends(get_current_user)])


# ---------- Schemas ----------

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    purpose: Optional[str] = None
    emoji: str = "👥"
    member_ids: Optional[List[str]] = None
    default_runtime: str = "generic"
    config: Optional[dict] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    emoji: Optional[str] = None
    status: Optional[str] = None
    default_runtime: Optional[str] = None
    config: Optional[dict] = None


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    purpose: Optional[str] = None
    emoji: str
    status: str
    member_ids: List[str] = []
    default_runtime: str
    config: dict = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MemberAdd(BaseModel):
    agent_id: str = Field(..., min_length=1)


class MemberResponse(BaseModel):
    id: uuid.UUID
    name: str
    emoji: str
    role: str
    status: str
    capabilities: List[str]
    runtime: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    health_status: Optional[str] = None
    availability: Optional[str] = None


class TeamMatchResponse(BaseModel):
    team_id: str
    name: str
    purpose: Optional[str] = None
    emoji: str
    default_runtime: str
    members_count: int
    coverage: int
    matched_caps: List[str]
    missing_caps: List[str]
    score: int


def _to_response(t: Team) -> TeamResponse:
    return TeamResponse(**t.to_dict())


# ---------- Endpoints ----------

@router.post("/", response_model=TeamResponse, status_code=201)
def create_team(req: TeamCreate, db: Session = Depends(get_db)):
    try:
        team = team_service.create_team(
            db,
            name=req.name,
            description=req.description,
            purpose=req.purpose,
            emoji=req.emoji,
            member_ids=req.member_ids,
            default_runtime=req.default_runtime,
            config=req.config,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(team)


@router.get("/", response_model=List[TeamResponse])
def list_teams(status: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        teams = team_service.list_teams(db, status=status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_to_response(t) for t in teams]


@router.get("/match", response_model=List[TeamMatchResponse])
def match_teams(capabilities: str = Query(""), db: Session = Depends(get_db)):
    """Teams que cubren las capabilities requeridas (coma-separadas), ordenados por score."""
    caps = [c.strip() for c in capabilities.split(",") if c.strip()]
    if not caps:
        return []
    return team_service.match_teams(db, required_capabilities=caps)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: str, db: Session = Depends(get_db)):
    team = team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return _to_response(team)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(team_id: str, req: TeamUpdate, db: Session = Depends(get_db)):
    team = team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        team = team_service.update_team(db, team, patch=req.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(team)


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: str, db: Session = Depends(get_db)):
    team = team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team_service.delete_team(db, team)


@router.post("/{team_id}/members", response_model=TeamResponse)
def add_member(team_id: str, req: MemberAdd, db: Session = Depends(get_db)):
    team = team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        team = team_service.add_member(db, team, req.agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(team)


@router.delete("/{team_id}/members/{agent_id}", response_model=TeamResponse)
def remove_member(team_id: str, agent_id: str, db: Session = Depends(get_db)):
    team = team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        team = team_service.remove_member(db, team, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(team)


@router.get("/{team_id}/members", response_model=List[MemberResponse])
def list_members(team_id: str, db: Session = Depends(get_db)):
    team = team_service.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    agents = team_service.resolve_team_agents(db, team)
    out = []
    for a in agents:
        out.append(MemberResponse(
            id=a.id,
            name=a.name,
            emoji=a.emoji or "🤖",
            role=a.role.value if hasattr(a.role, "value") else str(a.role),
            status=a.status.value if hasattr(a.status, "value") else str(a.status),
            capabilities=a.capabilities or [],
            runtime=a.runtime.value if hasattr(a.runtime, "value") else str(a.runtime),
            provider=a.provider.value if hasattr(a.provider, "value") else str(a.provider),
            model=a.model,
            health_status=a.health_status,
            availability=a.availability,
        ))
    return out
