"""AskService — `conciencia ask` (master prompt §9/§E).

Pipeline: texto natural → intent classification (reglas + fallback LLM opcional)
→ agentes sugeridos (capability_matching) → runtime → workflow → costo estimado
→ propuesta estructurada. La creación de la misión requiere confirmación humana.

Sin API keys funciona 100% por reglas (cero costo). Con LLM configurado, el
intent classifier puede refinar el tipo de misión.
"""

import re

from sqlalchemy.orm import Session

from app.models.mission import Mission
from app.services import mission_service
from app.services.capability_matching import match_agents
from app.services.workflow_registry import resolve_workflow

# ---------------------------------------------------------------------------
# 1. Intent classification por reglas (funciona sin LLM)
# ---------------------------------------------------------------------------

# keyword → tipo de misión. Orden importa: más específico primero.
_INTENT_KEYWORDS: list[tuple] = [
    ("technical-proposal", ["devpost", "hackathon submission", "submission", "pitch deck", "demo para jurado", "presentacion al jurado", "entrega del proyecto"]),
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
    return classify_intent_details(text)["type"]


def classify_intent_details(text: str) -> dict:
    """Return the selected intent with confidence and a visible alternative."""
    t = (text or "").lower()
    matches = []
    for mtype, keywords in _INTENT_KEYWORDS:
        matched = [kw for kw in keywords if kw in t]
        if matched and mtype not in [item[0] for item in matches]:
            matches.append((mtype, matched))
    if not matches:
        return {
            "type": _DEFAULT_TYPE,
            "confidence": 0.4,
            "alternative": None,
            "reason": "no specific intent signal; safe research default",
        }
    selected, keywords = matches[0]
    distinctive = {"devpost", "hackathon submission", "pitch deck", "deploy", "desplegar"}
    confidence = 0.94 if any(keyword in distinctive for keyword in keywords) else 0.82
    return {
        "type": selected,
        "confidence": confidence,
        "alternative": matches[1][0] if len(matches) > 1 else None,
        "reason": f"matched: {', '.join(keywords[:3])}",
    }


# capabilities requeridas por tipo de misión (para sugerir agentes)
_TYPE_CAPABILITIES: dict[str, list[str]] = {
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
_TYPE_RUNTIME: dict[str, str] = {
    "software-development": "claude_code",
    "code-review": "codex",
    "debugging": "claude_code",
    "testing": "codex",
    "devops": "openclaw",
    "deployment": "openclaw",
    "automation": "openclaw",
    "integration": "openclaw",
}


def runtime_readiness(
    db: Session,
    preferred: str,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """Compatibility wrapper over canonical capability readiness."""
    from app.services.capability_readiness import runtime_readiness as resolve_runtime

    status = resolve_runtime(db, preferred, provider=provider, model=model)
    return {**status, "preferred": preferred, "selected": preferred}


# ---------------------------------------------------------------------------
# 2. Costo estimado (precios por millón de tokens, input/output)
# ---------------------------------------------------------------------------

_MODEL_PRICES: dict[str, tuple] = {
    "deepseek-chat": (0.27, 1.10),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "gemini-2.0-flash": (0.075, 0.30),
    "default": (0.30, 1.20),
}

# tokens estimados por step según tipo (input/output)
_STEP_TOKENS: dict[str, tuple] = {
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


def estimate_cost(workflow_steps: list[dict], model: str = "default") -> dict:
    """Estima costo y tokens de un workflow (sin llamadas reales).

    Recorre también steps anidados de bloques paralelos (Fase F).
    """
    price_in, price_out = _MODEL_PRICES.get(model, _MODEL_PRICES["default"])
    total_in = total_out = 0

    def _count(step: dict) -> None:
        nonlocal total_in, total_out
        if step.get("approval"):
            return
        if step.get("parallel") and step.get("steps"):
            for child in step["steps"]:
                _count(child)
            return
        name = step.get("name", "default")
        t_in, t_out = _STEP_TOKENS.get(name, _STEP_TOKENS["default"])
        total_in += t_in
        total_out += t_out

    for step in workflow_steps or []:
        _count(step)
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
    intent = classify_intent_details(text)
    mtype = intent["type"]
    caps = _TYPE_CAPABILITIES.get(mtype, ["research"])

    agents = match_agents(db, required_capabilities=caps)
    top_agents = agents[:3] if agents else []

    # Fase F: sugiero teams que cubran las capabilities (0 si no hay teams)
    from app.services import team_service

    teams = team_service.match_teams(db, required_capabilities=caps)[:3]
    suggested_team = teams[0] if teams else None

    preferred_runtime = _TYPE_RUNTIME.get(mtype, "generic")
    if suggested_team:
        preferred_runtime = suggested_team.get("default_runtime") or preferred_runtime
    provider = top_agents[0].get("provider") if top_agents else None
    model = top_agents[0].get("model") if top_agents else None
    runtime_status = runtime_readiness(
        db,
        preferred_runtime,
        provider=provider if preferred_runtime == "generic" else None,
        model=model if preferred_runtime == "generic" else None,
    )
    runtime = preferred_runtime
    workflow_resolution = resolve_workflow(mtype)
    if not workflow_resolution.resolvable:
        raise ValueError(f"No hay workflow resoluble para tipo '{mtype}': {workflow_resolution.reason}")
    workflow_steps = list(workflow_resolution.steps)

    model = model or "default"
    cost = estimate_cost(workflow_steps, model=model)

    return {
        "text": text,
        "mission_type": mtype,
        "intent": intent,
        "name": _proposal_name(text, mtype),
        "objective": text,
        "runtime": runtime,
        "agents": top_agents,
        "team": suggested_team,
        "workflow": [
            {"name": s.get("name"), "approval": bool(s.get("approval")), "capabilities": s.get("capabilities", []), "parallel": bool(s.get("parallel"))}
            for s in workflow_steps
        ],
        "cost_estimate": cost,
        "success_criteria": _default_criteria(mtype),
        "readiness": {
            "workflow": {
                "resolvable": workflow_resolution.resolvable,
                "source": workflow_resolution.source,
                "reason": workflow_resolution.reason,
            },
            "runtime": runtime_status,
        },
    }


def _proposal_name(text: str, mtype: str) -> str:
    """Nombre corto de la misión: primeros N chars del texto."""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) > 60:
        clean = clean[:57] + "..."
    return clean or f"Mission {mtype}"


def _default_criteria(mtype: str) -> list[str]:
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
    resolution = resolve_workflow(proposal.get("mission_type", ""))
    if not resolution.resolvable:
        raise ValueError(f"La propuesta no es planificable: {resolution.reason}")
    team_id = (proposal.get("team") or {}).get("team_id")
    # Si hay team seleccionado, los agentes explícitos quedan de referencia:
    # los miembros del team pueblan agent_ids en create_mission.
    agents = [a["agent_id"] for a in proposal["agents"]] if not team_id else None
    return mission_service.create_mission(
        db,
        name=proposal["name"],
        objective=proposal["objective"],
        type=proposal["mission_type"],
        runtime=proposal["runtime"],
        agent_ids=agents,
        team_id=team_id,
        success_criteria=proposal["success_criteria"],
    )
