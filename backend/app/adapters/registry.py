"""Agent Adapter Registry — resuelve el adapter según el runtime del agente."""

from typing import Dict, Optional

from .base import AgentAdapter
from .generic import GenericAgentAdapter
from .openclaw import OpenClawAdapter

_ADAPTERS: Dict[str, AgentAdapter] = {}


def _ensure() -> None:
    if not _ADAPTERS:
        _ADAPTERS["generic"] = GenericAgentAdapter()
        _ADAPTERS["openclaw"] = OpenClawAdapter()
        # Claude Code / Codex: se registran cuando haya implementación concreta
        # (el contrato ya los soporta; sin adapter devuelven "unsupported").


def get_adapter(runtime: str) -> Optional[AgentAdapter]:
    _ensure()
    return _ADAPTERS.get((runtime or "generic").lower())


def list_runtimes() -> list:
    _ensure()
    return [
        {"name": name, "capabilities": adapter.get_capabilities()}
        for name, adapter in _ADAPTERS.items()
    ]


def adapters() -> Dict[str, AgentAdapter]:
    _ensure()
    return _ADAPTERS
