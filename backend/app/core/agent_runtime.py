"""Multi-Runtime Agent Integration (Fase 9 — requisito CEO, 23/08).

Conciencia como control plane: además del motor embebido (generic/LLM Harness),
puede operar agentes externos reales (Claude Code, Codex, OpenCode, OpenClaw)
desde la plataforma. La config vive en Settings (`AGENT_RUNTIMES` JSON) y cada
runtime declara: tipo, comando, cwd, habilitado, timeout y permisos.

Seguridad (spec §28/§47):
- Los CLIs corren en SUBPROCESO con timeout, sin shell=True.
- El comando sale de la config (allowlist) — el usuario NUNCA pasa el binario.
- La tarea se pasa como ARGUMENTO único (nunca se concatena a un shell).
- cwd solo si existe y está en la config; sin cwd → directorio de trabajo default.
- Un runtime externo solo corre si está `enabled=true` (el dueño lo habilitó).
"""

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

SETTING_KEY = "AGENT_RUNTIMES"
DEFAULT_TIMEOUT_S = 300

# Tipos soportados
TYPE_INTERNAL = "internal"   # motor LLM embebido (adapter generic)
TYPE_CLI = "cli"             # CLIs externos (claude/codex/opencode/openclaw)
TYPE_MCP = "mcp"             # herramientas MCP (routers/mcp.py)

DEFAULT_RUNTIMES: List[Dict[str, Any]] = [
    {
        "name": "generic", "type": TYPE_INTERNAL, "label": "Motor embebido (LLM Harness)",
        "enabled": True, "command": "", "cwd": "", "timeout_s": 120,
        "permissions": {"allow": ["*"], "deny": []},
    },
    {
        "name": "claude_code", "type": TYPE_CLI, "label": "Claude Code (CLI)",
        "enabled": False, "command": "claude", "cwd": "", "timeout_s": 300,
        "permissions": {"allow": ["run"], "deny": []},
    },
    {
        "name": "codex", "type": TYPE_CLI, "label": "OpenAI Codex (CLI)",
        "enabled": False, "command": "codex", "cwd": "", "timeout_s": 300,
        "permissions": {"allow": ["run"], "deny": []},
    },
    {
        "name": "opencode", "type": TYPE_CLI, "label": "OpenCode (CLI)",
        "enabled": False, "command": "opencode", "cwd": "", "timeout_s": 300,
        "permissions": {"allow": ["run"], "deny": []},
    },
    {
        "name": "openclaw", "type": TYPE_CLI, "label": "OpenClaw (CLI/gateway)",
        "enabled": False, "command": "openclaw", "cwd": "", "timeout_s": 300,
        "permissions": {"allow": ["run"], "deny": []},
    },
    {
        "name": "mcp", "type": TYPE_MCP, "label": "Herramientas MCP",
        "enabled": True, "command": "", "cwd": "", "timeout_s": 60,
        "permissions": {"allow": ["tool_call"], "deny": []},
    },
]

DEFAULT_CWD = os.path.expanduser("~")

# Template de invocación por tipo: cómo se pasa la tarea como argumento
CLI_ARGS: Dict[str, List[str]] = {
    "claude_code": ["-p", "--output-format", "text"],
    "codex": ["exec"],
    "opencode": ["run"],
    "openclaw": ["run"],
}


@dataclass
class RuntimeConfig:
    """Config de un runtime (persistida en Settings como JSON)."""
    name: str
    type: str
    label: str = ""
    enabled: bool = True
    command: str = ""
    cwd: str = ""
    timeout_s: int = DEFAULT_TIMEOUT_S
    permissions: Dict[str, List[str]] = field(default_factory=lambda: {"allow": ["*"], "deny": []})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "type": self.type, "label": self.label,
            "enabled": self.enabled, "command": self.command, "cwd": self.cwd,
            "timeout_s": self.timeout_s, "permissions": self.permissions,
        }


@dataclass
class RunResult:
    ok: bool
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    runtime: Optional[str] = None
    duration_ms: Optional[int] = None
    exit_code: Optional[int] = None
    simulated: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)


def _db_setting(db: Session, key: str) -> str:
    from app.models.setting import Setting
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value else ""


def _save_setting(db: Session, key: str, value: str) -> None:
    from app.models.setting import Setting
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def get_runtime_configs(db: Session) -> List[RuntimeConfig]:
    """Configs persistidas + defaults (merge por nombre)."""
    defaults = {r["name"]: RuntimeConfig(**r) for r in DEFAULT_RUNTIMES}
    raw = _db_setting(db, SETTING_KEY)
    if raw:
        try:
            for item in json.loads(raw):
                name = item.get("name")
                if name in defaults:
                    cfg = defaults[name]
                    for k, v in item.items():
                        if hasattr(cfg, k):
                            setattr(cfg, k, v)
        except (json.JSONDecodeError, TypeError):
            pass
    return list(defaults.values())


def save_runtime_configs(db: Session, configs: List[Dict[str, Any]]) -> List[RuntimeConfig]:
    """Valida y persiste (solo campos conocidos; nombres existentes)."""
    defaults = {r["name"]: r for r in DEFAULT_RUNTIMES}
    cleaned = []
    for item in configs:
        name = (item.get("name") or "").strip()
        if name not in defaults:
            continue
        cfg = {k: v for k, v in defaults[name].items()}
        for k, v in item.items():
            if k in cfg and k != "name":
                cfg[k] = v
        cleaned.append(cfg)
    _save_setting(db, SETTING_KEY, json.dumps(cleaned, ensure_ascii=False))
    return get_runtime_configs(db)


def get_runtime(db: Session, name: str) -> Optional[RuntimeConfig]:
    for cfg in get_runtime_configs(db):
        if cfg.name == name:
            return cfg
    return None


def check_runtime_health(cfg: RuntimeConfig) -> Dict[str, Any]:
    """¿Está disponible el binario? (no ejecuta nada)."""
    if cfg.type == TYPE_INTERNAL:
        return {"name": cfg.name, "enabled": cfg.enabled, "online": True, "detail": "motor embebido"}
    if cfg.type == TYPE_MCP:
        return {"name": cfg.name, "enabled": cfg.enabled, "online": True, "detail": "MCP tools (vía routers/mcp.py)"}
    if not cfg.command:
        return {"name": cfg.name, "enabled": cfg.enabled, "online": False, "detail": "sin comando configurado"}
    path = shutil.which(cfg.command)
    return {
        "name": cfg.name, "enabled": cfg.enabled,
        "online": bool(path), "detail": path or f"'{cfg.command}' no encontrado en PATH",
    }


def run_in_runtime(db: Session, runtime_name: str, task: str,
                   context: Optional[str] = None) -> RunResult:
    """Ejecuta una tarea en un runtime externo (CLI) o devuelve error claro.

    Para `generic`/`internal` usá el adapter existente (no este runner).
    """
    cfg = get_runtime(db, runtime_name)
    if not cfg:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"Runtime '{runtime_name}' no configurado")
    if not cfg.enabled:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"Runtime '{runtime_name}' está deshabilitado — habilitalo en Settings → Agents → Runtimes (solo el dueño)")

    if cfg.type == TYPE_INTERNAL:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error="Usá el adapter generic (motor embebido) para este runtime")
    if cfg.type == TYPE_MCP:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error="MCP: usá los endpoints de /api/v1/mcp (tool registry)")

    # --- CLI externo (subprocess seguro) ---
    if not cfg.command:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"Runtime '{runtime_name}' sin comando configurado")

    argv = CLI_ARGS.get(runtime_name, [])
    if not argv and runtime_name not in CLI_ARGS:
        # runtime CLI custom: el comando se invoca con la tarea como primer argumento
        pass

    command = [cfg.command, *argv, task]
    cwd = cfg.cwd or DEFAULT_CWD
    if not os.path.isdir(cwd):
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"cwd '{cwd}' no existe — configuralo en Settings → Agents → Runtimes")

    prompt = f"## TAREA\n{task}\n"
    if context:
        prompt = f"## CONTEXTO\n{context[:4000]}\n\n" + prompt

    start = time.time()
    try:
        proc = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=cfg.timeout_s,
            cwd=cwd,
            env={**os.environ, "NO_COLOR": "1"},
        )
        duration_ms = int((time.time() - start) * 1000)
        output = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        ok = proc.returncode == 0
        return RunResult(
            ok=ok,
            status="completed" if ok else "failed",
            output=output[:10000] if output else None,
            error=(err or "salida vacía")[:2000] if not ok else None,
            runtime=runtime_name,
            duration_ms=duration_ms,
            exit_code=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"Timeout ({cfg.timeout_s}s) ejecutando {cfg.command}",
                         duration_ms=int((time.time() - start) * 1000))
    except FileNotFoundError:
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"'{cfg.command}' no encontrado — instalalo o ajustá el comando en Settings")
    except Exception as e:  # noqa: BLE001
        return RunResult(ok=False, status="failed", runtime=runtime_name,
                         error=f"Error ejecutando {cfg.command}: {str(e)[:300]}")
