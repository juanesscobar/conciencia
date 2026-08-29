"""Endpoints de propuestas: generación IA, manuales, envío (email/whatsapp), PDF."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user

from ..models import Lead, LeadProposal, LeadStatus
from ..schemas import (
    LeadProposalCreate,
    LeadProposalResponse,
    SendProposalRequest,
)
from ..helpers import _get_lead_or_404, _slug

router = APIRouter(tags=["leadhunter"], dependencies=[Depends(get_current_user)])


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
    from ..proposal import generate_sales_proposal

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
    from ..discovery import add_event
    db.add(proposal)
    db.add(add_event(db, lead.id, "proposal_generated", "Propuesta generada con IA (sales squad)"))
    db.commit()
    db.refresh(proposal)
    return LeadProposalResponse(**proposal.to_dict())


@router.post("/{lead_id}/proposal", response_model=LeadProposalResponse)
def create_proposal_manual(lead_id: str, req: LeadProposalCreate, db: Session = Depends(get_db)):
    """Crea una propuesta manual (pegada por el usuario)."""
    from ..discovery import add_event

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
    from ..delivery import build_delivery_links, send_email
    from ..discovery import add_event

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
            from ..pdfgen import render_proposal_pdf

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
            pdf_filename = f"propuesta-{_slug(lead.company)}.pdf"
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
    from ..delivery import build_delivery_links

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
    from ..pdfgen import render_proposal_pdf
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
