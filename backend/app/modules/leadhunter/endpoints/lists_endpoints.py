"""Endpoints de búsquedas guardadas + listas de leads."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user

from ..models import Lead, LeadList, LeadSavedSearch
from ..schemas import (
    LeadSavedSearchCreate,
    LeadSavedSearchResponse,
    SavedLeadListCreate,
    SavedLeadListResponse,
    SavedLeadListDetailResponse,
    SavedLeadListAddRequest,
)
from ..helpers import _to_response, _get_lead_or_404

router = APIRouter(tags=["leadhunter"], dependencies=[Depends(get_current_user)])


@router.get("/searches", response_model=list[LeadSavedSearchResponse])
def list_saved_searches(db: Session = Depends(get_db)):
    """Búsquedas guardadas (snapshots de filtros)."""
    items = db.query(LeadSavedSearch).order_by(LeadSavedSearch.created_at.desc()).all()
    return [LeadSavedSearchResponse(**s.to_dict()) for s in items]


@router.post("/searches", response_model=LeadSavedSearchResponse, status_code=201)
def create_saved_search(req: LeadSavedSearchCreate, db: Session = Depends(get_db)):
    """Guarda la búsqueda actual (filtros de la tabla de leads)."""
    search = LeadSavedSearch(name=req.name.strip(), filters=req.filters or {})
    db.add(search)
    db.commit()
    db.refresh(search)
    return LeadSavedSearchResponse(**search.to_dict())


@router.delete("/searches/{search_id}", status_code=204)
def delete_saved_search(search_id: str, db: Session = Depends(get_db)):
    """Elimina una búsqueda guardada."""
    search = db.query(LeadSavedSearch).filter(LeadSavedSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Búsqueda guardada no encontrada")
    db.delete(search)
    db.commit()
    return None


@router.get("/lists", response_model=list[SavedLeadListResponse])
def list_lead_lists(db: Session = Depends(get_db)):
    """Listas de leads guardadas (ej: 'Seguimiento marzo', 'Distribuidoras Gran Asunción')."""
    items = db.query(LeadList).order_by(LeadList.created_at.desc()).all()
    return [SavedLeadListResponse(**l.to_dict()) for l in items]


@router.post("/lists", response_model=SavedLeadListResponse, status_code=201)
def create_lead_list(req: SavedLeadListCreate, db: Session = Depends(get_db)):
    """Crea una lista de leads."""
    lst = LeadList(name=req.name.strip(), description=req.description)
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return SavedLeadListResponse(**lst.to_dict())


@router.delete("/lists/{list_id}", status_code=204)
def delete_lead_list(list_id: str, db: Session = Depends(get_db)):
    """Elimina una lista (no borra los leads)."""
    lst = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    db.delete(lst)
    db.commit()
    return None


@router.post("/lists/{list_id}/leads", response_model=SavedLeadListResponse)
def add_lead_to_list(list_id: str, req: SavedLeadListAddRequest, db: Session = Depends(get_db)):
    """Agrega un lead a una lista (idempotente)."""
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
    lst = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    d = lst.to_dict()
    d["leads"] = [_to_response(l, db=db) for l in lst.leads]
    return SavedLeadListDetailResponse(**d)


@router.get("/{lead_id}/lists", response_model=list[SavedLeadListResponse])
def lead_lists(lead_id: str, db: Session = Depends(get_db)):
    """Listas a las que pertenece un lead."""
    _get_lead_or_404(db, lead_id)
    lists = db.query(LeadList).filter(LeadList.leads.any(Lead.id == lead_id)).all()
    return [SavedLeadListResponse(**l.to_dict()) for l in lists]
