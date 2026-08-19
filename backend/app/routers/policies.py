"""Policies - Governance: reglas allow/approval/deny por agente y acción."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.policy import Policy
from app.models.agent import Agent

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    agent_id: Optional[str] = None
    action: str
    effect: str  # allow | approval | deny
    note: Optional[str] = None


def _db() -> SessionLocal:
    return SessionLocal()


def _with_agent_names(policies: list) -> list:
    db = _db()
    try:
        agents = {str(a.id): a.name for a in db.query(Agent).all()}
    finally:
        db.close()
    out = []
    for p in policies:
        d = p.to_dict()
        if d["agent_id"] and d["agent_id"] in agents:
            d["agent_name"] = agents[d["agent_id"]]
        elif d["agent_id"] is None:
            d["agent_name"] = "global"
        out.append(d)
    return out


@router.get("/")
def list_policies():
    db = _db()
    try:
        rows = db.query(Policy).order_by(Policy.created_at).all()
        return _with_agent_names(rows)
    finally:
        db.close()


@router.post("/", status_code=201)
def create_policy(req: PolicyCreate):
    if req.effect not in ("allow", "approval", "deny"):
        raise HTTPException(status_code=400, detail="effect debe ser allow | approval | deny")
    db = _db()
    try:
        pol = Policy(
            agent_id=req.agent_id,
            action=req.action.strip().lower(),
            effect=req.effect,
            note=req.note,
        )
        db.add(pol)
        db.commit()
        db.refresh(pol)
        return _with_agent_names([pol])[0]
    finally:
        db.close()


@router.delete("/{policy_id}")
def delete_policy(policy_id: str):
    db = _db()
    try:
        pol = db.query(Policy).filter(Policy.id == policy_id).first()
        if not pol:
            raise HTTPException(status_code=404, detail="Policy no encontrada")
        db.delete(pol)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/agents")
def agents_overview():
    """Jerarquía de governance: agentes con autonomía + counts de policies."""
    db = _db()
    try:
        from sqlalchemy import func

        counts = dict(db.query(Policy.agent_id, func.count(Policy.id)).group_by(Policy.agent_id).all())
        rows = db.query(Agent).order_by(Agent.name).all()
        return [
            {
                "id": str(a.id),
                "name": a.name,
                "role": str(a.role.value) if hasattr(a.role, "value") else str(a.role),
                "autonomy_level": str(a.autonomy_level.value) if hasattr(a.autonomy_level, "value") else str(a.autonomy_level),
                "status": str(a.status.value) if hasattr(a.status, "value") else str(a.status),
                "runtime": str(a.runtime.value) if hasattr(a.runtime, "value") else str(a.runtime),
                "provider": str(a.provider.value) if hasattr(a.provider, "value") else str(a.provider),
                "policies": counts.get(str(a.id), 0),
            }
            for a in rows
        ]
    finally:
        db.close()
