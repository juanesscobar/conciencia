"""API de email multi-proveedor: cuentas, inbox, envío, test."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import SessionLocal
from app.modules.email.models import EmailAccount
from app.modules.email.providers import list_providers
from app.modules.email import service


router = APIRouter(prefix="/api/v1/email", tags=["email"])


class AccountCreate(BaseModel):
    name: str
    provider: str
    email: str
    password: str
    username: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    from_name: Optional[str] = None


class AccountPatch(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    username: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    from_name: Optional[str] = None
    enabled: Optional[bool] = None


class SendRequest(BaseModel):
    to: str
    subject: str
    body: str


def _get_account(account_id: str) -> EmailAccount:
    db = SessionLocal()
    try:
        acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail="Cuenta de email no encontrada")
        return acc
    finally:
        db.close()


def _as_dict(acc: EmailAccount) -> dict:
    d = acc.to_dict()
    return d


@router.get("/providers")
def providers():
    return list_providers()


@router.get("/accounts")
def list_accounts():
    db = SessionLocal()
    try:
        return [_as_dict(a) for a in db.query(EmailAccount).order_by(EmailAccount.created_at).all()]
    finally:
        db.close()


@router.post("/accounts", status_code=201)
def create_account(req: AccountCreate):
    db = SessionLocal()
    try:
        acc = EmailAccount(
            name=req.name.strip(),
            provider=req.provider.strip().lower(),
            email=req.email.strip(),
            password=req.password,
            username=(req.username or "").strip() or None,
            imap_host=(req.imap_host or "").strip() or None,
            imap_port=req.imap_port,
            smtp_host=(req.smtp_host or "").strip() or None,
            smtp_port=req.smtp_port,
            from_name=(req.from_name or "").strip() or None,
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return _as_dict(acc)
    finally:
        db.close()


@router.patch("/accounts/{account_id}")
def patch_account(account_id: str, req: AccountPatch):
    db = SessionLocal()
    try:
        acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail="Cuenta de email no encontrada")
        for field, value in req.dict(exclude_unset=True).items():
            if value is None:
                continue
            setattr(acc, field, value)  # password se cifra solo vía @validates
        db.commit()
        db.refresh(acc)
        return _as_dict(acc)
    finally:
        db.close()


@router.delete("/accounts/{account_id}")
def delete_account(account_id: str):
    db = SessionLocal()
    try:
        acc = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail="Cuenta de email no encontrada")
        db.delete(acc)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/accounts/{account_id}/test")
def test_account(account_id: str):
    acc = _get_account(account_id)
    return service.test_connection(acc.to_service_dict())


@router.get("/accounts/{account_id}/inbox")
def inbox(account_id: str, limit: int = 20):
    acc = _get_account(account_id)
    if not acc.enabled:
        raise HTTPException(status_code=400, detail="Cuenta deshabilitada")
    try:
        return service.list_inbox(acc.to_service_dict(), limit=min(limit, 50))
    except service.EmailError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/accounts/{account_id}/send")
def send(account_id: str, req: SendRequest):
    acc = _get_account(account_id)
    if not acc.enabled:
        raise HTTPException(status_code=400, detail="Cuenta deshabilitada")
    try:
        return service.send_email(acc.to_service_dict(), req.to, req.subject, req.body)
    except service.EmailError as e:
        raise HTTPException(status_code=502, detail=str(e))
