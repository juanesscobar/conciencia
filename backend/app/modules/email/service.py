"""Servicio de email: envío (SMTP) y lectura (IMAP). Stdlib puro.

send_email / list_inbox / search_inbox / test_connection
Reciben un dict de cuenta (model EmailAccount + config resuelta).
"""

import imaplib
import smtplib
import ssl
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional

from .providers import resolve_provider


class EmailError(Exception):
    pass


def _resolve(account: dict) -> dict:
    cfg = resolve_provider(account.get("provider", "generic"), account)
    if not cfg["imap_host"] or not cfg["smtp_host"]:
        raise EmailError("Faltan hosts IMAP/SMTP: usá el preset del proveedor o completá los overrides.")
    username = (account.get("username") or "").strip() or (account.get("email") or "").strip()
    if not username or not account.get("password"):
        raise EmailError("Faltan credenciales (username/password).")
    return {**cfg, "username": username, "password": account["password"]}


def send_email(
    account: dict,
    to_email: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> dict:
    r = _resolve(account)
    msg = EmailMessage()
    from_name = (account.get("from_name") or "").strip()
    msg["From"] = f"{from_name} <{r['username']}>" if from_name else r["username"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        if r["smtp_port"] == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(r["smtp_host"], r["smtp_port"], timeout=30, context=context) as s:
                s.login(r["username"], r["password"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(r["smtp_host"], r["smtp_port"], timeout=30) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(r["username"], r["password"])
                s.send_message(msg)
    except Exception as e:  # noqa: BLE001
        raise EmailError(f"SMTP send failed: {e}")

    return {"ok": True, "to": to_email, "subject": subject}


def _decode(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for data, enc in parts:
        if isinstance(data, bytes):
            try:
                out.append(data.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                out.append(data.decode("utf-8", errors="replace"))
        else:
            out.append(data)
    return "".join(out)


def _decode_body(msg) -> str:
    """Extrae el cuerpo del email (texto plano preferido, fallback HTML->texto)."""
    import re

    if msg.is_multipart():
        text_part = None
        html_part = None
        for part in msg.walk():
            ct = (part.get_content_type() or "").lower()
            if ct == "text/plain" and text_part is None:
                text_part = part
            elif ct == "text/html" and html_part is None:
                html_part = part
        if text_part is not None:
            payload = text_part.get_payload(decode=True) or b""
            charset = text_part.get_content_charset() or "utf-8"
            try:
                return payload.decode(charset, errors="replace")
            except LookupError:
                return payload.decode("utf-8", errors="replace")
        if html_part is not None:
            payload = html_part.get_payload(decode=True) or b""
            charset = html_part.get_content_charset() or "utf-8"
            try:
                html = payload.decode(charset, errors="replace")
            except LookupError:
                html = payload.decode("utf-8", errors="replace")
            # strip tags para dejar texto legible
            html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
            html = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", html, flags=re.I)
            html = re.sub(r"<[^>]+>", "", html)
            return re.sub(r"\n{3,}", "\n\n", html).strip()
        return ""
    payload = msg.get_payload(decode=True) or b""
    if not payload:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _parse_message(raw: bytes) -> dict:
    import email as email_lib
    msg = email_lib.message_from_bytes(raw)
    body = _decode_body(msg).strip()
    return {
        "from": _decode(msg.get("From", "")),
        "to": _decode(msg.get("To", "")),
        "subject": _decode(msg.get("Subject", "")) or "(sin asunto)",
        "date": msg.get("Date", ""),
        "message_id": msg.get("Message-ID", ""),
        "body": body[:4000],  # preview del cuerpo (sin attachments)
    }


def list_inbox(account: dict, limit: int = 20, folder: str = "INBOX") -> List[dict]:
    r = _resolve(account)
    try:
        imap = imaplib.IMAP4_SSL(r["imap_host"], r["imap_port"], timeout=30)
        imap.login(r["username"], r["password"])
        try:
            imap.select(folder)
            status, data = imap.search(None, "ALL")
            if status != "OK":
                return []
            ids = data[0].split()
            selected = ids[-limit:] if limit > 0 else ids
            messages = []
            for mid in reversed(selected):
                status, mdata = imap.fetch(mid, "(RFC822)")
                if status != "OK" or not mdata or not isinstance(mdata[0], tuple):
                    continue
                messages.append(_parse_message(mdata[0][1]))
            return messages
        finally:
            imap.logout()
    except Exception as e:  # noqa: BLE001
        raise EmailError(f"IMAP fetch failed: {e}")


def test_connection(account: dict) -> dict:
    r = _resolve(account)
    result = {"imap": False, "smtp": False, "error": None}
    try:
        imap = imaplib.IMAP4_SSL(r["imap_host"], r["imap_port"], timeout=20)
        imap.login(r["username"], r["password"])
        imap.logout()
        result["imap"] = True
    except Exception as e:  # noqa: BLE001
        result["error"] = f"IMAP: {e}"
        return result
    try:
        if r["smtp_port"] == 465:
            with smtplib.SMTP_SSL(r["smtp_host"], r["smtp_port"], timeout=20, context=ssl.create_default_context()) as s:
                s.login(r["username"], r["password"])
        else:
            with smtplib.SMTP(r["smtp_host"], r["smtp_port"], timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(r["username"], r["password"])
        result["smtp"] = True
    except Exception as e:  # noqa: BLE001
        result["error"] = f"SMTP: {e}"
    return result
