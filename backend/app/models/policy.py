"""Policies - reglas de governance del Control Plane (Control - Governance).

Efecto por (agent, action): allow | approval | deny.
- agent_id null => policy global (aplica a todos los agentes)
- action: categoría de acción (send_email, modify_crm, delete, deploy, ...)
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean

from app.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String(50), nullable=True)   # null = global
    action = Column(String(100), nullable=False)   # send_email, modify_crm, delete, deploy...
    effect = Column(String(20), nullable=False)    # allow | approval | deny
    note = Column(String(300), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name if hasattr(self, "agent_name") else None,
            "action": self.action,
            "effect": self.effect,
            "note": self.note,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
