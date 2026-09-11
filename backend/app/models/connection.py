"""External connection registry without credential material."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, JSON, String, Text, Uuid

from app.database import Base


class Connection(Base):
    """A configured external boundary; secrets stay in the secret store/env."""

    __tablename__ = "connections"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    type = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, default="configured")
    capabilities = Column(JSON, nullable=False, default=list)
    config_reference = Column(Text, nullable=True)
    last_check = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
