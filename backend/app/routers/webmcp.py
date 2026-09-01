"""WebMCP API — Fase K: interactuar con apps web WebMCP-enabled desde Conciencia.

POST /api/v1/webmcp/run    ejecuta un script de acciones contra una app
GET  /api/v1/webmcp/demo   info de la demo app (y cómo correrla)
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.webmcp import client as wm

router = APIRouter(prefix="/api/v1/webmcp", tags=["webmcp"], dependencies=[Depends(get_current_user)])


class WebMCPRun(BaseModel):
    url: str = Field(..., description="Base URL de la app WebMCP-enabled")
    actions: List[Dict[str, Any]] = Field(..., min_length=1)


@router.post("/run")
def webmcp_run(req: WebMCPRun, db: Session = Depends(get_db)):
    """Ejecuta acciones contra una app WebMCP-enabled y devuelve la evidencia."""
    try:
        return wm.run_script(req.url, req.actions)
    except wm.WebMCPError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/demo")
def demo_info():
    """Cómo correr la demo app WebMCP-enabled para pruebas."""
    return {
        "description": "WebMCP Demo App: app web WebMCP-enabled de prueba (formulario + contador).",
        "run": "python -m app.services.webmcp.demo_runner --port 8765",
        "url": "http://127.0.0.1:8765",
        "example_actions": [
            {"type": "input", "selector": "#name", "value": "Juan"},
            {"type": "input", "selector": "#email", "value": "juan@correo.com"},
            {"type": "submit", "selector": "form"},
            {"type": "click", "selector": "#increment"},
        ],
    }
