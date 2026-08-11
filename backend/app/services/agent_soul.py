"""Carga la identidad (SOUL.md / AGENTS.md) de un agente desde el filesystem.

Es el mismo mecanismo que usa el router de agentes, extraído a un servicio
compartido para que el sales squad (propuestas) reutilice las mismas personalidades.
"""

import os


def _default_agents_dir() -> str:
    """Repo local en dev, /app en Docker."""
    local = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "agents",
    )
    if os.path.isdir(local):
        return local
    return "/app/agents"


AGENTS_DIR = os.getenv("AGENTS_DIR") or _default_agents_dir()


def list_agent_roles() -> list:
    if not os.path.isdir(AGENTS_DIR):
        return []
    return sorted(d for d in os.listdir(AGENTS_DIR) if os.path.isdir(os.path.join(AGENTS_DIR, d)))


def load_agent_persona(role: str) -> str:
    """Devuelve todos los .md del agente (SOUL.md, AGENTS.md…) concatenados como system prompt."""
    agent_dir = os.path.join(AGENTS_DIR, role)
    if not os.path.isdir(agent_dir):
        return ""
    parts: list = []
    for fname in sorted(os.listdir(agent_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(agent_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                parts.append(f"===== {fname} =====\n{f.read()}\n")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(parts)
