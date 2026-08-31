"""AskService — `conciencia ask` (master prompt §9/§E).

Pipeline: texto natural → intent classification (reglas + fallback LLM opcional)
→ agentes sugeridos (capability_matching) → runtime → workflow → costo estimado
→ propuesta estructurada. La creación de la misión requiere confirmación humana.

Sin API keys funciona 100% por reglas (cero costo). Con LLM configurado, el
intent classifier puede refinar el tipo de misión.
"""

import re
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.mission import Mission, MISSION_TYPES
from app.services import mission_service
from app.services.capability_matching import match_agents

# ---------------------------------------------------------------------------
# 1. Intent classification por reglas (funciona sin LLM)
# ---------------------------------------------------------------------------

# keyword → tipo de misión. Orden importa: más específico primero.
_INTENT_KEYWORDS: List[tuple] = [
    ("technical-audit", ["audit", "auditar", "deuda técnica", "technical debt", "revisar arquitectura", "assessment"]),
    ("code-review", ["code review", "revisar pr", "review pr", "revisión de código", "revisar código", "pull request"]),
    ("debugging", ["debug", "bug", "error", "falla", "crash", "no funciona", "fix"]),
    ("testing", ["test", "testing", "prueba", "qa", "coverage", "e2e", "unit test"]),
    ("deployment", ["deploy", "desplegar", "producción", "production", "release", "lanzar"]),
    ("devops", ["devops", "ci/cd", "ci cd", "infra", "docker", "kubernetes", "servidor", "pipeline"]),
    ("architecture", ["arquitectura", "architecture", "diseño de sistema", "system design", "diagrama"]),
    ("data-analysis", ["analizar datos", "data analysis", "dataset", "métrica", "analítica", "sql"]),
    ("competitive-research", ["competencia", "competitor", "análisis de mercado", "market research", "benchmark"]),
    ("product-research", ["producto", "product research", "ux", "usuario", "feature research"]),
    ("technical-discovery", ["descubrimiento", "discovery", "explorar", "prospecto", "oportunidad"]),
    ("lead-research", ["lead", "prospect", "cliente potencial", "empresas de", "companies in", "cazar"]),
    ("technical-proposal", ["propuesta", "proposal", "cotización", "quote", "oferta técnica"]),
    ("integration", ["integrar", "integration", "api externa", "webhook", "conectar"]),
    ("automation", ["automatizar", "automation", "script", "bot"]),
    ("agent-design", ["agente", "agent", "harness", "soul", "prompt engineering"]),
    ("workflow-design", ["workflow", "flujo de trabajo", "orquestar", "orchestration"]),
    ("research", ["investigar", "research", "analizar", "estudio", "comparar", "evaluar"]),
    ("software-development", ["implementar", "desarrollar", "feature", "módulo", "componente", "refactor", "crear", "build"]),
]

_DEFAULT_TYPE = "research"


def classify_intent(text: str) -> str:
    """Clasifica el intent por keywords. Fallback: research."""
    t = (text or "").lower()
    for mtype, keywords in _INTENT_KEYWORDS:
        for kw in keywords:
            if kw in t:
                return mtype
    return _DEFAULT_TYPE


# capabilities requeridas por tipo de misión (para sugerir agentes)
_TYPE_CAPABILITIES: Dict[str, List[str]] = {
    "research": ["research"],
    "software-development": ["code", "refactoring"],
    "code-review": ["code_review"],
    "debugging": ["bug_fixing"],
    "architecture": ["research", "documentation"],
    "testing": ["testing"],
    "devops": ["deploys", "ci_cd"],
    "deployment": ["deploys", "monitoring"],
    "technical-audit": ["research", "code_review"],
    "agent-design": ["research", "documentation"],
    "workflow-design": ["research", "documentation"],
    "automation": ["code", "refactoring"],
    "integration": ["code", "research"],
    "data-analysis": ["research"],
    "product-research": ["research"],
    "competitive-research": ["research"],
    "technical-discovery": ["research", "leads.read"],
    "lead-research": ["leads.read", "search.execute", "website_fetch"],
    "technical-proposal": ["research", "reporting"],
}

# runtime sugerido por tipo
_TYPE_RUNTIME: Dict[str, str] = {
    "software-development": "claude_code",
    "code-review": "codex",
    "debugging": "claude_code",
    "testing": "codex",
    "devops": "openclaw",
    "deployment": "openclaw",
    "automation": "openclaw",
    "integration": "openclaw",
}


# ---------------------------------------------------------------------------
# 2. Costo estimado (precios por millón de tokens, input/output)
# ---------------------------------------------------------------------------

_MODEL_PRICES: Dict[str, tuple] = {
    "deepseek-chat": (0.27, 1.10),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "gemini-2.0-flash": (0.075, 0.30),
    "default": (0.30, 1.20),
}

# tokens estimados por step según tipo (input/output)
_STEP_TOKENS: Dict[str, tuple] = {
    "research": (800, 300),
    "synthesis": (600, 400),
    "plan": (500, 200),
    "implement": (2500, 1200),
    "test": (1200, 400),
    "review": (1500, 500),
    "report": (500, 400),
    "audit": (2000, 800),
    "discovery": (300, 100),
    "enrich": (400, 150),
    "classify": (400, 150),
    "approval": (0, 0),
    "default": (800, 300),
}


def estimate_cost(workflow_steps: List[dict], model: str = "default") -> dict:
    """Estima costo y tokens de un workflow (sin llamadas reales)."""
    price_in, price_out = _MODEL_PRICES.get(model, _MODEL_PRICES["default"])
    total_in = total_out = 0
    for step in workflow_steps or []:
        if step.get("approval"):
            continue
        name = step.get("name", "default")
        t_in, t_out = _STEP_TOKENS.get(name, _STEP_TOKENS["default"])
        total_in += t_in
        total_out += t_out
    cost_in = total_in / 1_000_000 * price_in
    cost_out = total_out / 1_000_000 * price_out
    total = round(cost_in + cost_out, 4)
    return {
        "tokens_in": total_in,
        "tokens_out": total_out,
        "tokens_total": total_in + total_out,
        "cost_usd": total,
        "model": model,
        "note": "estimación estática (sin llamadas reales)",
    }


# ---------------------------------------------------------------------------
# 3. Propuesta
# ---------------------------------------------------------------------------

def build_proposal(db: Session, text: str) -> dict:
    """Texto natural → propuesta de misión completa (sin crear nada)."""
    mtype = classify_intent(text)
    caps = _TYPE_CAPABILITIES.get(mtype, ["research"])

    agents = match_agents(db, required_capabilities=caps)
    top_agents = agents[:3] if agents else []

    runtime = _TYPE_RUNTIME.get(mtype, "generic")
    workflow_steps = mission_service.DEFAULT_WORKFLOWS.get(mtype, mission_service.DEFAULT_WORKFLOWS["research"])

    model = "default"
    if top_agents:
        model = top_agents[0].get("model") or "default"
    cost = estimate_cost(workflow_steps, model=model)

    return {
        "text": text,
        "mission_type": mtype,
        "name": _proposal_name(text, mtype),
        "objective": text,
        "runtime": runtime,
        "agents": top_agents,
        "workflow": [
            {"name": s.get("name"), "approval": bool(s.get("approval")), "capabilities": s.get("capabilities", [])}
            for s in workflow_steps
        ],
        "cost_estimate": cost,
        "success_criteria": _default_criteria(mtype),
    }


def _proposal_name(text: str, mtype: str) -> str:
    """Nombre corto de la misión: primeros N chars del texto."""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) > 60:
        clean = clean[:57] + "..."
    return clean or f"Mission {mtype}"


def _default_criteria(mtype: str) -> List[str]:
    base = ["resultado documentado", "evidencia adjunta"]
    extra = {
        "software-development": ["código implementado", "tests pasando"],
        "code-review": ["hallazgos listados por severidad"],
        "testing": ["tests escritos y verdes"],
        "deployment": ["deploy verificado"],
        "technical-audit": ["riesgos identificados con evidencia"],
        "lead-research": ["leads calificados con score"],
        "technical-proposal": ["propuesta entregada"],
    }
    return extra.get(mtype, []) + base


def create_from_proposal(db: Session, proposal: dict) -> Mission:
    """Crea la misión a partir de una propuesta confirmada."""
    return mission_service.create_mission(
        db,
        name=proposal["name"],
        objective=proposal["objective"],
        type=proposal["mission_type"],
        runtime=proposal["runtime"],
        agent_ids=[a["agent_id"] for a in proposal["agents"]],
        success_criteria=proposal["success_criteria"],
    )
