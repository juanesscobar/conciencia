"""Endpoints de HUNT (descubrimiento) + jobs async (cancel/retry)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user

from ..models import Lead, LeadHuntRun, LeadHunterJob, LeadHunterJobStatus
from ..schemas import (
    HuntSourceInfo,
    HuntSummary,
    HuntRunResponse,
    LeadHunterJobCreate,
    LeadHunterJobResponse,
    LeadHunterJobListResponse,
    LeadListResponse,
)
from ..helpers import _to_response
from ..discovery import run_discovery
from ..geo import build_geo_context, get_geo_provider, GeoScopeError
from ..sources import get_all_sources

router = APIRouter(tags=["leadhunter"], dependencies=[Depends(get_current_user)])


@router.get("/hunt/sources", response_model=list[HuntSourceInfo])
def hunt_sources():
    """Fuentes de prospección disponibles."""
    return [
        HuntSourceInfo(name=s.name, label=s.label, description=s.description, enabled=s.enabled)
        for s in get_all_sources().values()
    ]


@router.get("/geo/scope", response_model=dict)
def geo_scope(
    country: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
):
    """Scope geográfico efectivo: defaults de Settings + contexto resuelto (bbox/área).

    Permite a la UI mostrar el ámbito vigente (ej: PY · país) y validar antes de cazar.
    """
    try:
        ctx = build_geo_context(country=country, region=region, city=city)
    except GeoScopeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ctx["provider"] = get_geo_provider().name
    ctx["scope_dict"] = ctx["scope"].to_dict()
    return ctx


@router.post("/hunt/run", response_model=HuntSummary)
def hunt_run(
    source: Optional[str] = None,
    industry: Optional[str] = None,
    segment: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    allow_global: bool = Query(False, description="Permite scope global SOLO si se pide explícitamente (spec §9)"),
    limit: Optional[int] = Query(None, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Ejecuta el descubrimiento ahora (todas las fuentes o una sola).

    Acepta los mismos criterios que el filtro de la UI: industry, segment, region,
    más geografía first-class: country, city. El scope efectivo se resuelve desde
    Settings (SEARCH_DEFAULT_COUNTRY=PY por defecto); nunca se caza el mundo salvo
    allow_global=true explícito (spec §7-9).
    """
    filters = {}
    if industry:
        filters["industry"] = industry
    if segment:
        filters["segment"] = segment
    # El match de items se hace contra la localidad más específica (ciudad > región)
    if city:
        filters["region"] = city
    elif region:
        filters["region"] = region
    try:
        geo_ctx = build_geo_context(
            country=country,
            region=region,
            city=city,
            allow_global=allow_global,
        )
        return run_discovery(db, source=source, limit=limit, filters=filters or None, geo=geo_ctx)
    except GeoScopeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/hunt/runs", response_model=list[HuntRunResponse])
def hunt_runs(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """Historial de corridas de descubrimiento."""
    runs = db.query(LeadHuntRun).order_by(LeadHuntRun.started_at.desc()).limit(limit).all()
    return [HuntRunResponse(**r.to_dict()) for r in runs]


# ================== JOBS (prospección async con cancel/retry) ==================


@router.post("/jobs", response_model=LeadHunterJobResponse, status_code=201)
def create_job(req: LeadHunterJobCreate, db: Session = Depends(get_db)):
    """Crea un job de prospección con criterios y lo lanza async (PENDING → RUNNING).

    criteria: {source?: str, limit?: int, industry?: str, region?: str, segment?: str}
    """
    from ..jobs import create_job as _create_job

    job = _create_job(db, name=req.name, project_id=req.project_id, criteria=req.criteria)
    return LeadHunterJobResponse(**job.to_dict())


@router.get("/jobs", response_model=LeadHunterJobListResponse)
def list_jobs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Lista de jobs de prospección (más recientes primero)."""
    jobs = db.query(LeadHunterJob).order_by(LeadHunterJob.created_at.desc()).limit(limit).all()
    return LeadHunterJobListResponse(
        items=[LeadHunterJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=LeadHunterJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Estado de un job (incluye progress: searching/extracting/validating/scoring/done)."""
    job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return LeadHunterJobResponse(**job.to_dict())


@router.post("/jobs/{job_id}/cancel", response_model=LeadHunterJobResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Solicita la cancelación del job (se corta entre fuentes)."""
    from ..jobs import request_cancel

    job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (LeadHunterJobStatus.PENDING, LeadHunterJobStatus.RUNNING):
        raise HTTPException(status_code=409, detail=f"El job está {job.status.value}; solo se cancelan jobs pendientes/running")
    request_cancel(job_id)
    return LeadHunterJobResponse(**job.to_dict())


@router.post("/jobs/{job_id}/retry", response_model=LeadHunterJobResponse)
def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Reintenta un job fallido o cancelado (misma configuración)."""
    from ..jobs import start_job

    job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (LeadHunterJobStatus.RUNNING, LeadHunterJobStatus.PENDING):
        raise HTTPException(status_code=409, detail="El job ya está corriendo")
    job.status = LeadHunterJobStatus.PENDING
    job.error = None
    job.completed_at = None
    job.results_count = 0
    job.duplicates_count = 0
    db.commit()
    start_job(job.id)
    db.refresh(job)
    return LeadHunterJobResponse(**job.to_dict())


@router.get("/jobs/{job_id}/leads", response_model=LeadListResponse)
def job_leads(job_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    """Leads creados por un job."""
    query = db.query(Lead).filter(Lead.job_id == job_id).order_by(Lead.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return LeadListResponse(items=[_to_response(l, db=db) for l in items], total=total, page=page, page_size=page_size)
