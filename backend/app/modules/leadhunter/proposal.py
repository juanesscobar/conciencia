"""Sales squad — generación modular de propuestas comerciales.

Corre 4 agentes en secuencia (cada uno con su SOUL.md como personalidad):

  pm    → análisis del negocio del lead (dolores, madurez digital, oportunidades)
  rd    → compatibilidad con el catálogo de servicios de Conciencia
  fin   → inversión estimada en USD según segmento y fases
  comms → redacción final de la propuesta (markdown, lista para enviar)

Cada paso recibe como contexto la salida de los anteriores (encadenado), así el
resultado es coherente y modular: podés agregar/quitar agentes sin tocar el resto.
"""

from typing import Optional

from .catalog import catalog_context
from .models import Lead

SQUAD_STEPS = [
    {
        "role": "pm",
        "name": "PM",
        "label": "Análisis del negocio",
        "mission": (
            "Analizá el negocio de este lead como consultor senior de una software factory.\n"
            "Detectá: sector y modelo de negocio, dolores más probables, madurez digital, "
            "y 2-3 oportunidades concretas donde el software genera valor.\n"
            "Devolvé SOLO un bloque markdown titulado '## Análisis del negocio' con bullets "
            "cortos y accionables. Sin relleno, sin saludos."
        ),
    },
    {
        "role": "rd",
        "name": "R&D",
        "label": "Compatibilidad con servicios",
        "mission": (
            "Con el análisis de negocio previo, mapeá qué servicios del catálogo de Conciencia "
            "encajan mejor con este lead. Usá SOLO los servicios del catálogo provisto.\n"
            "Devolvé SOLO un bloque markdown titulado '## Solución propuesta' con bullets: "
            "servicio (con emoji), por qué encaja, y resultado esperado para el negocio. "
            "Priorizá máximo 3 servicios: lo que le venderías primero."
        ),
    },
    {
        "role": "fin",
        "name": "Fin",
        "label": "Inversión estimada",
        "mission": (
            "Estimá la inversión en USD para los servicios recomendados usando los rangos del "
            "catálogo (segmento del lead) y el análisis previo.\n"
            "Devolvé SOLO un bloque markdown titulado '## Inversión estimada' con: rango por "
            "servicio, total estimado del proyecto, y 2 opciones de arranque "
            "(ej: 'Fase 1 — MVP' y 'Fase 2 — completo') con su rango cada una."
        ),
    },
    {
        "role": "comms",
        "name": "Comms",
        "label": "Propuesta final",
        "mission": (
            "Redactá la propuesta comercial final en español, markdown, tono profesional pero "
            "cercano. Usá los insumos de PM, R&D y Fin (secciones previas).\n"
            "Estructura EXACTA:\n"
            "1. Resumen ejecutivo (2-3 líneas)\n"
            "2. Problemas que resolvemos\n"
            "3. Solución propuesta y alcance inicial\n"
            "4. Inversión estimada (USD)\n"
            "5. Próximos pasos (reunión → diagnóstico → pilotaje)\n"
            "6. Cierre con llamado a la acción\n"
            "Mencioná 'Conciencia' como la software factory que propone. Devolvé SOLO la "
            "propuesta final completa, sin comentarios ni advertencias."
        ),
    },
]


def build_lead_context(lead: Lead) -> str:
    """Contexto base del lead + catálogo, primer input del squad."""
    meta = lead.meta if isinstance(lead.meta, dict) else {}
    diag = ""
    if meta:
        diag = "\n- Respuestas de diagnóstico: " + "; ".join(
            f"{k}: {v}" for k, v in meta.items() if v
        )
    return (
        "## DATOS DEL LEAD\n"
        f"- Empresa: {lead.company}\n"
        f"- Contacto: {lead.contact_name or 'no disponible'}\n"
        f"- Sector: {lead.industry or 'no especificado'}\n"
        f"- Segmento: {lead.segment or 'no especificado'}\n"
        f"- Región: {lead.region or 'no especificada'}\n"
        f"- Website: {lead.website or 'sin web'}\n"
        f"- Notas: {lead.notes or 'sin notas'}\n"
        f"- Fuente: {lead.source}"
        f"{diag}\n\n"
        f"{catalog_context(lead.segment)}"
    )


def _step_system_prompt(step: dict) -> str:
    from app.services.agent_soul import load_agent_persona

    persona = load_agent_persona(step["role"])
    mission = step["mission"]
    return f"{persona}\n\n## MISIÓN ESPECIAL DE ESTA TAREA\n{mission}" if persona else mission


def generate_sales_proposal(lead: Lead, mode: str = "squad") -> dict:
    """Corre el squad y devuelve la propuesta armada.

    Returns:
        {"ok": True, "content", "sections", "agents", "model", "provider", "simulated"}
        {"ok": False, "reason": "llm_not_configured" | "no_output", "detail": ...}
    """
    from app.services.llm import is_configured, run_agent

    if not is_configured():
        return {
            "ok": False,
            "reason": "llm_not_configured",
            "detail": "El proveedor de IA no está configurado. Agregá tu API key en Configuración → Integraciones.",
        }

    steps = SQUAD_STEPS if mode == "squad" else SQUAD_STEPS[-1:]  # 'quick' → solo comms
    sections: dict = {}
    agents: list = []
    last_context = build_lead_context(lead)

    for step in steps:
        result = run_agent(step["name"], _step_system_prompt(step), last_context)
        output = result.get("output")
        if result.get("error") or not output:
            agents.append({
                "role": step["role"], "name": step["name"], "label": step["label"],
                "ok": False, "error": result.get("error") or "sin respuesta del LLM",
            })
            continue
        agents.append({
            "role": step["role"], "name": step["name"], "label": step["label"],
            "ok": True, "model": result.get("model"), "provider": result.get("provider"),
        })
        sections[step["role"]] = output
        last_context += f"\n\n## SALIDA DEL AGENTE {step['name']} ({step['label']})\n{output}"

    content = sections.get("comms")
    if not content and sections:
        # Fallback: si comms falló, armamos la propuesta con las secciones disponibles
        content = "\n\n".join(
            f"# {next(s['label'] for s in steps if s['role'] == role)}\n{out}"
            for role, out in sections.items()
        )

    if not content:
        return {
            "ok": False,
            "reason": "no_output",
            "detail": "Ningún agente del squad respondió. Revisá la conexión con el proveedor de IA.",
            "agents": agents,
        }

    models = [a.get("model") for a in agents if a.get("ok") and a.get("model")]
    providers = [a.get("provider") for a in agents if a.get("ok") and a.get("provider")]
    return {
        "ok": True,
        "content": content,
        "sections": sections,
        "agents": agents,
        "model": models[-1] if models else None,
        "provider": providers[-1] if providers else None,
        "simulated": False,
    }
