"""Decision Memory API (spec §26): CRUD + auto-numeración DEC-NNN."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.decision import Decision
from app.models.context_pack import ContextPack

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


class DecisionCreate(BaseModel):
    title: str
    decision: str
    reason: Optional[str] = None
    rejected: Optional[list] = None
    impact: Optional[list] = None
    links: Optional[dict] = None
    status: Optional[str] = None


def _db() -> SessionLocal:
    return SessionLocal()


def _next_number(db) -> int:
    last = db.query(Decision).order_by(Decision.number.desc()).first()
    return (last.number + 1) if last else 1


@router.get("/")
def list_decisions():
    db = _db()
    try:
        rows = db.query(Decision).order_by(Decision.number.desc()).all()
        return [d.to_dict() for d in rows]
    finally:
        db.close()


@router.get("/{decision_id}")
def get_decision(decision_id: str):
    db = _db()
    try:
        d = db.query(Decision).filter(Decision.id == decision_id).first()
        if not d:
            raise HTTPException(status_code=404, detail="Decisión no encontrada")
        return d.to_dict()
    finally:
        db.close()


@router.post("/", status_code=201)
def create_decision(req: DecisionCreate):
    db = _db()
    try:
        d = Decision(
            number=_next_number(db),
            title=req.title.strip(),
            decision=req.decision.strip(),
            reason=req.reason,
            rejected=req.rejected or [],
            impact=req.impact or [],
            links=req.links or {},
            status=req.status or "accepted",
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        return d.to_dict()
    finally:
        db.close()


@router.delete("/{decision_id}")
def delete_decision(decision_id: str):
    db = _db()
    try:
        d = db.query(Decision).filter(Decision.id == decision_id).first()
        if not d:
            raise HTTPException(status_code=404, detail="Decisión no encontrada")
        db.delete(d)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/pack/{pack_id}")
def decisions_for_pack(pack_id: str):
    """Decisiones referenciadas por un Context Pack."""
    db = _db()
    try:
        pack = db.query(ContextPack).filter(ContextPack.id == pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="Context Pack no encontrado")
        refs = (pack.content or {}).get("decisions") or []
        numbers = []
        for r in refs:
            if isinstance(r, str):
                numbers.append(int(r.split("-")[-1]) if r.startswith("DEC-") else 0)
        rows = db.query(Decision).filter(Decision.number.in_(numbers)).all() if numbers else []
        return [d.to_dict() for d in rows]
    finally:
        db.close()
