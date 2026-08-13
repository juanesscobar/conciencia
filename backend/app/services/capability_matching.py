"""Capability matching — encuentra el mejor agente para una tarea según capabilities.

Task requirements (lista de capabilities requeridas)
    ↓
Agent Registry (capabilities por agente + score + disponibilidad)
    ↓
Candidatos con % de match
    ↓
Mejor agente → dispatch
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.agent import Agent, AgentStatus


def normalize_cap(cap: str) -> str:
    return (cap or "").strip().lower().replace("-", "_").replace(" ", "_")


def match_agents(
    db: Session,
    *,
    required_capabilities: List[str],
    role: Optional[str] = None,
    runtime: Optional[str] = None,
    min_score: int = 0,
) -> List[dict]:
    """Devuelve agentes ordenados por % de capabilities cubiertas.

    Cada resultado: {agent, coverage, matched_caps, missing_caps, score}
    """
    required = [normalize_cap(c) for c in required_capabilities if c]
    if not required:
        return []

    query = db.query(Agent)
    if role:
        from app.models.agent import AgentRole
        try:
            query = query.filter(Agent.role == AgentRole(role))
        except ValueError:
            query = query.filter(Agent.role == role)
    if runtime:
        from app.models.agent import AgentRuntime
        try:
            query = query.filter(Agent.runtime == AgentRuntime(runtime))
        except ValueError:
            query = query.filter(Agent.runtime == runtime)

    agents = query.all()
    results = []
    for agent in agents:
        if agent.status == AgentStatus.ERROR:
            continue
        caps = {normalize_cap(c) for c in (agent.capabilities or [])}
        matched = [c for c in required if c in caps]
        missing = [c for c in required if c not in caps]
        coverage = round(len(matched) / len(required) * 100) if required else 0
        if coverage == 0:
            continue
        # score compuesto: cobertura 70% + disponibilidad 20% + base 10%
        avail = 100 if agent.status in (AgentStatus.IDLE, None) else 50
        score = round(coverage * 0.7 + avail * 0.2 + 10)
        if coverage < min_score:
            continue
        results.append({
            "agent_id": str(agent.id),
            "name": agent.name,
            "role": agent.role.value if hasattr(agent.role, "value") else str(agent.role),
            "runtime": agent.runtime.value if hasattr(agent.runtime, "value") else str(agent.runtime or "generic"),
            "provider": agent.provider.value if hasattr(agent.provider, "value") else str(agent.provider or "deepseek"),
            "model": agent.model,
            "coverage": coverage,
            "matched_caps": matched,
            "missing_caps": missing,
            "score": score,
            "status": agent.status.value if hasattr(agent.status, "value") else str(agent.status),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def best_agent(
    db: Session,
    *,
    required_capabilities: List[str],
    role: Optional[str] = None,
    runtime: Optional[str] = None,
) -> Optional[dict]:
    """Mejor agente para la tarea, o None si ninguno cubre >= 50%."""
    candidates = match_agents(
        db,
        required_capabilities=required_capabilities,
        role=role,
        runtime=runtime,
        min_score=50,
    )
    return candidates[0] if candidates else None
