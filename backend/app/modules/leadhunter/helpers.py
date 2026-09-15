"""Helpers compartidos del módulo LeadHunter (Fase 7 — slimming de router.py).

Utilidades HTTP/de dominio reutilizadas por los sub-routers de `endpoints/`.
"""

import re
import unicodedata
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Lead
from .schemas import LeadResponse
from .search import SearchQuery
from .service import compute_score
from .ranking import enrich_lead_dict

ONLINE_FILTERS = {"website", "email", "phone", "social", "any"}
SORT_OPTIONS = {"newest", "score", "company", "oldest"}

STREET_LIKE = re.compile(r"^(av|avda|avenida|calle|ruta|camino|autopista|acceso|km|pasaje|tacuara|azara|cnl|gral|san|sta|procer|eugenio|teniente)", re.I)


def _norm(s: str) -> str:
    """Normaliza para comparaciones: minúsculas, sin acentos."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _slug(text: str) -> str:
    """Slug seguro para nombres de archivo (propuestas)."""
    import unicodedata as _u
    t = _u.normalize("NFKD", text or "propuesta")
    t = "".join(c for c in t if not _u.combining(c))
    t = re.sub(r"[^a-zA-Z0-9\-_\.]+", "-", t.lower()).strip("-")
    return t or "propuesta"


def _to_response(lead: Lead, db: Optional[Session] = None, sq: Optional[SearchQuery] = None) -> LeadResponse:
    """LeadResponse + campos de Fase 4 (data_quality, opportunity, relevance, reasons)."""
    return LeadResponse(**enrich_lead_dict(lead, db=db, sq=sq))


def _get_lead_or_404(db: Session, lead_id: str) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _recompute_score(lead: Lead) -> None:
    """Recalcula el score persistido del lead (contrato histórico de compute_score)."""
    lead.score = compute_score(
        company=lead.company or "",
        industry=lead.industry or "",
        source=lead.source or "manual",
        email=lead.email or "",
        phone=lead.phone or "",
        notes=lead.notes or "",
        metadata=lead.meta,
    )
