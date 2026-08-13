"""Motor de descubrimiento de leads: corre fuentes, deduplica, puntúa y guarda."""

import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .models import Lead, LeadHuntRun, LeadStatus, LeadEvent
from .sources import get_all_sources
from .service import compute_score

# Sufijos legales que no cuentan para dedupe
LEGAL_SUFFIX_RE = re.compile(
    r"\b(s\.?a\.?|s\.?r\.?l\.?|s\.?a\.?c\.?i\.?|e\.?i\.?r\.?l\.?|"
    r"ltda?\.?|inc\.?|corp\.?|co\.?|sociedad anonima|sociedad de responsabilidad limitada)\b",
    re.I,
)


def normalize_company(name: str) -> str:
    """Nombre normalizado para detectar duplicados: 'Cooperativa Ypacarai S.A.' -> 'cooperativa ypacarai'."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))  # quita acentos
    name = LEGAL_SUFFIX_RE.sub(" ", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    return re.sub(r"\s+", " ", name).strip()


def domain_of(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.match(r"https?://(?:www\.)?([^/]+)", url.strip())
    return m.group(1).lower() if m else None


def _is_duplicate(db: Session, company: str, website: Optional[str], phone: Optional[str]) -> bool:
    norm = normalize_company(company)
    if not norm:
        return False
    domain = domain_of(website)

    existing = db.query(Lead).all()
    for lead in existing:
        if normalize_company(lead.company or "") == norm:
            return True
        if domain and domain_of(lead.website) == domain and domain:
            return True
        if phone and lead.phone and re.sub(r"\D", "", phone)[-8:] == re.sub(r"\D", "", lead.phone)[-8:]:
            return True
    return False


def add_event(db: Session, lead_id: str, event_type: str, description: Optional[str] = None) -> LeadEvent:
    """Registra un evento en el timeline del lead."""
    event = LeadEvent(lead_id=lead_id, event_type=event_type, description=description)
    db.add(event)
    return event


def run_discovery(db: Session, source: Optional[str] = None, limit: Optional[int] = None, job_id: Optional[str] = None) -> dict:
    """Corre una (o todas) las fuentes y agrega leads nuevos. Devuelve resumen."""
    sources = get_all_sources()
    if source:
        if source not in sources:
            raise ValueError(f"Fuente desconocida: {source}. Disponibles: {', '.join(sources)}")
        sources = {source: sources[source]}

    results = []
    total_found = total_added = total_dupes = 0

    for name, src in sources.items():
        run = LeadHuntRun(source=name, status="running")
        if job_id:
            run.job_id = job_id
        db.add(run)
        db.commit()

        try:
            items = src.fetch(limit=limit)
            found = len(items)
            added = 0
            dupes = 0

            for item in items:
                company = (item.get("company") or "").strip()
                if not company:
                    continue
                if _is_duplicate(db, company, item.get("website"), item.get("phone")):
                    dupes += 1
                    continue

                lead = Lead(
                    company=company,
                    contact_name=item.get("contact_name"),
                    email=item.get("email"),
                    phone=item.get("phone"),
                    website=item.get("website"),
                    source=name,
                    industry=item.get("industry"),
                    segment=item.get("segment"),
                    region=item.get("region"),
                    status=LeadStatus.NEW,
                    notes=(item.get("address") or None),
                    meta=item.get("meta") or {},
                    job_id=job_id,
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
                db.flush()  # para tener lead.id
                add_event(
                    db, lead.id, "created",
                    f"Lead descubierto por fuente '{name}'" + (f" en {item.get('region')}" if item.get("region") else ""),
                )
                added += 1

            run.status = "completed"
            run.found = found
            run.added = added
            run.duplicates = dupes
            run.finished_at = datetime.utcnow()
            db.commit()

            total_found += found
            total_added += added
            total_dupes += dupes
            results.append({"source": name, "found": found, "added": added, "duplicates": dupes, "status": "completed"})
        except Exception as e:  # noqa: BLE001
            run.status = "error"
            run.error = str(e)[:500]
            run.finished_at = datetime.utcnow()
            db.commit()
            results.append({"source": name, "found": 0, "added": 0, "duplicates": 0, "status": "error", "error": str(e)[:300]})

    return {
        "results": results,
        "total_found": total_found,
        "total_added": total_added,
        "total_duplicates": total_dupes,
    }


def run_discovery_job():
    """Wrapper para scheduler/CLI: abre su propia sesión."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        return run_discovery(db)
    finally:
        db.close()
