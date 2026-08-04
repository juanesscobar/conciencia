"""Lead Hunter — lógica de scoring y búsqueda."""

from typing import Optional

from sqlalchemy.orm import Session

from .models import Lead, LeadStatus

# Palabras que suman puntos según el sector objetivo de Conciencia
HIGH_VALUE_INDUSTRY = {
    "cooperativa": 25,
    "cooperativas": 25,
    "hospital": 20,
    "clinica": 20,
    "clínica": 20,
    "salud": 15,
    "distribuidora": 20,
    "industria": 15,
    "comercio": 10,
    "logistica": 15,
    "logística": 15,
    "farmacia": 15,
    "agro": 10,
    "financiero": 15,
}

SOURCE_BONUS = {
    "conciencia": 15,   # viene caliente del diagnóstico
    "referral": 20,     # recomendación = alta confianza
    "web": 10,
    "linkedin": 10,
}


def compute_score(company: str = "", industry: str = "", source: str = "manual",
                  email: str = "", phone: str = "", notes: str = "",
                  metadata: Optional[dict] = None) -> int:
    """Score heurístico 0-100 basado en completitud y contexto."""
    score = 0

    # Completitud de datos
    if email:
        score += 20
    if phone:
        score += 15
    if company:
        score += 10

    # Sector objetivo (Conciencia: cooperativas, hospitales, distribuidoras)
    haystack = f"{company} {industry} {notes or ''}".lower()
    for keyword, points in HIGH_VALUE_INDUSTRY.items():
        if keyword in haystack:
            score += points
            break  # un solo sector cuenta

    # Fuente
    score += SOURCE_BONUS.get(source, 0)

    # El diagnóstico de Conciencia con respuestas completas = lead caliente
    if metadata and isinstance(metadata, dict):
        n_answers = sum(1 for v in metadata.values() if v)
        if n_answers >= 3:
            score += 10

    return max(0, min(100, score))


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
