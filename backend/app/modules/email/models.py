"""Email multi-proveedor - cuentas IMAP/SMTP.

Proveedores presets: gmail, outlook/office365, generic (IMAP/SMTP custom).
Soporta multiples cuentas. Envio via SMTP, lectura via IMAP.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, Integer

from app.database import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(100), nullable=False)          # etiqueta: "Personal", "Ventas", ...
    provider = Column(String(20), nullable=False)       # gmail | outlook | generic
    email = Column(String(200), nullable=False)         # cuenta (from + login si aplica)
    username = Column(String(200), nullable=True)       # login (default: email)
    password = Column(String(500), nullable=False)      # app password / contraseña IMAP/SMTP
    imap_host = Column(String(200), nullable=True)      # override generic
    imap_port = Column(Integer, nullable=True)
    smtp_host = Column(String(200), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    from_name = Column(String(200), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "email": self.email,
            "username": self.username,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "from_name": self.from_name,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # nunca exponer password
        }
