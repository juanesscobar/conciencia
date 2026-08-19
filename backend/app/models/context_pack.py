"""Context Pack - contexto canónico estructurado y transferible (spec §28-30).

Un Context Pack es UNA representación canónica del contexto relevante,
que puede exportarse como: system prompt / coding agent context /
markdown / JSON (Context Adapters, §30).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON

from app.database import Base


class ContextPack(Base):
    __tablename__ = "context_packs"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title = Column(String(200), nullable=False)
    project_id = Column(String(50), nullable=True)
    source = Column(String(50), default="conciencia")     # de dónde se generó
    target = Column(String(50), nullable=True)            # para qué destino (qwen_code, claude_code, ...)
    content = Column(JSON, nullable=False, default=dict)  # estructura canónica
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "project_id": self.project_id,
            "source": self.source,
            "target": self.target,
            "content": self.content or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
