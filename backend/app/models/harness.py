"""Harness — contrato versionado y reutilizable de ejecución de agentes (master prompt §G).

Un Harness formaliza CÓMO ejecuta un agente, independiente de quién es:

  instructions     — system prompt base (template con placeholders {objective} {project_name} ...)
  context          — {template, max_chars, include_context_pack: bool}
  tools            — {allow: [...], deny: [...]} allowlist de herramientas
  validation       — {input: {rules}, output: {rules}} (ej: required_fields, min_length, format)
  guardrails       — [no_network, max_tokens, require_approval, ...] constraints
  runtime          — {default: "generic", allowed: ["generic", "claude_code", ...]}
  output_contract  — {format: "json"|"markdown"|"text", required_fields: [...], description}

Versionado: cada update con new_version guarda el snapshot anterior en `versions`
(historial). Un Harness activo puede reusarse en cualquier Mission (mission.harness_id).

Nota de diseño: spec/status usan String/JSON (sin enums de Postgres) para evitar
ALTER TYPE en prod.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, JSON, Uuid

from app.database import Base

HARNESS_STATUSES = ["draft", "active", "archived"]

DEFAULT_HARNESS_SPEC = {
    "instructions": "",
    "context": {"template": "", "max_chars": 6000, "include_context_pack": True},
    "tools": {"allow": [], "deny": []},
    "validation": {"input": {}, "output": {}},
    "guardrails": [],
    "runtime": {"default": "generic", "allowed": ["generic"]},
    "output_contract": {"format": "text", "required_fields": [], "description": ""},
}


class Harness(Base):
    __tablename__ = "harnesses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0.0")
    description = Column(Text)
    spec = Column(JSON, nullable=False, default=dict)      # DEFAULT_HARNESS_SPEC
    status = Column(String(20), default="draft")            # HARNESS_STATUSES
    versions = Column(JSON, default=list)                   # historial [{version, changes, updated_at}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "spec": self.spec or {},
            "status": self.status,
            "versions": self.versions or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
