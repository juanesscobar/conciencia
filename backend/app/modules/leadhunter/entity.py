"""Entity resolution / Dedupe v2 (spec §12).

Reemplaza el dedupe O(n²) (`db.query(Lead).all()` por candidato) por lookups
indexados contra columnas normalizadas (`leads.normalized_name`,
`leads.normalized_phone`, dominio y email normalizado).
"""

from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .models import Lead
from .normalization import domain_of, norm_email, norm_phone, normalize_company


def find_duplicates(
    db: Session,
    company: Optional[str] = None,
    website: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    exclude_id: Optional[str] = None,
) -> List[Lead]:
    """Devuelve leads existentes que matchean por nombre, dominio, teléfono o email.

    Lookups indexados (normalized_name / normalized_phone / email) — sin
    full-scan. Se puede excluir un lead (para updates).
    """
    hits: dict = {}

    if company:
        nname = normalize_company(company)
        if nname:
            for lead in db.query(Lead).filter(Lead.normalized_name == nname).all():
                if lead.id != exclude_id:
                    hits[lead.id] = lead

    if website:
        domain = domain_of(website)
        if domain:
            for lead in db.query(Lead).filter(Lead.normalized_domain == domain).all():
                if lead.id != exclude_id:
                    hits[lead.id] = lead

    if phone:
        nphone = norm_phone(phone)
        if nphone:
            for lead in db.query(Lead).filter(Lead.normalized_phone == nphone).all():
                if lead.id != exclude_id:
                    hits[lead.id] = lead

    if email:
        nemail = norm_email(email)
        if nemail:
            for lead in db.query(Lead).filter(Lead.email == nemail).all():
                if lead.id != exclude_id:
                    hits[lead.id] = lead

    return list(hits.values())


def is_duplicate(
    db: Session,
    company: Optional[str] = None,
    website: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    exclude_id: Optional[str] = None,
) -> bool:
    """True si existe al menos un lead duplicado (dedupe v2 indexado)."""
    return bool(find_duplicates(db, company, website, phone, email, exclude_id=exclude_id))


def apply_normalization(lead: Lead) -> Lead:
    """Puebla normalized_name / normalized_domain / normalized_phone (idempotente)."""
    lead.normalized_name = normalize_company(lead.company)
    lead.normalized_domain = domain_of(lead.website)
    lead.normalized_phone = norm_phone(lead.phone)
    return lead
