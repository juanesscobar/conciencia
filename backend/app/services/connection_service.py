"""Read-only connection registry and truthful connector boundaries."""

from __future__ import annotations

import re

from sqlalchemy import inspect

from app.models.connection import Connection

LINTEAM_CAPABILITIES = [
    "linteam.task.create", "linteam.task.update", "linteam.report.publish",
    "linteam.deliverable.create", "linteam.comment.create",
]


def _table_available(db) -> bool:
    return inspect(db.get_bind()).has_table(Connection.__tablename__)


def _serialize(connection: Connection) -> dict:
    reference = connection.config_reference
    if reference and re.search(r"(key|secret|token|password|bearer)", reference, re.IGNORECASE):
        reference = "[redacted configuration reference]"
    return {
        "id": str(connection.id),
        "name": connection.name,
        "type": connection.type,
        "status": connection.status,
        "capabilities": connection.capabilities or [],
        "config_reference": reference,
        "last_check": connection.last_check.isoformat() if connection.last_check else None,
    }


def linteam_contract_state() -> dict:
    """Expose the future boundary without inventing an API contract."""
    return {
        "id": "linteam",
        "name": "LINTEAM",
        "type": "REST API",
        "status": "contract_required",
        "capabilities": LINTEAM_CAPABILITIES,
        "config_reference": None,
        "last_check": None,
        "reason": "LINTEAM API contract and authentication are not configured.",
        "external_writes": "approval_required",
    }


def list_connections(db) -> list[dict]:
    rows = [_serialize(row) for row in db.query(Connection).order_by(Connection.name).all()] if _table_available(db) else []
    if not any(row["name"].casefold() == "linteam" for row in rows):
        rows.append(linteam_contract_state())
    return rows


def inspect_connection(db, name: str) -> dict | None:
    if name.casefold() == "linteam":
        if not _table_available(db):
            return linteam_contract_state()
        row = db.query(Connection).filter(Connection.name.ilike("linteam")).first()
        return _serialize(row) if row else linteam_contract_state()
    if not _table_available(db):
        return None
    row = db.query(Connection).filter(Connection.name.ilike(name)).first()
    return _serialize(row) if row else None


def doctor_connection(db, name: str) -> dict | None:
    row = inspect_connection(db, name)
    if not row:
        return None
    if row["status"] == "contract_required":
        return {**row, "state": "blocked", "action": "Define the LINTEAM API contract before configuring a connector."}
    state = "ready" if row["status"] == "ready" else "configured"
    return {**row, "state": state, "action": None if state == "ready" else "Run the connector-specific check before external use."}
