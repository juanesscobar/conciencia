"""Endpoints de búsqueda/ranking/semántica (Fases 2/4/5) — capa fina HTTP."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user

from ..models import Lead, LeadStatus
from ..schemas import (
    LeadResponse,
    LeadListResponse,
    LeadStats,
    RankingWeights,
    SemanticSearchRequest,
    SemanticSearchResult,
    SemanticStatus,
)
from ..helpers import ONLINE_FILTERS, _norm, _to_response
from ..search import SearchEngine, SearchQuery, SearchResult
from ..nlu import interpret_with_llm_fallback
from ..ranking import get_ranking_weights, set_ranking_weights, enrich_lead_dict
from ..embeddings import (
    embeddings_enabled, embedding_model, embedding_backend_name, embedding_provider,
    get_backend, reindex_if_needed, semantic_search, _api_key,
)

router = APIRouter(tags=["leadhunter"], dependencies=[Depends(get_current_user)])


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
        from ..models import LeadList

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
        items=[_to_response(l, db=db) for l in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


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


@router.get("/ranking/weights", response_model=RankingWeights)
def get_weights(db: Session = Depends(get_db)):
    """Pesos actuales de ranking/scoring (merged con defaults)."""
    return RankingWeights(**get_ranking_weights(db))


@router.put("/ranking/weights", response_model=RankingWeights)
def update_weights(body: RankingWeights, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """Actualiza RANKING_WEIGHTS (persistido en Settings, JSON). Solo admin/owner/ceo."""
    if current_user.role not in ("admin", "owner", "ceo"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    merged = set_ranking_weights(db, body.model_dump(exclude_none=True))
    return RankingWeights(**merged)


def _semantic_simulated() -> bool:
    """True si estamos en modo simulado (sin API key real de embeddings)."""
    return not bool(_api_key(embedding_provider())) or embedding_provider() == "ollama"


@router.get("/search/semantic/status", response_model=SemanticStatus)
def semantic_status(db: Session = Depends(get_db)):
    """Estado del backend semántico: enabled, backend activo, modelo, indexados."""
    if not embeddings_enabled():
        return SemanticStatus(enabled=False, backend=embedding_backend_name(),
                              model=embedding_model(), simulated=True, indexed=0)
    return SemanticStatus(
        enabled=True,
        backend=get_backend().name,
        model=embedding_model(),
        simulated=_semantic_simulated(),
        indexed=get_backend().count(),
    )


@router.post("/search/semantic", response_model=SemanticSearchResult)
def search_semantic(body: SemanticSearchRequest, db: Session = Depends(get_db)):
    """Búsqueda semántica: embed query → vector search → leads rankeados por similitud.

    Requiere EMBEDDING_ENABLED=1; sin API key de embeddings corre en modo simulado
    (determinístico, útil para demo/tests). Devuelve 501 si está deshabilitado.
    """
    if not embeddings_enabled():
        raise HTTPException(
            status_code=501,
            detail="embedding model not configured: set EMBEDDING_ENABLED=1 (Settings → Lead Hunter → Semantic Search)",
        )

    reindex_if_needed(db)
    hits = semantic_search(db, body.query, top_k=body.top_k)
    weights = get_ranking_weights(db)

    items = []
    for lead, sim in hits:
        d = enrich_lead_dict(lead, db=db, sq=None)
        d["search_relevance"] = round(sim * 100, 1)
        reasons = list(d.get("reasons") or [])
        reasons.insert(0, f"Match semántico: {round(sim * 100)}% de similitud")
        d["reasons"] = reasons
        items.append(LeadResponse(**d))

    return SemanticSearchResult(
        items=items,
        total=len(items),
        query=body.query,
        backend=get_backend().name,
        model=embedding_model(),
        simulated=_semantic_simulated(),
    )


@router.get("/regions", response_model=list[str])
def lead_regions(db: Session = Depends(get_db)):
    """Regiones (ciudades) con leads, para el filtro (limpio, sin calles)."""
    from ..helpers import STREET_LIKE
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
