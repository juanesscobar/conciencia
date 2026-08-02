import sys
sys.path.append('/app')
from app.database import SessionLocal
from app.models.agent import Agent, AgentRole, AgentType, AgentStatus, AutonomyLevel
from app.models.activity import Activity
from datetime import datetime

agents_data = [
    {
        "name": "Dev", "emoji": "👨‍💻", "role": AgentRole.DEV,
        "capabilities": ["coding", "code_review", "testing", "refactoring", "debugging"],
        "autonomy": AutonomyLevel.FULL,
        "personality": "Code artisan — pragmático, test-first, meticuloso",
    },
    {
        "name": "Ops", "emoji": "🚀", "role": AgentRole.OPS,
        "capabilities": ["infra", "deploys", "ci_cd", "docker", "monitoring"],
        "autonomy": AutonomyLevel.APPROVAL,
        "personality": "SRE — despliega con seguridad, observabilidad primero",
    },
    {
        "name": "QA", "emoji": "🧪", "role": AgentRole.QA,
        "capabilities": ["testing", "e2e", "regression", "quality_gates"],
        "autonomy": AutonomyLevel.FULL,
        "personality": "Quality gatekeeper — nada pasa sin verificación",
    },
    {
        "name": "PM", "emoji": "📊", "role": AgentRole.PM,
        "capabilities": ["backlog", "roadmap", "prioritization", "sprints"],
        "autonomy": AutonomyLevel.PREVIEW,
        "personality": "Product strategist — convierte visión en tareas accionables",
    },
    {
        "name": "R&D", "emoji": "📚", "role": AgentRole.RD,
        "capabilities": ["research", "pocs", "documentation", "trends"],
        "autonomy": AutonomyLevel.PREVIEW,
        "personality": "Researcher — explora, prototipa y documenta",
    },
    {
        "name": "Comms", "emoji": "🎨", "role": AgentRole.COMMS,
        "capabilities": ["content", "reports", "updates", "marketing"],
        "autonomy": AutonomyLevel.PREVIEW,
        "personality": "Storyteller — comunica el progreso con claridad",
    },
    {
        "name": "Fin", "emoji": "💰", "role": AgentRole.FIN,
        "capabilities": ["costs", "budgets", "roi", "invoicing"],
        "autonomy": AutonomyLevel.PREVIEW,
        "personality": "CFO digital — cada peso tiene que rendir",
    },
    {
        "name": "Admin", "emoji": "🎯", "role": AgentRole.ADMIN,
        "capabilities": ["scheduling", "followups", "organization", "coordination"],
        "autonomy": AutonomyLevel.FULL,
        "personality": "Chief of staff — mantiene todo en movimiento",
    },
]

db = SessionLocal()
created = 0
for data in agents_data:
    existing = db.query(Agent).filter(Agent.role == data["role"]).first()
    if existing:
        print(f"  YA EXISTE: {data['name']}")
        continue
    agent = Agent(
        name=data["name"],
        emoji=data["emoji"],
        role=data["role"],
        type=AgentType.SYSTEM,
        status=AgentStatus.IDLE,
        capabilities=data["capabilities"],
        personality=data["personality"],
        autonomy_level=data["autonomy"],
        cost_per_execution=0,
    )
    db.add(agent)
    created += 1

db.commit()

# Actividad inicial
for data in agents_data:
    agent = db.query(Agent).filter(Agent.role == data["role"]).first()
    if agent:
        act = Activity(
            type="agent_action",
            description=f"🤖 {agent.name} agente registrado y listo para trabajar",
            agent_id=agent.id,
        )
        db.add(act)
db.commit()

total = db.query(Agent).count()
db.close()
print(f"\nCreados: {created} | Total agentes en DB: {total}")
