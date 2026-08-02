from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ActivityBase(BaseModel):
    type: str
    description: str
    external_url: Optional[str] = None


class ActivityCreate(ActivityBase):
    project_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    metadata: Optional[dict] = None  # compat: alias de extra_data
    extra_data: Optional[dict] = None


class Activity(ActivityBase):
    id: UUID
    project_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    created_at: datetime
    metadata: dict = {}
    extra_data: dict = {}

    @model_validator(mode="before")
    @classmethod
    def map_extra_data(cls, data):
        """Convierte el ORM (o dict) al formato del schema.

        El modelo SQLAlchemy tiene `extra_data` (JSON); el schema expone
        `metadata` por compatibilidad. SQLAlchemy también tiene un atributo
        interno `metadata` que NO debe usarse.
        """
        if isinstance(data, dict):
            d = dict(data)
        else:
            d = data.__dict__.copy()
        extra = d.get("extra_data") or d.get("metadata") or {}
        d["extra_data"] = extra
        d["metadata"] = extra
        return d

    class Config:
        from_attributes = True
