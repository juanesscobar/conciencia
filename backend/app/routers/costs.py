"""Costs - observabilidad de costos del Control Plane (fuente: cost_records)."""

from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func

from app.database import SessionLocal
from app.models.cost_record import CostRecord

router = APIRouter(prefix="/api/v1/costs", tags=["costs"])


def _db() -> SessionLocal:
    return SessionLocal()


@router.get("/summary")
def summary():
    db = _db()
    try:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week = today - timedelta(days=7)
        total = db.query(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)).scalar() or 0.0
        today_cost = db.query(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)) \
            .filter(CostRecord.timestamp >= today).scalar() or 0.0
        week_cost = db.query(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)) \
            .filter(CostRecord.timestamp >= week).scalar() or 0.0
        tokens = db.query(func.coalesce(func.sum(CostRecord.total_tokens), 0)).scalar() or 0
        records = db.query(func.count(CostRecord.id)).scalar() or 0

        by_provider = db.query(
            CostRecord.provider,
            func.sum(CostRecord.cost_usd),
            func.count(CostRecord.id),
        ).group_by(CostRecord.provider).order_by(func.sum(CostRecord.cost_usd).desc()).all()

        by_model = db.query(
            CostRecord.model,
            func.sum(CostRecord.cost_usd),
            func.count(CostRecord.id),
        ).group_by(CostRecord.model).order_by(func.sum(CostRecord.cost_usd).desc()).limit(10).all()

        return {
            "total_usd": round(total, 6),
            "today_usd": round(today_cost, 6),
            "week_usd": round(week_cost, 6),
            "total_tokens": tokens,
            "records": records,
            "by_provider": [
                {"provider": p, "cost_usd": round(c, 6), "calls": n}
                for p, c, n in by_provider
            ],
            "by_model": [
                {"model": m, "cost_usd": round(c, 6), "calls": n}
                for m, c, n in by_model
            ],
        }
    finally:
        db.close()


@router.get("/records")
def records(limit: int = 50):
    db = _db()
    try:
        rows = db.query(CostRecord) \
            .order_by(CostRecord.timestamp.desc()) \
            .limit(min(limit, 200)).all()
        return [r.to_dict() for r in rows]
    finally:
        db.close()
