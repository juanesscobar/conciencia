from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime


class UserMemory(Base):
    """Memoria persistente por usuario — contexto individual de cada operador."""
    __tablename__ = "user_memories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="general")  # general, project, decision, preference
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="memories")
