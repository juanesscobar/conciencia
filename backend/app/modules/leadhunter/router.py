"""Lead Hunter API router: caza (hunt), pipeline, propuestas, import CSV y webhook."""

import csv
import io
import os
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user

from .models import Lead, LeadStatus, LeadHuntRun, LeadEvent, LeadProposal, LeadHunterJobStatus
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
    LeadEventResponse,
    LeadProposalCreate,
    LeadProposalResponse,
    ActionRequest,
    ImportResult,
    SendProposalRequest,
    LeadHunterJobCreate,
    LeadHunterJobResponse,
    LeadHunterJobListResponse,
    SavedLeadListCreate,
    SavedLeadListResponse,
    SavedLeadListDetailResponse,
    SavedLeadListAddRequest,
    LeadSavedSearchCreate,
    LeadSavedSearchResponse,
)
from .service import compute_score, enrich_with_ai
from .sources import get_all_sources
from .discovery import run_discovery, add_event
from .enrich import enrich_from_website
from .geo import build_geo_context, get_geo_provider, GeoScopeError
from .search import SearchEngine, SearchQuery, SearchResult
from .nlu import interpret as nlu_interpret, interpret_with_llm_fallback

router = APIRouter(prefix="/api/v1/leads", tags=["leadhunter"], dependencies=[Depends(get_current_user)])

# Router público SOLO para el webhook de intake (lo usa la landing de Conciencia sin token)
intake_router = APIRouter(prefix="/api/v1/leads", tags=["leadhunter-intake"])

ONLINE_FILTERS = {"website", "email", "phone", "social", "any"}
SORT_OPTIONS = {"newest", "score", "company", "oldest"}

STREET_LIKE = re.compile(r"^(av|avda|avenida|calle|ruta|camino|autopista|acceso|km|pasaje|tacuara|azara|cnl|gral|san|sta|procer|eugenio|teniente)", re.I)


def _norm(s: str) -> str:
    """Normaliza para comparaciones: minúsculas, sin acentos."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _to_response(lead: Lead) -> LeadResponse:
    return LeadResponse(**lead.to_dict())


def _get_lead_or_404(db: Session, lead_id: str) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _recompute_score(lead: Lead) -> None:
    lead.score = compute_score(
        company=lead.company or "",
        industry=lead.industry or "",
        source=lead.source or "manual",
        email=lead.email or "",
        phone=lead.phone or "",
        notes=lead.notes or "",
        metadata=lead.meta,
    )


@router.get("/", response_model=LeadListResponse)
def list_leads(
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    industry: Optional[str] = None,
    segment: Optional[str] = None,
    region: Optional[str] = None,
    online: Optional[str] = None,       # website | email | phone | any
    age_days: Optional[int] = Query(None, ge=0),   # creados en los últimos N días
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    list_id: Optional[str] = None,      # filtro por lista guardada
    sort: str = Query("newest", regex="^(newest|oldest|score|company)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lista de leads con filtros avanzados: región, tamaño, presencia online, antigüedad, score."""
    query = db.query(Lead)

    if list_id:
        from .models import LeadList

        lst = db.query(LeadList).filter(LeadList.id == list_id).first()
        if not lst:
            raise HTTPException(status_code=404, detail="Lista no encontrada")
        query = query.filter(Lead.id.in_([l.id for l in lst.leads]))

    if status:
        query = query.filter(Lead.status == LeadStatus(status))
    if source:
        query = query.filter(Lead.source == source)
    if industry:
        query = query.filter(Lead.industry.ilike(f"%{industry}%"))
    if segment:
        query = query.filter(Lead.segment == segment)
    if region:
        # Normaliza acentos/case para matchear 'Asuncion' con 'Asunción'
        norm_region = _norm(region)
        pairs = db.query(Lead.id, Lead.region).filter(Lead.region.isnot(None)).all()
        ids = [
            lid for lid, reg in pairs
            if any(norm_region in _norm(part) for part in reg.split(","))
        ]
        query = query.filter(Lead.id.in_(ids))
    if online:
        if online not in ONLINE_FILTERS:
            raise HTTPException(status_code=400, detail=f"online debe ser uno de: {', '.join(sorted(ONLINE_FILTERS))}")
        if online == "any":
            query = query.filter(or_(Lead.website.isnot(None), Lead.email.isnot(None), Lead.phone.isnot(None)))
        else:
            col = {"website": Lead.website, "email": Lead.email, "phone": Lead.phone}[online]
            query = query.filter(col.isnot(None))
    if age_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=age_days)
        query = query.filter(Lead.created_at >= cutoff)
    if min_score is not None:
        query = query.filter(Lead.score >= min_score)
    if max_score is not None:
        query = query.filter(Lead.score <= max_score)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Lead.company.ilike(like),
                Lead.contact_name.ilike(like),
                Lead.email.ilike(like),
                Lead.phone.ilike(like),
                Lead.notes.ilike(like),
                Lead.region.ilike(like),
            )
        )

    total = query.count()

    if sort == "score":
        query = query.order_by(Lead.score.desc(), Lead.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Lead.created_at.asc())
    elif sort == "company":
        query = query.order_by(Lead.company.asc())
    else:
        query = query.order_by(Lead.created_at.desc())

    leads = query.offset((page - 1) * page_size).limit(page_size).all()

    return LeadListResponse(
        items=[_to_response(l) for l in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


# ================== SEARCH CANÓNICO + NL (Fase 2, aditivo) ==================


class InterpretRequest(BaseModel):
    """Texto libre a interpretar como SearchQuery."""
    text: str
    default_country: Optional[str] = None


@router.post("/search/interpret", response_model=SearchQuery)
def interpret_search(body: InterpretRequest):
    """NL → SearchQuery: convierte 'playas de autos usados en Ciudad del Este'
    en filtros estructurados (categoría, región, país). Fallback LLM opcional."""
    return interpret_with_llm_fallback(
        body.text,
        default_country=body.default_country or "PY",
    )


@router.post("/search", response_model=SearchResult)
def search_leads(body: SearchQuery, db: Session = Depends(get_db)):
    """Ejecuta un SearchQuery canónico (misma lógica que UI/CLI/Agentes)."""
    return SearchEngine().execute(db, body)


@router.get("/regions", response_model=list[str])
def lead_regions(db: Session = Depends(get_db)):
    """Regiones (ciudades) con leads, para el filtro (limpio, sin calles)."""
    rows = db.query(Lead.region).filter(Lead.region.isnot(None)).distinct().all()
    seen: set = set()
    out = []
    for (r,) in rows:
        r = (r or "").strip()
        if not r or STREET_LIKE.match(r) or len(r) < 3:
            continue
        key = _norm(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return sorted(out, key=lambda s: s.lower())


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


# ================== HUNT (descubrimiento) ==================


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
    from .jobs import create_job as _create_job

    job = _create_job(db, name=req.name, project_id=req.project_id, criteria=req.criteria)
    return LeadHunterJobResponse(**job.to_dict())


@router.get("/jobs", response_model=LeadHunterJobListResponse)
def list_jobs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Lista de jobs de prospección (más recientes primero)."""
    from .models import LeadHunterJob

    jobs = db.query(LeadHunterJob).order_by(LeadHunterJob.created_at.desc()).limit(limit).all()
    return LeadHunterJobListResponse(
        items=[LeadHunterJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=LeadHunterJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Estado de un job (incluye progress: searching/extracting/validating/scoring/done)."""
    from .models import LeadHunterJob

    job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return LeadHunterJobResponse(**job.to_dict())


@router.post("/jobs/{job_id}/cancel", response_model=LeadHunterJobResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Solicita la cancelación del job (se corta entre fuentes)."""
    from .models import LeadHunterJob
    from .jobs import request_cancel

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
    from .models import LeadHunterJob
    from .jobs import start_job

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
    return LeadListResponse(items=[_to_response(l) for l in items], total=total, page=page, page_size=page_size)


# ================== SEARCHES GUARDADAS + LISTAS ==================


@router.get("/searches", response_model=list[LeadSavedSearchResponse])
def list_saved_searches(db: Session = Depends(get_db)):
    """Búsquedas guardadas (snapshots de filtros)."""
    from .models import LeadSavedSearch

    items = db.query(LeadSavedSearch).order_by(LeadSavedSearch.created_at.desc()).all()
    return [LeadSavedSearchResponse(**s.to_dict()) for s in items]


@router.post("/searches", response_model=LeadSavedSearchResponse, status_code=201)
def create_saved_search(req: LeadSavedSearchCreate, db: Session = Depends(get_db)):
    """Guarda la búsqueda actual (filtros de la tabla de leads)."""
    from .models import LeadSavedSearch

    search = LeadSavedSearch(name=req.name.strip(), filters=req.filters or {})
    db.add(search)
    db.commit()
    db.refresh(search)
    return LeadSavedSearchResponse(**search.to_dict())


@router.delete("/searches/{search_id}", status_code=204)
def delete_saved_search(search_id: str, db: Session = Depends(get_db)):
    """Elimina una búsqueda guardada."""
    from .models import LeadSavedSearch

    search = db.query(LeadSavedSearch).filter(LeadSavedSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Búsqueda guardada no encontrada")
    db.delete(search)
    db.commit()
    return None


@router.get("/lists", response_model=list[SavedLeadListResponse])
def list_lead_lists(db: Session = Depends(get_db)):
    """Listas de leads guardadas (ej: 'Seguimiento marzo', 'Distribuidoras Gran Asunción')."""
    from .models import LeadList

    items = db.query(LeadList).order_by(LeadList.created_at.desc()).all()
    return [SavedLeadListResponse(**l.to_dict()) for l in items]


@router.post("/lists", response_model=SavedLeadListResponse, status_code=201)
def create_lead_list(req: SavedLeadListCreate, db: Session = Depends(get_db)):
    """Crea una lista de leads."""
    from .models import LeadList

    lst = LeadList(name=req.name.strip(), description=req.description)
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return SavedLeadListResponse(**lst.to_dict())


@router.delete("/lists/{list_id}", status_code=204)
def delete_lead_list(list_id: str, db: Session = Depends(get_db)):
    """Elimina una lista (no borra los leads)."""
    from .models import LeadList

    lst = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    db.delete(lst)
    db.commit()
    return None


@router.post("/lists/{list_id}/leads", response_model=SavedLeadListResponse)
def add_lead_to_list(list_id: str, req: SavedLeadListAddRequest, db: Session = Depends(get_db)):
    """Agrega un lead a una lista (idempotente)."""
    from .models import LeadList

    lst = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    _get_lead_or_404(db, req.lead_id)
    if not any(l.id == req.lead_id for l in lst.leads):
        lst.leads.append(db.query(Lead).filter(Lead.id == req.lead_id).first())
        db.commit()
        db.refresh(lst)
    return SavedLeadListResponse(**lst.to_dict())


@router.delete("/lists/{list_id}/leads/{lead_id}", response_model=SavedLeadListResponse)
def remove_lead_from_list(list_id: str, lead_id: str, db: Session = Depends(get_db)):
    """Saca un lead de una lista."""
    from .models import LeadList

    lst = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    lst.leads = [l for l in lst.leads if l.id != lead_id]
    db.commit()
    db.refresh(lst)
    return SavedLeadListResponse(**lst.to_dict())


@router.get("/lists/{list_id}/leads", response_model=SavedLeadListDetailResponse)
def get_lead_list(list_id: str, db: Session = Depends(get_db)):
    """Detalle de una lista con sus leads."""
    from .models import LeadList

    lst = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    d = lst.to_dict()
    d["leads"] = [_to_response(l) for l in lst.leads]
    return SavedLeadListDetailResponse(**d)


@router.get("/{lead_id}/lists", response_model=list[SavedLeadListResponse])
def lead_lists(lead_id: str, db: Session = Depends(get_db)):
    """Listas a las que pertenece un lead."""
    from .models import LeadList

    _get_lead_or_404(db, lead_id)
    lists = db.query(LeadList).filter(LeadList.leads.any(Lead.id == lead_id)).all()
    return [SavedLeadListResponse(**l.to_dict()) for l in lists]


# ================== PIPELINE (acciones) ==================


@router.post("/{lead_id}/contact", response_model=LeadResponse)
def contact_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Marca el lead como contactado (primer acercamiento)."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.CONTACTED
    db.add(add_event(db, lead.id, "contacted", req.reason or "Primer contacto realizado"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.post("/{lead_id}/qualify", response_model=LeadResponse)
def qualify_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Califica el lead (validado como prospecto real)."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.QUALIFIED
    db.add(add_event(db, lead.id, "qualified", req.reason or "Lead calificado como prospecto"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.post("/{lead_id}/won", response_model=LeadResponse)
def won_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Cierra el lead como ganado."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.WON
    db.add(add_event(db, lead.id, "won", req.reason or "Cliente ganado"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.post("/{lead_id}/lost", response_model=LeadResponse)
def lost_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Cierra el lead como perdido (con motivo)."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.LOST
    db.add(add_event(db, lead.id, "lost", req.reason or "Lead perdido"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.post("/{lead_id}/note", response_model=LeadResponse)
def add_note(lead_id: str, req: ActionRequest, db: Session = Depends(get_db)):
    """Agrega una nota al lead (se guarda en el timeline)."""
    if not req.note or not req.note.strip():
        raise HTTPException(status_code=400, detail="note no puede estar vacía")
    lead = _get_lead_or_404(db, lead_id)
    db.add(add_event(db, lead.id, "note", req.note.strip()))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


# ================== TIMELINE ==================


@router.get("/{lead_id}/events", response_model=list[LeadEventResponse])
def lead_events(lead_id: str, db: Session = Depends(get_db)):
    """Timeline de acciones del lead."""
    _get_lead_or_404(db, lead_id)
    events = db.query(LeadEvent).filter(LeadEvent.lead_id == lead_id).order_by(LeadEvent.created_at.desc()).all()
    return [LeadEventResponse(**e.to_dict()) for e in events]


# ================== PROPUESTAS ==================


def _send_whatsapp(wa: dict) -> dict:
    """Envía por WhatsApp real si el bridge está conectado; si no, deep link wa.me."""
    try:
        from app.modules.whatsapp.bridge import get_status, send_message
        status = get_status()
        if status.get("state") == "connected":
            res = send_message(wa["to"], wa["text"])
            return {"sent": bool(res.get("ok")), "method": "whatsapp_api", **res}
    except Exception as e:  # noqa: BLE001
        return {"sent": False, "method": "whatsapp_api", "ok": False, "error": str(e)[:200]}
    return {
        "sent": False,
        "method": "whatsapp_link",
        "url": wa["url"],
        "reason": "WhatsApp no conectado — se generó el link wa.me",
    }


@router.get("/{lead_id}/proposals", response_model=list[LeadProposalResponse])
def lead_proposals(lead_id: str, db: Session = Depends(get_db)):
    """Propuestas del lead."""
    _get_lead_or_404(db, lead_id)
    props = db.query(LeadProposal).filter(LeadProposal.lead_id == lead_id).order_by(LeadProposal.created_at.desc()).all()
    return [LeadProposalResponse(**p.to_dict()) for p in props]


@router.post("/{lead_id}/proposal/generate", response_model=LeadProposalResponse)
def generate_proposal(lead_id: str, mode: str = Query("squad", regex="^(squad|quick)$"), db: Session = Depends(get_db)):
    """Genera una propuesta comercial con IA usando el sales squad (pm→rd→fin→comms).

    - mode=squad: 4 agentes encadenados (default).
    - mode=quick: solo el agente Comms (1 llamada).
    Si el LLM no está configurado devuelve 409 con instrucciones, sin guardar basura.
    """
    from .proposal import generate_sales_proposal

    lead = _get_lead_or_404(db, lead_id)
    result = generate_sales_proposal(lead, mode=mode)

    if not result.get("ok"):
        if result.get("reason") == "llm_not_configured":
            raise HTTPException(status_code=409, detail=result["detail"])
        raise HTTPException(status_code=502, detail=result.get("detail", "El squad no pudo generar la propuesta"))

    title = f"Propuesta — {lead.company}"
    proposal = LeadProposal(
        lead_id=lead.id,
        title=title,
        content=result["content"],
        status="draft",
        model=(f"{result.get('provider', '?')}:{result['model']}" if result.get("model") else None),
        meta={
            "squad": result.get("agents", []),
            "sections": {k: v[:400] for k, v in result.get("sections", {}).items()},
            "mode": mode,
        },
    )
    db.add(proposal)
    db.add(add_event(db, lead.id, "proposal_generated", "Propuesta generada con IA (sales squad)"))
    db.commit()
    db.refresh(proposal)
    return LeadProposalResponse(**proposal.to_dict())


@router.post("/{lead_id}/proposal", response_model=LeadProposalResponse)
def create_proposal_manual(lead_id: str, req: LeadProposalCreate, db: Session = Depends(get_db)):
    """Crea una propuesta manual (pegada por el usuario)."""
    lead = _get_lead_or_404(db, lead_id)
    proposal = LeadProposal(
        lead_id=lead.id,
        title=req.title or f"Propuesta — {lead.company}",
        content=req.content,
        status="draft",
    )
    db.add(proposal)
    db.add(add_event(db, lead.id, "proposal_generated", "Propuesta cargada manualmente"))
    db.commit()
    db.refresh(proposal)
    return LeadProposalResponse(**proposal.to_dict())


@router.post("/proposals/{proposal_id}/send", response_model=dict)
def send_proposal(proposal_id: str, req: SendProposalRequest = SendProposalRequest(), db: Session = Depends(get_db)):
    """Marca la propuesta como enviada y la entrega por el canal pedido:
    - channel=email → SMTP si está configurado, si no mailto
    - channel=whatsapp → deep link wa.me con el contenido
    - channel=link o vacío → solo marca enviada y devuelve los links"""
    from .delivery import build_delivery_links, send_email

    proposal = db.query(LeadProposal).filter(LeadProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    delivery = build_delivery_links(proposal, lead)
    channel = (req.channel or "link").strip().lower()
    result = {"proposal_id": proposal.id, "channel": channel, "delivery": delivery}

    if channel == "email":
        to = (req.to_email or lead.email or "").strip()
        if not to:
            raise HTTPException(status_code=400, detail="El lead no tiene email. Editalo o elegí otro canal.")
        # Adjunta el PDF de la propuesta si se puede generar
        pdf_bytes = None
        pdf_filename = None
        try:
            from .pdfgen import render_proposal_pdf

            pdf_bytes = render_proposal_pdf(
                company=lead.company,
                contact_name=lead.contact_name,
                email=lead.email,
                phone=lead.phone,
                title=proposal.title or f"Propuesta — {lead.company}",
                content=proposal.content,
                model=proposal.model,
                generated_at=proposal.created_at.isoformat() if proposal.created_at else None,
                proposal_status=proposal.status,
            )
            import re as _re
            import unicodedata as _u

            fname = _u.normalize("NFKD", lead.company or "propuesta")
            fname = "".join(c for c in fname if not _u.combining(c))
            fname = _re.sub(r"[^a-zA-Z0-9\-_\.]+", "-", fname.lower()).strip("-")
            pdf_filename = f"propuesta-{fname or 'comercial'}.pdf"
        except Exception:  # noqa: BLE001
            pdf_bytes = None
        email_res = send_email(to, delivery["subject"], delivery["body"], pdf_bytes=pdf_bytes, pdf_filename=pdf_filename)
        if pdf_bytes:
            email_res["pdf_attached"] = True
        result["send_result"] = email_res
    elif channel == "whatsapp":
        wa = delivery["channels"].get("whatsapp")
        if not wa:
            raise HTTPException(status_code=400, detail="El lead no tiene teléfono para WhatsApp.")
        result["send_result"] = _send_whatsapp(wa)

    # Seguimiento de entrega: marcar como enviada SOLO si hubo entrega real (SMTP/WhatsApp API)
    # o fallback manual (mailto / wa.me). Si el envío falla, queda en draft y se registra el error
    # para que se pueda verificar en el timeline si realmente salió o no.
    sr = result.get("send_result") or {}
    # channel=link (o vacío) = marcado manual: se marca enviada sin delivery externo
    manual_mark = channel in ("link", "") or "send_result" not in result
    delivered = manual_mark or bool(sr.get("sent")) or sr.get("method") in ("mailto", "whatsapp_link")
    if delivered:
        proposal.status = "sent"
        proposal.sent_at = datetime.utcnow()
        if lead.status != LeadStatus.PROPOSAL:
            lead.status = LeadStatus.PROPOSAL
        detail = f"Propuesta enviada por {channel}"
        if sr.get("to"):
            detail += f" a {sr['to']}"
        if sr.get("method"):
            detail += f" (método: {sr['method']})"
        db.add(add_event(db, lead.id, "proposal_sent", detail))
        result["status"] = "sent"
    else:
        err = sr.get("error") or sr.get("reason") or "Error de entrega desconocido"
        db.add(add_event(db, lead.id, "proposal_send_failed", f"Fallo envío por {channel}: {err}"))
        result["status"] = "failed"
    result["lead_status"] = lead.status.value
    db.commit()
    return result


@router.get("/proposals/{proposal_id}/deliver", response_model=dict)
def proposal_delivery_links(proposal_id: str, db: Session = Depends(get_db)):
    """Devuelve los canales disponibles (email/whatsapp) con sus links, sin marcar nada."""
    from .delivery import build_delivery_links

    proposal = db.query(LeadProposal).filter(LeadProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"proposal_id": proposal.id, "lead_company": lead.company, **build_delivery_links(proposal, lead)}


@router.get("/proposals/{proposal_id}/pdf")
def proposal_pdf(proposal_id: str, db: Session = Depends(get_db)):
    """Genera y devuelve la propuesta como PDF descargable (fpdf2, sin dependencias nativas)."""
    from .pdfgen import render_proposal_pdf
    from fastapi.responses import Response
    from urllib.parse import quote

    proposal = db.query(LeadProposal).filter(LeadProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        pdf_bytes = render_proposal_pdf(
            company=lead.company,
            contact_name=lead.contact_name,
            email=lead.email,
            phone=lead.phone,
            title=proposal.title or f"Propuesta — {lead.company}",
            content=proposal.content,
            model=proposal.model,
            generated_at=proposal.created_at.isoformat() if proposal.created_at else None,
            proposal_status=proposal.status,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)[:200]}")

    filename = f"propuesta-{_slug(lead.company)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename*=UTF-8\'\'{quote(filename)}'},
    )


def _slug(text: str) -> str:
    import unicodedata as _u
    t = _u.normalize("NFKD", text or "propuesta")
    t = "".join(c for c in t if not _u.combining(c))
    t = re.sub(r"[^a-zA-Z0-9\-_\.]+", "-", t.lower()).strip("-")
    return t or "propuesta"


# ================== IMPORT CSV ==================


@router.post("/import", response_model=ImportResult)
async def import_leads_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Importa leads desde un CSV (company requerida; contact_name, email, phone, website,
    industry, segment, region, notes, source opcionales). Dedupe automático."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vacío o sin encabezados")

    from .discovery import _is_duplicate

    added = duplicates = errors = 0
    total = 0
    for row in reader:
        total += 1
        try:
            company = (row.get("company") or row.get("empresa") or "").strip()
            if not company:
                errors += 1
                continue
            if _is_duplicate(db, company, row.get("website"), row.get("phone")):
                duplicates += 1
                continue

            lead = Lead(
                company=company,
                contact_name=(row.get("contact_name") or row.get("contacto") or "").strip() or None,
                email=(row.get("email") or "").strip() or None,
                phone=(row.get("phone") or row.get("telefono") or "").strip() or None,
                website=(row.get("website") or row.get("web") or "").strip() or None,
                source=(row.get("source") or row.get("fuente") or "import").strip() or "import",
                industry=(row.get("industry") or row.get("sector") or "").strip() or None,
                segment=(row.get("segment") or "").strip() or None,
                region=(row.get("region") or row.get("ciudad") or "").strip() or None,
                status=LeadStatus.NEW,
                notes=(row.get("notes") or row.get("notas") or "").strip() or None,
                meta={"source_detail": "csv_import"},
            )
            _recompute_score(lead)
            db.add(lead)
            db.flush()
            db.add(add_event(db, lead.id, "created", "Lead importado por CSV"))
            added += 1
        except Exception:  # noqa: BLE001
            errors += 1

    db.commit()
    return ImportResult(total=total, added=added, duplicates=duplicates, errors=errors)


# ================== CRUD básico ==================


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
        region=req.region,
        status=req.status,
        notes=req.notes,
        meta=req.metadata,
    )
    _recompute_score(lead)
    db.add(lead)
    db.flush()
    db.add(add_event(db, lead.id, "created", "Lead creado manualmente"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@intake_router.post("/intake", response_model=LeadResponse, status_code=201)
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
        region=req.region,
        status=LeadStatus.NEW,
        notes=req.notes,
        meta=req.metadata,
    )
    if req.metadata and req.metadata.get("source"):
        lead.source = req.metadata["source"]
    _recompute_score(lead)
    db.add(lead)
    db.flush()
    db.add(add_event(db, lead.id, "created", "Lead capturado por webhook (landing/formulario)"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)
    return _to_response(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, req: LeadUpdate, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)

    data = req.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(lead, field, value)

    _recompute_score(lead)
    db.commit()
    db.refresh(lead)
    return _to_response(lead)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)
    db.delete(lead)
    db.commit()
    return None


@router.post("/{lead_id}/enrich-website", response_model=EnrichResult)
def enrich_lead_website(lead_id: str, db: Session = Depends(get_db)):
    """Raspa el website del lead para completar email/teléfono."""
    lead = _get_lead_or_404(db, lead_id)
    result = enrich_from_website(lead)
    if result.get("changed"):
        _recompute_score(lead)
        db.add(add_event(db, lead.id, "enriched", f"Enriquecido desde website: email={result.get('email')} tel={result.get('phone')}"))
        db.commit()
        db.refresh(lead)
    return EnrichResult(**result)


@router.post("/{lead_id}/enrich", response_model=dict)
def enrich_lead_ai(lead_id: str, db: Session = Depends(get_db)):
    """Enriquece el lead con IA (DeepSeek si está configurado).

    Guarda el análisis en meta.analysis y lo deja visible en el timeline.
    Si el LLM no está configurado devuelve 409 para que la UI avise.
    """
    from .service import enrich_with_ai

    lead = _get_lead_or_404(db, lead_id)
    analysis = enrich_with_ai(lead)
    if not analysis:
        raise HTTPException(status_code=409, detail="IA no configurada — cargá la API key en Settings → Integraciones para enriquecer con IA")

    meta = dict(lead.meta or {})
    meta["analysis"] = analysis[:2000]
    lead.meta = meta
    _recompute_score(lead)
    db.add(add_event(db, lead.id, "enriched", "Enriquecido con IA (análisis guardado en el lead)"))
    db.commit()
    db.refresh(lead)
    return {"analysis": analysis, "score": lead.score, "lead": _to_response(lead)}
