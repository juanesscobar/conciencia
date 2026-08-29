"""Endpoints CRUD de leads + pipeline actions + import CSV + intake webhook."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user

from ..models import Lead, LeadStatus, LeadEvent
from ..schemas import (
    LeadCreate,
    LeadUpdate,
    LeadIntake,
    LeadResponse,
    LeadEventResponse,
    ActionRequest,
    ImportResult,
    EnrichResult,
)
from ..helpers import _to_response, _get_lead_or_404, _recompute_score
from ..discovery import add_event, _is_duplicate
from ..entity import apply_normalization
from ..enrich import enrich_from_website

router = APIRouter(tags=["leadhunter"], dependencies=[Depends(get_current_user)])
intake_router = APIRouter(tags=["leadhunter-intake"])  # webhook público, SIN auth


# ================== PIPELINE (acciones) ==================


@router.post("/{lead_id}/contact", response_model=LeadResponse)
def contact_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Marca el lead como contactado (primer acercamiento)."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.CONTACTED
    db.add(add_event(db, lead.id, "contacted", req.reason or "Primer contacto realizado"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


@router.post("/{lead_id}/qualify", response_model=LeadResponse)
def qualify_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Califica el lead (validado como prospecto real)."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.QUALIFIED
    db.add(add_event(db, lead.id, "qualified", req.reason or "Lead calificado como prospecto"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


@router.post("/{lead_id}/won", response_model=LeadResponse)
def won_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Cierra el lead como ganado."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.WON
    db.add(add_event(db, lead.id, "won", req.reason or "Cliente ganado"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


@router.post("/{lead_id}/lost", response_model=LeadResponse)
def lost_lead(lead_id: str, req: ActionRequest = ActionRequest(), db: Session = Depends(get_db)):
    """Cierra el lead como perdido (con motivo)."""
    lead = _get_lead_or_404(db, lead_id)
    lead.status = LeadStatus.LOST
    db.add(add_event(db, lead.id, "lost", req.reason or "Lead perdido"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


@router.post("/{lead_id}/note", response_model=LeadResponse)
def add_note(lead_id: str, req: ActionRequest, db: Session = Depends(get_db)):
    """Agrega una nota al lead (se guarda en el timeline)."""
    if not req.note or not req.note.strip():
        raise HTTPException(status_code=400, detail="note no puede estar vacía")
    lead = _get_lead_or_404(db, lead_id)
    db.add(add_event(db, lead.id, "note", req.note.strip()))
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


# ================== TIMELINE ==================


@router.get("/{lead_id}/events", response_model=list[LeadEventResponse])
def lead_events(lead_id: str, db: Session = Depends(get_db)):
    """Timeline de acciones del lead."""
    _get_lead_or_404(db, lead_id)
    events = db.query(LeadEvent).filter(LeadEvent.lead_id == lead_id).order_by(LeadEvent.created_at.desc()).all()
    return [LeadEventResponse(**e.to_dict()) for e in events]


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
            apply_normalization(lead)
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
    apply_normalization(lead)
    _recompute_score(lead)
    db.add(lead)
    db.flush()
    db.add(add_event(db, lead.id, "created", "Lead creado manualmente"))
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


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
    return _to_response(lead, db=db)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)
    return _to_response(lead, db=db)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, req: LeadUpdate, db: Session = Depends(get_db)):
    lead = _get_lead_or_404(db, lead_id)

    data = req.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(lead, field, value)

    apply_normalization(lead)

    _recompute_score(lead)
    db.commit()
    db.refresh(lead)
    return _to_response(lead, db=db)


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
    from ..service import enrich_with_ai

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
    return {"analysis": analysis, "score": lead.score, "lead": _to_response(lead, db=db)}
