"""Fuentes de prospección de leads B2B.

Cada fuente descubre empresas/negocios potenciales y las devuelve como
dicts normalizados:
    {
        "company": str,          # obligatorio
        "industry": str,         # cooperativa, salud, distribuidora, comercio, farmacia, financiero, industria
        "phone": str | None,
        "email": str | None,
        "website": str | None,
        "address": str | None,
        "segment": str | None,   # pyme | mediana | corporativo
        "meta": dict,            # datos crudos de la fuente
    }
"""
from .base import BaseLeadSource, get_source, get_all_sources, run_all_sources
from .overpass import OverpassSource

__all__ = [
    "BaseLeadSource",
    "get_source",
    "get_all_sources",
    "run_all_sources",
    "OverpassSource",
]
