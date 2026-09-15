"""Team — agrupación de agentes especializados (master prompt §F / Phase F).

Un Team es un conjunto de agentes con un propósito (ej: "research squad",
"delivery squad"). Una Mission puede apuntar a un team: el workflow resuelve
los steps por capabilities DENTRO del team primero (fallback al registry
global), y el runtime default del team aplica a la misión.

Nota de diseño: member_ids es JSON de UUIDs-string (mismo patrón que
Mission.agent_ids). status/type usan String para evitar ALTER TYPE en prod.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, JSON, Uuid
from sqlalchemy.orm import relationship

from app.database import Base

# Estados del ciclo de vida de un team
TEAM_STATUSES = ["active", "paused", "archived"]


class Team(Base):
    __tablename__ = "teams"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    purpose = Column(String(255), nullable=True)      # para qué se usa este team
    emoji = Column(String(10), default="👥")

    status = Column(String(20), default="active")     # TEAM_STATUSES
    member_ids = Column(JSON, default=list)           # agent UUIDs como strings
    default_runtime = Column(String(50), default="generic")
    config = Column(JSON, default=dict)               # {coordinator_agent_id, max_parallel, ...}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "purpose": self.purpose,
            "emoji": self.emoji,
            "status": self.status,
            "member_ids": self.member_ids or [],
            "default_runtime": self.default_runtime,
            "config": self.config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
