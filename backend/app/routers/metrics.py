from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Metric
from app.schemas import Metric as MetricSchema, MetricCreate
from uuid import UUID

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("/", response_model=List[MetricSchema])
def get_metrics(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    metrics = db.query(Metric).order_by(Metric.recorded_at.desc()).offset(skip).limit(limit).all()
    return metrics
