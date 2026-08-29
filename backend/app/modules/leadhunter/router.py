"""Lead Hunter API router — capa fina HTTP (Fase 7: slimming, spec §42/§48).

La lógica vive en los services (`search.py`, `discovery.py`, `ranking.py`,
`embeddings.py`, ...) y los handlers en `endpoints/`. Este archivo solo
agrega los sub-routers (orden importa: los paths estáticos van ANTES de
`/{lead_id}` para que FastAPI matchee bien).
"""

from fastapi import APIRouter, Depends

from app.services.auth import get_current_user

from .endpoints import (
    search_endpoints,
    hunt_endpoints,
    lists_endpoints,
    proposals_endpoints,
    leads_endpoints,
)
from .helpers import _norm, _slug, _to_response, _get_lead_or_404, _recompute_score  # noqa: F401 (re-export compat)

router = APIRouter(prefix="/api/v1/leads", tags=["leadhunter"], dependencies=[Depends(get_current_user)])

# Orden de inclusión crítico: rutas estáticas antes de las dinámicas /{lead_id}.
router.include_router(search_endpoints.router)
router.include_router(hunt_endpoints.router)
router.include_router(lists_endpoints.router)
router.include_router(proposals_endpoints.router)
router.include_router(leads_endpoints.router)

# Webhook público (sin auth) — lo usa la landing de Conciencia.
intake_router = APIRouter(prefix="/api/v1/leads", tags=["leadhunter-intake"])
intake_router.include_router(leads_endpoints.intake_router)
