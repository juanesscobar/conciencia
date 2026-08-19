"""Costos de LLM persistidos (Control Plane - Costs).

Cada uso del harness (proveedor/modelo/tokens/costo) se persiste
para observabilidad y reporting real de costos.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Float, Integer, JSON

from app.database import Base


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    meta = Column(JSON, default=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "metadata": self.meta or {},
        }
