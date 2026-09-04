"""WebMCP — tool/adapter de Conciencia para apps web WebMCP-enabled (Fase K)."""

from app.services.webmcp.client import (  # noqa: F401
    WebMCPError, get_context, act, snapshot, run_script,
)
from app.services.webmcp.demo_app import create_demo_app, render_snapshot  # noqa: F401
from app.services.webmcp.evidence import promote_step_evidence  # noqa: F401
