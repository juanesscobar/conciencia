from sqlalchemy import Column, String, DateTime, Text
from app.database import Base
import uuid
from datetime import datetime


class Setting(Base):
    """Configuración persistente clave-valor (API keys, preferencias, etc.)."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
