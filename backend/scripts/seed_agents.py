"""Seed/upsert de los 8 agentes (dev, ops, qa, pm, rd, comms, fin, admin).
Idempotente: actualiza por role. Uso: python scripts/seed_agents.py"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.db_sync import sync_schema
from app.models.agent import (
    Agent,
    AgentRole,
    AgentType,
    AgentStatus,
    AutonomyLevel,
    AgentRuntime,
    AgentProvider,
)
from sqlalchemy import func

Base.metadata.create_all(bind=engine)
sync_schema(engine, Base)

# Arquitectura: runtime (cómo ejecuta) y provider (quién da el modelo) son EJES INDEPENDIENTES.
# Ej: un Lead Hunter puede correr en OpenClaw con DeepSeek, o un Developer en Claude Code con Anthropic.
AGENTS = [
    {
        "role": AgentRole.DEV, "name": "DevBot", "emoji": "👨‍💻",
        "personality": "Ingeniero de software senior: código limpio, code review y buenas prácticas.",
        "capabilities": ["code_review", "bug_fixing", "refactoring", "pull_requests"],
        "autonomy": AutonomyLevel.PREVIEW,
        "runtime": AgentRuntime.CLAUDE_CODE, "provider": AgentProvider.ANTHROPIC, "model": "claude-sonnet-4-20250514",
    },
    {
        "role": AgentRole.OPS, "name": "OpsBot", "emoji": "🚀",
        "personality": "Especialista en infraestructura, deploys y CI/CD.",
        "capabilities": ["deploys", "ci_cd", "monitoring", "docker"],
        "autonomy": AutonomyLevel.APPROVAL,
        "runtime": AgentRuntime.OPENCLAW, "provider": AgentProvider.DEEPSEEK, "model": "deepseek-chat",
    },
    {
        "role": AgentRole.QA, "name": "QATester", "emoji": "🧪",
        "personality": "Ingeniero de calidad: testing manual y automatizado, e2e.",
        "capabilities": ["unit_tests", "integration_tests", "e2e_tests", "regression"],
        "autonomy": AutonomyLevel.APPROVAL,
        "runtime": AgentRuntime.CODEX, "provider": AgentProvider.OPENAI, "model": "gpt-4o-mini",
    },
    {
        "role": AgentRole.PM, "name": "ProjectManager", "emoji": "📋",
        "personality": "PM organizado: backlog, roadmap, sprints y priorización.",
        "capabilities": ["task_tracking", "reporting", "sprint_planning", "backlog"],
        "autonomy": AutonomyLevel.FULL,
        "runtime": AgentRuntime.OPENCLAW, "provider": AgentProvider.DEEPSEEK, "model": "deepseek-chat",
    },
    {
        "role": AgentRole.RD, "name": "ResearchBot", "emoji": "📚",
        "personality": "Investigador: research, POCs, documentación y nuevas tecnologías.",
        "capabilities": ["research", "pocs", "documentation", "tech_watch"],
        "autonomy": AutonomyLevel.PREVIEW,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.OPENROUTER, "model": "deepseek/deepseek-chat",
    },
    {
        "role": AgentRole.COMMS, "name": "CommsBot", "emoji": "🎨",
        "personality": "Comunicación: contenido, newsletter, redes y presentaciones.",
        "capabilities": ["content", "newsletter", "social", "presentations"],
        "autonomy": AutonomyLevel.PREVIEW,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.DEEPSEEK, "model": "deepseek-chat",
    },
    {
        "role": AgentRole.FIN, "name": "FinanceBot", "emoji": "💰",
        "personality": "Finanzas: costos, presupuestos, ROI y facturación.",
        "capabilities": ["costs", "budgets", "roi", "invoicing"],
        "autonomy": AutonomyLevel.APPROVAL,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.OPENAI, "model": "gpt-4o-mini",
    },
    {
        "role": AgentRole.ADMIN, "name": "AdminBot", "emoji": "🎯",
        "personality": "Administración: scheduling, follow-ups y organización.",
        "capabilities": ["scheduling", "follow_ups", "organization", "reports"],
        "autonomy": AutonomyLevel.FULL,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.GOOGLE, "model": "gemini-2.0-flash",
    },
    # --- Fase 8: agentes LeadHunter (spec §17/§18/§27/§28) ---
    {
        "role": AgentRole.LEAD_RESEARCH, "name": "LeadResearchBot", "emoji": "🔍",
        "personality": "Investigador de empresas: convierte leads en perfiles accionables (señales, necesidad, confianza).",
        "capabilities": ["leads.read", "search.execute", "website_fetch", "research"],
        "autonomy": AutonomyLevel.PREVIEW,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.DEEPSEEK, "model": "deepseek-chat",
        "permissions": {"allow": ["leads.read", "search.execute", "website_fetch"], "deny": ["finance.write", "crm.write"]},
    },
    {
        "role": AgentRole.BUSINESS_CLASSIFICATION, "name": "ClassifyBot", "emoji": "🎯",
        "personality": "Clasificador de negocios: categoría canónica + scores (lead/oportunidad/calidad) + razones.",
        "capabilities": ["leads.read", "search.execute", "classification"],
        "autonomy": AutonomyLevel.PREVIEW,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.DEEPSEEK, "model": "deepseek-chat",
        "permissions": {"allow": ["leads.read", "search.execute"], "deny": ["finance.write"]},
    },
    {
        "role": AgentRole.CONTACT_DISCOVERY, "name": "ContactBot", "emoji": "📞",
        "personality": "Descubridor de contactos: emails/teléfonos/web con origen (observado vs inferido).",
        "capabilities": ["leads.read", "website_fetch", "contact_discovery"],
        "autonomy": AutonomyLevel.PREVIEW,
        "runtime": AgentRuntime.GENERIC, "provider": AgentProvider.DEEPSEEK, "model": "deepseek-chat",
        "permissions": {"allow": ["leads.read", "website_fetch"], "deny": ["finance.write"]},
    },
]

db = SessionLocal()
try:
    for a in AGENTS:
        agent = db.query(Agent).filter(Agent.role == a["role"].name).first()
        if agent:
            agent.name = a["name"]
            agent.emoji = a["emoji"]
            agent.personality = a["personality"]
            agent.capabilities = a["capabilities"]
            agent.autonomy_level = a["autonomy"]
            agent.runtime = a["runtime"]
            agent.provider = a["provider"]
            agent.model = a["model"]
            if a.get("permissions"):
                agent.config = {**(agent.config or {}), "permissions": a["permissions"]}
            print("update:", a["role"].value)
        else:
            db.add(Agent(
                name=a["name"],
                emoji=a["emoji"],
                role=a["role"],
                type=AgentType.SYSTEM,
                status=AgentStatus.IDLE,
                personality=a["personality"],
                capabilities=a["capabilities"],
                autonomy_level=a["autonomy"],
                runtime=a["runtime"],
                provider=a["provider"],
                model=a["model"],
                config={"permissions": a["permissions"]} if a.get("permissions") else None,
                health_status="online",
                availability="available",
                last_heartbeat=func.now(),
            ))
            print("create:", a["role"].value)
    db.commit()
    print(f"OK: {len(AGENTS)} agentes")
finally:
    db.close()
