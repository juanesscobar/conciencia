"""WhatsApp Business API router — estado, QR, conexión y envío."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.user import User
from app.services.auth import get_current_user

from . import bridge

router = APIRouter(
    prefix="/api/v1/whatsapp",
    tags=["whatsapp"],
    dependencies=[Depends(get_current_user)],
)


class SendRequest(BaseModel):
    to: str  # E.164: 595981123456
    message: str


@router.get("/status")
def wa_status():
    """Estado de la sesión + QR (base64 PNG) cuando está en estado qr."""
    status = bridge.get_status()
    return {
        "ok": status.get("ok", False),
        "state": status.get("state", "error"),
        "qr": status.get("qr") if status.get("state") == "qr" else None,
        "phone": status.get("phone"),
        "error": status.get("error"),
    }


@router.post("/connect")
def wa_connect():
    """Inicia el cliente WhatsApp Web. El QR aparece en GET /status."""
    return bridge.connect()


@router.post("/disconnect")
def wa_disconnect():
    """Cierra la sesión (logout) y borra el estado local."""
    return bridge.disconnect()


@router.post("/send")
def wa_send(req: SendRequest):
    """Envía un mensaje de texto. Requiere sesión conectada."""
    status = bridge.get_status()
    if status.get("state") != "connected":
        raise HTTPException(status_code=409, detail="WhatsApp no conectado. Escaneá el QR en Configuración → Integraciones.")
    result = bridge.send_message(req.to.strip(), req.message)
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error enviando el mensaje"))
    return result
