"""Lead Hunter API router: CRUD, búsqueda (hunt), scoring, enriquecimiento y webhook de intake."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db

from .models import Lead, LeadStatus, LeadHuntRun
from .schemas import (
    LeadCreate,
    LeadUpdate,
    LeadIntake,
    LeadResponse,
    LeadListResponse,
    LeadStats,
    HuntSourceInfo,
    HuntSummary,
    HuntRunResponse,
    EnrichResult,
)
from .service import compute_score, enrich_with_ai
from .sources import get_all_sources
from .discovery import run_discovery
from .enrich import enrich_from_website

router = APIRouter(prefix="/api/v1/leads", tags=["leadhunter"])


def _to_response(lead: Lead) -> LeadResponse:
    return LeadResponse(**lead.to_dict())


@router.get("/", response_model=LeadListResponse)
def list_leads(
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    industry: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista de leads con filtros y paginación."""
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == LeadStatus(status))
    if source:
        query = query.filter(Lead.source == source)
    if industry:
        query = query.filter(Lead.industry.ilike(f"%{industry}%"))
    if min_score is not None:
        query = query.filter(Lead.score >= min_score)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Lead.company.ilike(like),
                Lead.contact_name.ilike(like),
                Lead.email.ilike(like),
                Lead.phone.ilike(like),
                Lead.notes.ilike(like),
            )
        )

    total = query.count()
    leads = query.order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return LeadListResponse(
        items=[_to_response(l) for l in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=LeadStats)
def lead_stats(db: Session = Depends(get_db)):
    """Estadísticas del pipeline de leads."""
    leads = db.query(Lead).all()
    by_status: dict = {}
    by_source: dict = {}
    total_score = 0
    for l in leads:
        by_status[l.status.value if hasattr(l.status, "value") else str(l.status)] = by_status.get(
            l.status.value if hasattr(l.status, "value") else str(l.status), 0
        ) + 1
        by_source[l.source] = by_source.get(l.source, 0) + 1
        total_score += l.score or 0

    top_sources = sorted(
        [{"source": k, "count": v} for k, v in by_source.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    return LeadStats(
        total=len(leads),
        by_status=by_status,
        by_source=by_source,
        avg_score=round(total_score / len(leads), 1) if leads else 0.0,
        top_sources=top_sources,
    )


# ================== HUNT (descubrimiento de leads) ==================


@router.get("/hunt/sources", response_model=list[HuntSourceInfo])
def hunt_sources():
    """Fuentes de prospección disponibles."""
    return [
        HuntSourceInfo(name=s.name, label=s.label, description=s.description, enabled=s.enabled)
        for s in get_all_sources().values()
    ]


@router.post("/hunt/run", response_model=HuntSummary)
def hunt_run(source: Optional[str] = None, db: Session = Depends(get_db)):
    """Ejecuta el descubrimiento ahora (todas las fuentes o una sola)."""
    try:
        return run_discovery(db, source=source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/hunt/runs", response_model=list[HuntRunResponse])
def hunt_runs(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """Historial de corridas de descubrimiento."""
    runs = db.query(LeadHuntRun).order_by(LeadHuntRun.started_at.desc()).limit(limit).all()
    return [HuntRunResponse(**r.to_dict()) for r in runs]


@router.post("/{lead_id}/enrich-website", response_model=EnrichResult)
def enrich_lead_website(lead_id: str, db: Session = Depends(get_db)):
    """Raspa el website del lead para completar email/teléfono."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    result = enrich_from_website(lead)
    if result.get("changed"):
        db.commit()
        db.refresh(lead)
    return EnrichResult(**result)


@router.post("/", response_model=LeadResponse, status_code=201)
def create_lead(req: LeadCreate, db: Session = Depends(get_db)):
    """Crea un lead manual y calcula su score."""
    lead = Lead(
        company=req.company.strip(),
        contact_name=req.contact_name,
        email=req.email,
        phone=req.phone,
        website=req.website,
        source=req.source or "manual",
        industry=req.industry,
        segment=req.segment,
        status=req.status,
        notes=req.notes,
        meta=req.metadata,
    )
    lead.score = compute_score(
        company=lead.company,
        industry=lead.industry or "",
        source=lead.source,
        email=lead.email or "",
        phone=lead.phone or "",
        notes=lead.notes or "",
        metadata=lead.meta,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.post("/intake", response_model=LeadResponse, status_code=201)
def intake_lead(req: LeadIntake, db: Session = Depends(get_db)):
    """Webhook público: captura leads desde landings/formularios (ej: conciencia-software)."""
    lead = Lead(
        company=req.company.strip(),
        contact_name=req.contact_name,
        email=req.email,
        phone=req.phone,
        website=req.website,
        source="conciencia" if not req.metadata or req.metadata.get("source") is None else req.metadata["source"],
        industry=req.industry,
        segment=req.segment,
        status=LeadStatus.NEW,
        notes=req.notes,
        meta=req.metadata,
    )
    if req.metadata and req.metadata.get("source"):
        lead.source = req.metadata["source"]
    lead.score = compute_score(
        company=lead.company,
        industry=lead.industry or "",
        source=lead.source,
        email=lead.email or "",
        phone=lead.phone or "",
        notes=lead.notes or "",
        metadata=lead.meta,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _to_response(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, req: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    data = req.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(lead, field, value)

    if req.status is not None or req.score is None:
        lead.score = compute_score(
            company=lead.company or "",
            industry=lead.industry or "",
            source=lead.source or "manual",
            email=lead.email or "",
            phone=lead.phone or "",
            notes=lead.notes or "",
            metadata=lead.meta,
        )
    db.commit()
    db.refresh(lead)
    return _to_response(lead)
