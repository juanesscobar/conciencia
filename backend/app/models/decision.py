"""Decision Memory - decisiones de arquitectura/producto como objetos de primera clase (spec §26)."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, JSON, Integer

from app.database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    number = Column(Integer, nullable=False)          # 42 -> DEC-042
    title = Column(String(200), nullable=False)
    decision = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    rejected = Column(JSON, default=list)             # alternativas descartadas
    impact = Column(JSON, default=list)               # UX, Data model, API, ...
    links = Column(JSON, default=dict)                # {projects, missions, tasks, agents, files, commits}
    status = Column(String(20), default="accepted")   # accepted | proposed | superseded
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "number": self.number,
            "ref": f"DEC-{self.number:03d}",
            "title": self.title,
            "decision": self.decision,
            "reason": self.reason,
            "rejected": self.rejected or [],
            "impact": self.impact or [],
            "links": self.links or {},
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
