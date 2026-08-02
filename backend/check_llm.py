from app.services import llm
print("llm service OK, configured:", llm.is_configured())
from app.routers import agents
print("agents router OK")
from app.models.execution import AgentExecution
print("execution model OK, task_id nullable:", AgentExecution.__table__.c.task_id.nullable)
