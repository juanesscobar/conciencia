"""Agentes LeadHunter (Fase 8, spec §17/§18/§27/§28).

Agentes mínimos que usan el AgentRuntime existente (adapters + SOUL.md):
- lead_research: perfil accionable de la empresa
- business_classification: categoría + scores + razones
- contact_discovery: contactos con origen (observado vs inferido)

Permisos (spec §28): cada agente declara allow/deny en `config.permissions`;
el endpoint valida la acción pedida contra esos permisos. Toda ejecución queda
en AgentExecution + audit (spec §29).
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .models import Lead

# Acciones expuestas → rol de agente
ACTION_TO_ROLE = {
    "research": "lead_research",
    "classify": "business_classification",
    "contacts": "contact_discovery",
}

# Permisos requeridos por acción (spec §28)
ACTION_PERMISSIONS = {
    "research": ["leads.read", "search.execute", "website_fetch"],
    "classify": ["leads.read", "search.execute"],
    "contacts": ["leads.read", "website_fetch"],
}


def get_agent_by_role(db: Session, role: str):
    """Busca un agente por role (devuelve None si no existe)."""
    from app.models.agent import Agent

    return db.query(Agent).filter(Agent.role == role).first()


def check_permissions(agent, action: str) -> Optional[str]:
    """Valida que el agente tenga permisos para la acción (spec §28).

    Devuelve un mensaje de error si NO puede, o None si puede.
    """
    perms = ((agent.config or {}).get("permissions") or {}) if agent else {}
    allow = set(perms.get("allow") or [])
    deny = set(perms.get("deny") or [])
    required = ACTION_PERMISSIONS.get(action, [])
    for req in required:
        if req in deny:
            return f"El agente {agent.name} tiene DENY sobre '{req}' — no puede ejecutar '{action}'"
        if allow and req not in allow:
            return f"El agente {agent.name} no tiene ALLOW sobre '{req}' — no puede ejecutar '{action}'"
    return None


def build_lead_context(lead: Lead, extra: Optional[dict] = None) -> str:
    """Contexto estructurado del lead para el agente."""
    meta = lead.meta if isinstance(lead.meta, dict) else {}
    lines = [
        f"Empresa: {lead.company}",
        f"Contacto: {lead.contact_name or 'no especificado'}",
        f"Email: {lead.email or 'no'}",
        f"Teléfono: {lead.phone or 'no'}",
        f"Website: {lead.website or 'no'}",
        f"Sector: {lead.industry or 'no especificado'}",
        f"Segmento: {lead.segment or 'no especificado'}",
        f"Región: {lead.region or 'no especificado'}",
        f"Fuente: {lead.source}",
        f"Notas: {lead.notes or 'sin notas'}",
        f"Metadata: {str(meta)[:600]}",
    ]
    if extra:
        lines.append(f"Datos extra del análisis: {str(extra)[:800]}")
    return "\n".join(lines)


def run_lead_agent(db: Session, agent, lead: Lead, action: str = "classify") -> Dict[str, Any]:
    """Ejecuta el agente sobre el lead y devuelve el resultado estructurado.

    Flujo: permisos → contexto → adapter (generic) → AgentExecution + audit.
    Para `contacts`, primero corre la herramienta `website_fetch` real
    (enrich_from_website) y le pasa lo encontrado como contexto.
    """
    from datetime import datetime

    from app.adapters.registry import get_adapter
    from app.adapters.base import AgentIdentity
    from app.services.agent_soul import load_agent_persona
    from app.models.agent import AgentStatus
    from app.models.execution import AgentExecution, ExecutionStatus
    from app.models.audit import audit

    # 1. Permisos (spec §28)
    err = check_permissions(agent, action)
    if err:
        raise PermissionError(err)

    # 2. Herramienta real para contact_discovery (mapea a enrich.py)
    extra: Optional[dict] = None
    if action == "contacts" and lead.website:
        try:
            from .enrich import enrich_from_website
            result = enrich_from_website(lead)
            if result.get("changed"):
                db.commit()
            extra = {"website_scan": {k: v for k, v in result.items() if k != "fetched"}}
        except Exception as e:  # noqa: BLE001
            extra = {"website_scan_error": str(e)[:200]}

    # 3. Persona (SOUL.md) + contexto
    role = agent.role.value if hasattr(agent.role, "value") else str(agent.role)
    system_prompt = load_agent_persona(role) or agent.system_prompt or agent.personality or ""
    context = build_lead_context(lead, extra=extra)

    task = (
        f"Analizá el siguiente lead de LeadHunter (acción: {action}).\n"
        f"Seguí el formato de output de tu SOUL.md exactamente.\n"
        f"Lead ID: {lead.id}"
    )

    runtime_name = getattr(agent, "runtime", None)
    runtime_name = runtime_name.value if hasattr(runtime_name, "value") else (runtime_name or "generic")
    provider_name = getattr(agent, "provider", None)
    provider_name = provider_name.value if hasattr(provider_name, "value") else (provider_name or "deepseek")
    model = getattr(agent, "model", None) or None

    adapter = get_adapter(runtime_name)
    if not adapter:
        raise RuntimeError(f"Runtime '{runtime_name}' sin adapter registrado")

    identity = AgentIdentity(
        agent_id=str(agent.id),
        name=agent.name,
        role=role,
        runtime=runtime_name,
        provider=provider_name,
        model=model,
        system_prompt=system_prompt,
        capabilities=agent.capabilities or [],
        config=agent.config or {},
    )

    # 4. Ejecución registrada (spec §29)
    execution = AgentExecution(
        agent_id=agent.id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    audit(db, event_type="agent_task_started", actor=agent.name, actor_type="agent",
          metadata={"action": action, "lead_id": lead.id, "runtime": runtime_name, "model": model})

    agent.status = AgentStatus.WORKING
    db.commit()

    try:
        result = adapter.dispatch_task(identity, task, context=context)
        status = result.status if result.ok else "failed"
        output = result.output
        error = result.error

        execution.status = ExecutionStatus.COMPLETED if result.ok else ExecutionStatus.FAILED
        execution.output = (output or "")[:10000]
        execution.error_message = (error or "")[:2000]
        execution.completed_at = datetime.utcnow()
        db.commit()

        audit(db, event_type="agent_task_completed" if result.ok else "agent_task_failed",
              actor=agent.name, actor_type="agent",
              metadata={"action": action, "lead_id": lead.id, "status": status,
                        "usage": result.usage, "duration_ms": result.duration_ms})

        return {
            "ok": result.ok,
            "status": status,
            "output": output,
            "error": error,
            "model": result.model,
            "provider": result.provider or provider_name,
            "runtime": runtime_name,
            "usage": result.usage,
            "duration_ms": result.duration_ms,
            "simulated": result.simulated,
            "execution_id": str(execution.id),
            "website_scan": extra,
        }
    finally:
        from app.models.agent import AgentStatus as _AS
        agent.status = _AS.IDLE
        db.commit()


def save_agent_output(lead: Lead, action: str, result: Dict[str, Any]) -> None:
    """Guarda el output del agente en lead.meta (provenance + análisis)."""
    meta = dict(lead.meta or {})
    agent_meta = dict(meta.get("agents") or {})
    agent_meta[action] = {
        "output": (result.get("output") or "")[:4000],
        "status": result.get("status"),
        "model": result.get("model"),
        "provider": result.get("provider"),
        "simulated": result.get("simulated", False),
        "ran_at": datetime.utcnow().isoformat(),
        "website_scan": result.get("website_scan"),
    }
    meta["agents"] = agent_meta
    lead.meta = meta
