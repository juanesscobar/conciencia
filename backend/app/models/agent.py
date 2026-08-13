from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, JSON, Numeric, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
import enum

class AgentRole(str, enum.Enum):
    DEV = "dev"
    OPS = "ops"
    QA = "qa"
    PM = "pm"
    RD = "rd"
    COMMS = "comms"
    FIN = "fin"
    ADMIN = "admin"

class AutonomyLevel(str, enum.Enum):
    FULL = "full"
    PREVIEW = "preview"
    APPROVAL = "approval"

class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    ERROR = "error"

class AgentType(str, enum.Enum):
    SYSTEM = "system"
    CUSTOM = "custom"
    MARKETPLACE = "marketplace"


class AgentRuntime(str, enum.Enum):
    """Runtime / ejecutor del agente — CÓMO ejecuta (independiente del proveedor LLM)."""
    GENERIC = "generic"          # motor LLM embebido (llm service) — default
    OPENCLAW = "openclaw"        # OpenClaw CLI/daemon
    CLAUDE_CODE = "claude_code"  # Claude Code CLI
    CODEX = "codex"              # OpenAI Codex CLI


class AgentProvider(str, enum.Enum):
    """Proveedor del modelo — QUIÉN da el LLM (independiente del runtime)."""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    emoji = Column(String(10), default="🤖")
    role = Column(Enum(AgentRole), nullable=False)
    type = Column(Enum(AgentType), default=AgentType.CUSTOM)
    
    status = Column(Enum(AgentStatus), default=AgentStatus.IDLE)
    current_task_id = Column(Uuid, ForeignKey("tasks.id", use_alter=True), nullable=True)
    
    capabilities = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    personality = Column(Text)
    system_prompt = Column(Text)

    # Arquitectura: runtime (cómo ejecuta) vs provider (quién da el modelo) vs model
    runtime = Column(Enum(AgentRuntime, values_callable=lambda e: [m.value for m in e]), default=AgentRuntime.GENERIC, nullable=False)
    provider = Column(Enum(AgentProvider, values_callable=lambda e: [m.value for m in e]), default=AgentProvider.DEEPSEEK, nullable=False)
    model = Column(String(100), nullable=True)
    workspace = Column(String(255), nullable=True)  # directorio de trabajo del runtime

    # Health / registry
    health_status = Column(String(20), default="unknown")  # online | idle | busy | degraded | offline | error | unknown
    last_heartbeat = Column(DateTime, nullable=True)
    version = Column(String(50), nullable=True)
    availability = Column(String(20), default="available")  # available | busy | maintenance
    
    autonomy_level = Column(Enum(AutonomyLevel), default=AutonomyLevel.PREVIEW)
    cost_per_execution = Column(Numeric(10, 4), default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activities = relationship("Activity", back_populates="agent")
    executions = relationship("AgentExecution", back_populates="agent")
    tasks = relationship("Task", back_populates="assigned_agent", foreign_keys="Task.assignee_id")
    current_task = relationship("Task", foreign_keys=[current_task_id])
