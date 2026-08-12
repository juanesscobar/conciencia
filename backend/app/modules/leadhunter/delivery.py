"""Entrega de propuestas: email (SMTP o mailto) y WhatsApp (deep link)."""

import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from urllib.parse import quote


def _db_setting(key: str) -> str:
    try:
        from app.database import SessionLocal
        from app.models.setting import Setting
        db = SessionLocal()
        try:
            s = db.query(Setting).filter(Setting.key == key).first()
            return s.value if s and s.value else ""
        finally:
            db.close()
    except Exception:
        return ""


def _clean_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits.startswith("595") and digits.startswith("0"):
        digits = "595" + digits[1:]
    return digits


def _plain_text(content: str) -> str:
    """Convierte markdown simple a texto plano legible."""
    text = re.sub(r"^#{1,6}\s*", "", content, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^[-\*]\s+", "• ", text, flags=re.M)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.M)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    return text.strip()


def build_delivery_links(proposal, lead) -> dict:
    """Arma los canales disponibles para enviar la propuesta (sin enviar nada)."""
    body = _plain_text(proposal.content or "")
    subject = f"Propuesta comercial — {lead.company}"
    links = {"subject": subject, "body": body, "channels": {}}

    # Email
    if lead.email:
        mailto = (
            f"mailto:{lead.email}?subject={quote(subject)}&body={quote(body)}"
        )
        links["channels"]["email"] = {
            "to": lead.email,
            "mailto": mailto,
            "smtp_configured": bool(os.getenv("SMTP_HOST") or _db_setting("SMTP_HOST")),
        }

    # WhatsApp
    if lead.phone:
        phone = _clean_phone(lead.phone)
        wa_text = f"Hola {lead.contact_name or ''}, te compartimos la propuesta de {subject}:\n\n{body}"
        links["channels"]["whatsapp"] = {
            "to": phone,
            "display": lead.phone,
            "text": wa_text,
            "url": f"https://wa.me/{phone}?text={quote(wa_text)}",
        }

    return links


def send_email(to_email: str, subject: str, body: str, pdf_bytes: Optional[bytes] = None, pdf_filename: Optional[str] = None) -> dict:
    """Envía el email por SMTP (configurado en Settings). Si no hay SMTP, devuelve mailto."""
    host = os.getenv("SMTP_HOST") or _db_setting("SMTP_HOST")
    if not host:
        mailto = f"mailto:{to_email}?subject={quote(subject)}&body={quote(body)}"
        return {"sent": False, "method": "mailto", "url": mailto, "reason": "SMTP no configurado — se abre el cliente de correo"}

    port = int(os.getenv("SMTP_PORT") or _db_setting("SMTP_PORT") or "587")
    user = os.getenv("SMTP_USER") or _db_setting("SMTP_USER")
    password = os.getenv("SMTP_PASS") or _db_setting("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM") or _db_setting("SMTP_FROM") or user or "mission-control@localhost"

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if pdf_bytes:
        from email.mime.application import MIMEApplication

        part = MIMEApplication(pdf_bytes, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=pdf_filename or "propuesta.pdf")
        msg.attach(part)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if port == 587 or port == 25:
                try:
                    server.starttls()
                    server.ehlo()
                except Exception:
                    pass
            if user:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return {"sent": True, "method": "smtp", "to": to_email, "attachments": [pdf_filename or "propuesta.pdf"] if pdf_bytes else []}
    except Exception as e:  # noqa: BLE001
        return {"sent": False, "method": "smtp", "error": str(e)[:300]}
