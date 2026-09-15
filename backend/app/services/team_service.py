"""TeamService — CRUD de teams + resolución de agentes dentro de un team.

Fase F (master prompt): una Mission puede coordinar un TEAM de agentes
especializados. El matching de capabilities se resuelve DENTRO del team
primero (fallback al registry global si el team no cubre la capability).

Principio: misma lógica de dominio para API, CLI y workflow engine.
"""

import logging
import uuid
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.team import Team, TEAM_STATUSES

log = logging.getLogger("teams")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_team(
    db: Session,
    *,
    name: str,
    description: Optional[str] = None,
    purpose: Optional[str] = None,
    emoji: str = "👥",
    member_ids: Optional[List[str]] = None,
    default_runtime: str = "generic",
    config: Optional[dict] = None,
) -> Team:
    if not name.strip():
        raise ValueError("Team name requerido")
    team = Team(
        name=name.strip(),
        description=description,
        purpose=purpose,
        emoji=emoji or "👥",
        status="active",
        member_ids=_validate_members(db, member_ids or []),
        default_runtime=default_runtime or "generic",
        config=config or {},
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    log.info("team creado: %s (%s)", team.name, team.id)
    return team


def list_teams(db: Session, status: Optional[str] = None, limit: int = 50) -> List[Team]:
    q = db.query(Team).order_by(Team.created_at.desc())
    if status:
        if status not in TEAM_STATUSES:
            raise ValueError(f"Status inválido: {status}. Válidos: {', '.join(TEAM_STATUSES)}")
        q = q.filter(Team.status == status)
    return q.limit(limit).all()


def get_team(db: Session, team_id: str) -> Optional[Team]:
    return db.query(Team).filter(Team.id == uuid.UUID(str(team_id))).first()


def update_team(db: Session, team: Team, *, patch: dict) -> Team:
    allowed = {"name", "description", "purpose", "emoji", "status", "default_runtime", "config"}
    for k, v in patch.items():
        if k not in allowed:
            continue
        if k == "name" and (not v or not str(v).strip()):
            raise ValueError("Team name requerido")
        if k == "status" and v not in TEAM_STATUSES:
            raise ValueError(f"Status inválido: {v}")
        setattr(team, k, v)
    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team: Team) -> None:
    db.delete(team)
    db.commit()


# ---------------------------------------------------------------------------
# Miembros
# ---------------------------------------------------------------------------

def add_member(db: Session, team: Team, agent_id: str) -> Team:
    member_ids = [str(m) for m in (team.member_ids or [])]
    if str(agent_id) in member_ids:
        return team  # idempotente
    _validate_members(db, [str(agent_id)])  # valida que exista
    member_ids.append(str(agent_id))
    team.member_ids = member_ids
    db.commit()
    db.refresh(team)
    return team


def remove_member(db: Session, team: Team, agent_id: str) -> Team:
    member_ids = [str(m) for m in (team.member_ids or [])]
    if str(agent_id) not in member_ids:
        raise ValueError(f"El agente {agent_id} no es miembro del team")
    member_ids.remove(str(agent_id))
    team.member_ids = member_ids
    db.commit()
    db.refresh(team)
    return team


def resolve_team_agents(db: Session, team: Team) -> List[Agent]:
    """Agentes del team (preservando el orden de member_ids)."""
    if not team.member_ids:
        return []
    ids = [uuid.UUID(str(m)) for m in team.member_ids]
    agents = db.query(Agent).filter(Agent.id.in_(ids)).all()
    by_id = {str(a.id): a for a in agents}
    return [by_id[str(i)] for i in ids if str(i) in by_id]


def team_capabilities(db: Session, team: Team) -> Dict[str, List[str]]:
    """Capabilities por agente + unión total del team."""
    union: List[str] = []
    per_agent: Dict[str, List[str]] = {}
    for a in resolve_team_agents(db, team):
        caps = [str(c) for c in (a.capabilities or [])]
        per_agent[str(a.id)] = caps
        for c in caps:
            if c not in union:
                union.append(c)
    return {"union": union, "per_agent": per_agent}


# ---------------------------------------------------------------------------
# Matching (misma normalización que capability_matching)
# ---------------------------------------------------------------------------

def _norm(cap: str) -> str:
    from app.services.capability_matching import normalize_cap
    return normalize_cap(cap)


def match_teams(
    db: Session,
    *,
    required_capabilities: List[str],
    min_score: int = 0,
) -> List[dict]:
    """Teams ordenados por % de capabilities cubiertas (score = cobertura 70% + tamaño 20% + base 10%)."""
    required = [_norm(c) for c in required_capabilities if c]
    if not required:
        return []

    results = []
    for team in db.query(Team).filter(Team.status == "active").all():
        union = {_norm(c) for c in team_capabilities(db, team)["union"]}
        if not union:
            continue
        matched = [c for c in required if c in union]
        missing = [c for c in required if c not in union]
        coverage = round(len(matched) / len(required) * 100) if required else 0
        if coverage == 0:
            continue
        size = len(team.member_ids or [])
        score = round(coverage * 0.7 + min(size, 5) * 4 + 10)  # hasta 5 miembros = 20 pts
        if coverage < min_score:
            continue
        results.append({
            "team_id": str(team.id),
            "name": team.name,
            "purpose": team.purpose,
            "emoji": team.emoji or "👥",
            "default_runtime": team.default_runtime,
            "members_count": size,
            "coverage": coverage,
            "matched_caps": matched,
            "missing_caps": missing,
            "score": score,
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def best_team(db: Session, *, required_capabilities: List[str]) -> Optional[dict]:
    """Mejor team que cubra >= 50% de las capabilities requeridas."""
    matches = match_teams(db, required_capabilities=required_capabilities, min_score=50)
    return matches[0] if matches else None


def best_agent_in_team(
    db: Session,
    *,
    team_id: str,
    required_capabilities: List[str],
    runtime: Optional[str] = None,
) -> Optional[dict]:
    """Mejor agente DENTRO del team para las capabilities requeridas.

    Reusa match_agents (score/disponibilidad) filtrando por los miembros.
    Devuelve None si el team no cubre >= 50% de las capabilities.
    """
    from app.services.capability_matching import match_agents, normalize_cap

    team = get_team(db, team_id)
    if not team:
        return None
    members = resolve_team_agents(db, team)
    if not members:
        return None
    member_ids = {str(m.id) for m in members}

    required = [normalize_cap(c) for c in required_capabilities if c]
    if not required:
        return None

    candidates = match_agents(
        db,
        required_capabilities=required_capabilities,
        runtime=runtime,
        min_score=50,
    )
    # el score de match_agents ya integra disponibilidad; filtramos por membresía
    for c in candidates:
        if c["agent_id"] in member_ids:
            return c
    return None


# ---------------------------------------------------------------------------
# helpers internos
# ---------------------------------------------------------------------------

def _validate_members(db: Session, member_ids: List[str]) -> List[str]:
    """Valida que los agentes existan; devuelve lista de strings únicos."""
    clean: List[str] = []
    seen = set()
    for mid in member_ids:
        mid = str(mid).strip()
        if not mid or mid in seen:
            continue
        agent = db.query(Agent).filter(Agent.id == uuid.UUID(mid)).first()
        if not agent:
            raise ValueError(f"Agente no encontrado: {mid}")
        clean.append(mid)
        seen.add(mid)
    return clean
