from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Metric
from app.schemas import Metric as MetricSchema, MetricCreate
from uuid import UUID

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/", response_model=List[MetricSchema])
def get_metrics(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    metrics = (
        db.query(Metric)
        .order_by(Metric.recorded_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return metrics


@router.post("/", response_model=MetricSchema, status_code=201)
def create_metric(metric: MetricCreate, db: Session = Depends(get_db)):
    db_metric = Metric(**metric.model_dump())
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric


@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total_projects = db.query(func.count(Metric.project_id.distinct())).scalar() or 0
    recent = (
        db.query(Metric)
        .order_by(Metric.recorded_at.desc())
        .limit(20)
        .all()
    )
    return {"total_projects_with_metrics": total_projects, "recent": recent}


@router.get("/industry")
def get_industry_benchmarks(db: Session = Depends(get_db)):
    metrics = (
        db.query(Metric)
        .filter(Metric.category == "industry")
        .order_by(Metric.recorded_at.desc())
        .all()
    )
    return metrics
