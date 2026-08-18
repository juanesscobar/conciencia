"""Tool Registry (MCP) - servidores MCP adjuntables y sus tools.

Config: settings key MCP_SERVERS (JSON array):
    [{"name": "email", "command": "python", "args": ["-m", "app.services.mcp.email_server"], "enabled": true}]

El server de email built-in se registra automáticamente si no existe.
"""

import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException

from app.database import SessionLocal
from app.models.setting import Setting
from app.services.mcp.client import MCPClient, MCPError

log = logging.getLogger("mcp.registry")

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])

MCP_SETTINGS_KEY = "MCP_SERVERS"

BUILTIN_EMAIL_SERVER = {
    "name": "email",
    "label": "Email (IMAP/SMTP multi-proveedor)",
    "command": "python",
    "args": ["-m", "app.services.mcp.email_server"],
    "builtin": True,
}


def _db() -> SessionLocal:
    return SessionLocal()


def _get_servers_config() -> list:
    db = _db()
    try:
        row = db.query(Setting).filter(Setting.key == MCP_SETTINGS_KEY).first()
        if not row or not row.value:
            return [dict(BUILTIN_EMAIL_SERVER, enabled=True)]
        try:
            servers = json.loads(row.value)
        except json.JSONDecodeError:
            servers = []
        names = {s.get("name") for s in servers}
        if "email" not in names:
            servers.append(dict(BUILTIN_EMAIL_SERVER, enabled=True))
        return servers
    finally:
        db.close()


def _client_for(server: dict) -> MCPClient:
    return MCPClient(
        name=server["name"],
        command=server["command"],
        args=server.get("args") or [],
        env=server.get("env"),
        cwd=server.get("cwd"),
    )


@router.get("/servers")
def list_servers():
    servers = _get_servers_config()
    out = []
    for s in servers:
        out.append({k: v for k, v in s.items() if k != "env"})
    return out


@router.get("/servers/{name}/tools")
def list_tools(name: str):
    server = next((s for s in _get_servers_config() if s["name"] == name), None)
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' no registrado")
    client = _client_for(server)
    try:
        return {"server": name, "tools": client.list_tools()}
    except MCPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        client.close()


@router.post("/servers/{name}/call")
def call_tool(name: str, body: dict):
    tool = body.get("tool")
    arguments = body.get("arguments") or {}
    if not tool:
        raise HTTPException(status_code=400, detail="Falta 'tool'")
    server = next((s for s in _get_servers_config() if s["name"] == name), None)
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' no registrado")
    client = _client_for(server)
    try:
        result = client.call_tool(tool, arguments)
        return {"server": name, "tool": tool, "result": result}
    except MCPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        client.close()
