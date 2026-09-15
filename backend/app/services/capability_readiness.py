"""Canonical execution capability and readiness semantics."""

import os
import shutil
from pathlib import Path
from urllib.parse import urlparse


def _valid_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def provider_readiness(provider: str | None = None, model: str | None = None) -> dict:
    """Run the same static provider preflight required by the generic executor."""
    from app.services import llm
    from app.services.llm_harness import get_provider

    cfg = llm.get_config(provider=provider, model=model)
    provider_name = (cfg.get("provider") or "").strip().lower()
    model_name = (cfg.get("model") or "").strip()
    api_key = (cfg.get("api_key") or "").strip()
    base_url = (cfg.get("base_url") or "").strip()
    adapter_registered = bool(provider_name and get_provider(provider_name))
    credentials_required = provider_name != "ollama"
    credentials_available = bool(api_key) or not credentials_required
    base_url_valid = provider_name == "anthropic" or _valid_url(base_url)

    if not provider_name:
        state, reason, action = "misconfigured", "No hay provider seleccionado", "Configurá LLM_PROVIDER"
    elif not adapter_registered:
        state, reason, action = (
            "unavailable",
            f"El provider '{provider_name}' no tiene adapter registrado",
            "Seleccioná un provider soportado",
        )
    elif not model_name:
        state, reason, action = "misconfigured", "No hay modelo seleccionado", "Configurá LLM_MODEL"
    elif not credentials_available:
        key_name = f"{provider_name.upper()}_API_KEY"
        state, reason, action = (
            "blocked",
            f"Credenciales no disponibles para {provider_name}",
            f"Configurá {key_name} en Integraciones o en el entorno",
        )
    elif not base_url_valid:
        state, reason, action = (
            "misconfigured",
            f"Base URL inválida para {provider_name}",
            "Configurá una URL http(s) válida",
        )
    else:
        state, reason, action = "ready", "Preflight de provider completada", None

    ready = state == "ready"
    return {
        "kind": "provider",
        "name": provider_name,
        "provider": provider_name,
        "model": model_name,
        "registered": adapter_registered,
        "configured": bool(provider_name and model_name and base_url_valid),
        "credentials": "available" if api_key else ("not_required" if not credentials_required else "unavailable"),
        "base_url_valid": base_url_valid,
        "state": state,
        "ready": ready,
        "resolvable": ready,
        "reason": reason,
        "action": action,
    }


def runtime_readiness(
    db,
    runtime_name: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    config=None,
) -> dict:
    """Resolve runtime state using the executor's actual static prerequisites."""
    from app.core.agent_runtime import (
        CLI_ARGS,
        TYPE_CLI,
        TYPE_INTERNAL,
        TYPE_MCP,
        get_runtime,
    )

    cfg = config or get_runtime(db, runtime_name)
    if not cfg:
        return {
            "kind": "runtime",
            "name": runtime_name,
            "registered": False,
            "detected": False,
            "configured": False,
            "enabled": False,
            "state": "unavailable",
            "ready": False,
            "resolvable": False,
            "reason": f"Runtime '{runtime_name}' no registrado",
            "action": "Registrá o seleccioná un runtime soportado",
        }

    common = {
        "kind": "runtime",
        "name": cfg.name,
        "type": cfg.type,
        "registered": True,
        "enabled": bool(cfg.enabled),
    }
    if cfg.type == TYPE_INTERNAL:
        provider_status = provider_readiness(provider=provider, model=model)
        state = "disabled" if not cfg.enabled else provider_status["state"]
        ready = bool(cfg.enabled and provider_status["ready"])
        reason = "Runtime deshabilitado por configuración" if not cfg.enabled else provider_status["reason"]
        action = "Habilitá el runtime con conciencia onboard" if not cfg.enabled else provider_status["action"]
        return {
            **common,
            "detected": True,
            "configured": provider_status["configured"],
            "state": state,
            "ready": ready,
            "resolvable": ready,
            "reason": reason,
            "action": action,
            "provider": provider_status,
        }
    if cfg.type == TYPE_MCP:
        ready = bool(cfg.enabled)
        return {
            **common,
            "detected": True,
            "configured": True,
            "state": "ready" if ready else "disabled",
            "ready": ready,
            "resolvable": ready,
            "reason": "MCP habilitado" if ready else "MCP deshabilitado por configuración",
            "action": None if ready else "Habilitá MCP explícitamente",
        }

    path = shutil.which(cfg.command) if cfg.command else None
    detected = bool(path)
    cwd = Path(cfg.cwd or os.path.expanduser("~"))
    handler_registered = cfg.type != TYPE_CLI or cfg.name in CLI_ARGS
    configured = bool(cfg.command and cwd.is_dir() and handler_registered)
    if not cfg.enabled:
        state = "disabled"
        reason = "Runtime detectado pero deshabilitado" if detected else "Runtime deshabilitado y binario no detectado"
        action = "Ejecutá conciencia onboard para habilitarlo con consentimiento"
    elif not cfg.command or not handler_registered:
        state, reason, action = "misconfigured", "Runtime sin comando o handler válido", "Revisá AGENT_RUNTIMES"
    elif not cwd.is_dir():
        state, reason, action = "misconfigured", f"Directorio de trabajo inexistente: {cwd}", "Configurá un cwd válido"
    elif not detected:
        state, reason, action = "unavailable", f"Binario '{cfg.command}' no encontrado en PATH", "Instalá el runtime o corregí command"
    else:
        state, reason, action = "ready", "Preflight de runtime completada", None
    ready = state == "ready"
    return {
        **common,
        "detected": detected,
        "binary": path,
        "configured": configured,
        "state": state,
        "ready": ready,
        "resolvable": ready,
        "reason": reason,
        "action": action,
    }


def execution_overview(db) -> dict:
    """Return all execution runtimes and a truthful aggregate state."""
    from app.core.agent_runtime import TYPE_CLI, TYPE_INTERNAL, get_runtime_configs

    runtimes = [
        runtime_readiness(db, cfg.name, config=cfg)
        for cfg in get_runtime_configs(db)
        if cfg.type in {TYPE_INTERNAL, TYPE_CLI}
    ]
    ready = [runtime for runtime in runtimes if runtime["ready"]]
    generic = next((runtime for runtime in runtimes if runtime["name"] == "generic"), None)
    if generic and generic["ready"]:
        overall = "READY"
    elif ready:
        overall = "READY WITH LIMITATIONS"
    else:
        overall = "BLOCKED FOR MISSION EXECUTION"
    return {"overall": overall, "ready": bool(ready), "runtimes": runtimes}


def tool_readiness(tool: dict) -> dict:
    """Apply the common state vocabulary to a configured MCP tool server."""
    name = tool.get("name") or "unknown"
    enabled = bool(tool.get("enabled", True))
    command = (tool.get("command") or "").strip()
    binary = shutil.which(command) if command else None
    cwd_value = tool.get("cwd")
    cwd_valid = not cwd_value or Path(cwd_value).expanduser().is_dir()
    configured = bool(command and cwd_valid)
    if not enabled:
        state, reason = "disabled", "Tool deshabilitada por configuración"
    elif not command or not cwd_valid:
        state, reason = "misconfigured", "Command o cwd inválido"
    elif not binary:
        state, reason = "unavailable", f"Binario '{command}' no encontrado en PATH"
    else:
        state, reason = "ready", "Preflight de proceso completada"
    return {
        "kind": "tool",
        "name": name,
        "registered": True,
        "detected": bool(binary),
        "configured": configured,
        "enabled": enabled,
        "state": state,
        "ready": state == "ready",
        "reason": reason,
    }
