"""Lead Hunter — scoring y enriquecimiento IA.

Fase 7: `compute_score` es ahora un wrapper de `ranking._blocks()` (única fuente
de verdad del scoring en `ranking.py`). El contrato histórico se preserva: mismos
valores, garantizado por `tests/test_discovery.py`.
"""

from typing import Optional

from sqlalchemy.orm import Session

from .models import Lead
from .ranking import _blocks, HIGH_VALUE_INDUSTRY, SOURCE_BONUS  # noqa: F401 (re-export compat)

__all__ = ["compute_score", "enrich_with_ai", "HIGH_VALUE_INDUSTRY", "SOURCE_BONUS"]


def compute_score(company: str = "", industry: str = "", source: str = "manual",
                  email: str = "", phone: str = "", notes: str = "",
                  metadata: Optional[dict] = None) -> int:
    """Score heurístico 0-100 basado en completitud y contexto.

    Contrato histórico preservado (mismos valores); delega en
    `ranking._blocks()` para que el scoring tenga una única fuente de verdad.
    """
    blocks = _blocks(
        company=company, industry=industry, source=source,
        email=email, phone=phone, notes=notes, metadata=metadata,
    )
    return max(0, min(100, int(sum(blocks.values()))))


def enrich_with_ai(lead: Lead) -> Optional[str]:
    """Usa DeepSeek (si está configurado) para enriquecer el lead."""
    from app.services.llm import is_configured, run_agent

    if not is_configured():
        return None

    task = (
        f"Analizá este lead de una software factory paraguaya (Conciencia):\n"
        f"- Empresa: {lead.company}\n"
        f"- Sector: {lead.industry or 'no especificado'}\n"
        f"- Segmento: {lead.segment or 'no especificado'}\n"
        f"- Fuente: {lead.source}\n"
        f"- Notas: {lead.notes or 'sin notas'}\n\n"
        f"Devolvé:\n"
        f"1. Score 0-100 de qué tan buen cliente potencial es para desarrollo de software, IA o ciberseguridad.\n"
        f"2. Sector/industria sugerida (cooperativa, salud, distribuidora, comercio, industria, otro).\n"
        f"3. Segmento sugerido (pyme, mediana, corporativo).\n"
        f"4. 3 preguntas clave para la primera llamada.\n"
        f"5. Próximo paso recomendado.\n"
        f"Formato: texto corto con secciones numeradas."
    )
    result = run_agent("LeadHunter", "Sos un experto en calificación de leads B2B para una software factory.", task)
    return result.get("output")
