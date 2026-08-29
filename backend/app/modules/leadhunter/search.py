"""SearchQuery canónico + SearchEngine (spec §5/§6/§32).

Una búsqueda canónica reutilizable por UI/API/CLI/Agentes: el usuario escribe
lenguaje natural (o filtros estructurados) y el SearchEngine unifica el
filtrado SQL que antes vivía en `list_leads` del router.

Contrato: los endpoints existentes (GET /api/v1/leads/) NO cambian; todo lo
nuevo es aditivo (POST /search y POST /search/interpret).
"""

import base64
import re
import unicodedata
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .models import Lead, LeadStatus
from .schemas import LeadResponse
from .ranking import enrich_lead_dict

ONLINE_FILTERS = {"website", "email", "phone", "any"}
SORT_OPTIONS = {"newest", "oldest", "score", "company"}


def norm(s: str) -> str:
    """Normaliza para comparaciones: minúsculas, sin acentos, espacios colapsados."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


class SearchQuery(BaseModel):
    """Búsqueda canónica de leads — misma semántica para UI, API, CLI y agentes."""

    query: Optional[str] = None            # texto libre (full-text sobre campos clave)
    entity_type: Optional[str] = None      # tipo de entidad (negocio, contacto...)
    country: Optional[str] = None          # PY por defecto (scope geográfico)
    region: Optional[str] = None           # departamento / ciudad / zona
    city: Optional[str] = None             # ciudad específica (más preciso que region)
    category: Optional[str] = None         # categoría canónica (farmacia, distribuidora, automotriz...)
    industry: Optional[str] = None         # industria libre (compat con filtro actual)
    segment: Optional[str] = None          # pyme | mediana | corporativo
    required_fields: List[str] = Field(default_factory=list)  # website|email|phone|any
    online: Optional[str] = None           # compat con filtro actual: website|email|phone|any
    status: Optional[str] = None           # new|contacted|qualified|proposal|won|lost
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    sort: str = "newest"
    scope: Optional[str] = None            # city|region|country|multi|global (metadata)
    page: int = 1
    page_size: int = 20
    cursor: Optional[str] = None           # paginación por cursor (opcional)

    def filter_fields(self) -> dict:
        """Representación plana de filtros activos (para guardar búsquedas / debug)."""
        return {
            "query": self.query,
            "entity_type": self.entity_type,
            "country": self.country,
            "region": self.region,
            "city": self.city,
            "category": self.category,
            "industry": self.industry,
            "segment": self.segment,
            "required_fields": self.required_fields,
            "online": self.online,
            "status": self.status,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "sort": self.sort,
            "scope": self.scope,
        }


class SearchResult(BaseModel):
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    next_cursor: Optional[str] = None
    query: Optional[SearchQuery] = None


def _to_response(lead: Lead, db: Optional[Session] = None, sq: Optional[SearchQuery] = None) -> LeadResponse:
    """LeadResponse + campos de Fase 4 (relevance/quality/opportunity/reasons)."""
    return LeadResponse(**enrich_lead_dict(lead, db=db, sq=sq))


def _encode_cursor(lead: Lead) -> str:
    """Cursor keyset: base64(created_at_iso|id). Válido para sort newest/oldest."""
    ts = lead.created_at.isoformat() if lead.created_at else ""
    raw = f"{ts}|{lead.id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple:
    """Devuelve (created_at_iso, id) del cursor."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        ts, lid = raw.split("|", 1)
        return ts, lid
    except Exception:
        return "", ""


class SearchEngine:
    """Ejecuta un SearchQuery contra la base de leads (SQLAlchemy)."""

    def execute(self, db: Session, sq: SearchQuery) -> SearchResult:
        query = db.query(Lead)

        # --- texto libre (full-text sobre campos clave) ---
        if sq.query:
            like = f"%{sq.query.strip()}%"
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

        # --- industria / categoría ---
        industry = sq.industry or sq.category
        if industry:
            query = query.filter(Lead.industry.ilike(f"%{industry}%"))

        if sq.segment:
            query = query.filter(Lead.segment == sq.segment)

        if sq.status:
            try:
                query = query.filter(Lead.status == LeadStatus(sq.status))
            except ValueError:
                pass

        # --- geografía (region/city) con normalización acentos/case ---
        geo_term = sq.region or sq.city
        if geo_term:
            ngeo = norm(geo_term)
            pairs = db.query(Lead.id, Lead.region).filter(Lead.region.isnot(None)).all()
            ids = [
                lid for lid, reg in pairs
                if reg and any(ngeo in norm(part) for part in reg.split(","))
            ]
            query = query.filter(Lead.id.in_(ids))

        # --- presencia online / required_fields ---
        online_terms = set(sq.required_fields or [])
        if sq.online:
            online_terms.add(sq.online)
        if "any" in online_terms:
            query = query.filter(or_(Lead.website.isnot(None), Lead.email.isnot(None), Lead.phone.isnot(None)))
        else:
            col_map = {"website": Lead.website, "email": Lead.email, "phone": Lead.phone}
            for term in online_terms:
                if term in col_map:
                    query = query.filter(col_map[term].isnot(None))

        # --- score ---
        if sq.min_score is not None:
            query = query.filter(Lead.score >= sq.min_score)
        if sq.max_score is not None:
            query = query.filter(Lead.score <= sq.max_score)

        total = query.count()

        # --- orden ---
        sort = sq.sort if sq.sort in SORT_OPTIONS else "newest"
        if sort == "score":
            query = query.order_by(Lead.score.desc(), Lead.created_at.desc())
        elif sort == "oldest":
            query = query.order_by(Lead.created_at.asc(), Lead.id.asc())
        elif sort == "company":
            query = query.order_by(Lead.company.asc())
        else:
            query = query.order_by(Lead.created_at.desc(), Lead.id.desc())

        # --- paginación: cursor (keyset) o page/page_size ---
        page = max(1, sq.page)
        page_size = max(1, min(200, sq.page_size))
        next_cursor = None

        if sq.cursor and sort in ("newest", "oldest"):
            ts, lid = _decode_cursor(sq.cursor)
            if ts:
                try:
                    ts_dt = datetime.fromisoformat(ts)
                except ValueError:
                    ts_dt = None
                if ts_dt:
                    if sort == "newest":
                        query = query.filter(
                            or_(
                                Lead.created_at < ts_dt,
                                and_(Lead.created_at == ts_dt, Lead.id < lid),
                            )
                        )
                    else:
                        query = query.filter(
                            or_(
                                Lead.created_at > ts_dt,
                                and_(Lead.created_at == ts_dt, Lead.id > lid),
                            )
                        )
            rows = query.limit(page_size + 1).all()
            if len(rows) > page_size:
                next_cursor = _encode_cursor(rows[page_size - 1])
                rows = rows[:page_size]
        else:
            rows = query.offset((page - 1) * page_size).limit(page_size + 1).all()
            if len(rows) > page_size:
                next_cursor = _encode_cursor(rows[page_size - 1])
                rows = rows[:page_size]

        return SearchResult(
            items=[_to_response(r, db=db, sq=sq) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
            next_cursor=next_cursor,
            query=sq,
        )


search_engine = SearchEngine()
