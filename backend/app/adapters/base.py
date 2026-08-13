"""Agent Adapter Layer — contrato común para ejecutar agentes en distintos runtimes.

Un agente en Mission Control se describe por DOS ejes ortogonales:
  - Runtime: CÓMO ejecuta (OpenClaw, Claude Code, Codex, Generic/embebido)
  - Provider: QUIÉN da el modelo LLM (DeepSeek, OpenAI, Anthropic, Google...)

Mission Control es runtime-agnostic: el adapter traduce el contrato común
(dispatch/cancel/status/logs) a la mecánica de cada runtime.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentIdentity:
    """Identidad mínima que el adapter necesita para ejecutar."""
    agent_id: str
    name: str
    role: str
    runtime: str          # generic | openclaw | claude_code | codex
    provider: str         # deepseek | openai | anthropic | google | ollama | openrouter
    model: Optional[str] = None
    workspace: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: list = field(default_factory=list)
    config: dict = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Resultado de un dispatch (ejecución de tarea)."""
    ok: bool
    status: str                     # completed | failed | cancelled | running
    output: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    runtime: Optional[str] = None
    usage: Optional[dict] = None    # {prompt_tokens, completion_tokens, total_tokens, cost_estimate}
    duration_ms: Optional[int] = None
    simulated: bool = False
    meta: dict = field(default_factory=dict)


class AgentAdapter(ABC):
    """Contrato común para cualquier runtime de agentes."""

    runtime_name: str = "generic"

    @abstractmethod
    def dispatch_task(self, identity: AgentIdentity, task: str, context: Optional[str] = None) -> DispatchResult:
        """Ejecuta una tarea. Debe retornar DispatchResult (puede ser sync)."""

    @abstractmethod
    def get_capabilities(self) -> list:
        """Capacidades que este runtime expone (control de ejecución, herramientas...)."""

    # --- Opcionales (defaults no-op) ---

    def get_status(self, agent_id: str) -> dict:
        return {"agent_id": agent_id, "runtime": self.runtime_name, "status": "unknown"}

    def cancel_task(self, agent_id: str, execution_id: Optional[str] = None) -> dict:
        return {"ok": False, "reason": "cancel not supported by this runtime"}

    def stream_logs(self, agent_id: str, execution_id: Optional[str] = None) -> list:
        return []
