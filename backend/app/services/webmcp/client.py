"""WebMCPClient — interactúa con una app web WebMCP-enabled (Fase K).

El cliente habla el bridge HTTP que la app WebMCP expone (el JS de
`window.webmcp` de la página usa el mismo bridge). Permite que una MISIÓN
interactúe con la app: consultar contexto, ejecutar acciones y tomar
snapshots — y preservar evidencia (action log + snapshot final).
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger("webmcp")

DEFAULT_TIMEOUT_S = 15.0
MAX_ACTIONS = 50


class WebMCPError(Exception):
    pass


def _base_url(url: str) -> str:
    return url.rstrip("/")


def get_context(base_url: str) -> Dict[str, Any]:
    """Contexto de la app: qué puede ver el agente."""
    try:
        r = httpx.get(f"{_base_url(base_url)}/api/webmcp/context", timeout=DEFAULT_TIMEOUT_S)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise WebMCPError(f"no se pudo obtener contexto de {base_url}: {e}") from e


def act(base_url: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta una acción en la app (input/click/submit/navigate)."""
    try:
        r = httpx.post(
            f"{_base_url(base_url)}/api/webmcp/act",
            json={"action": action},
            timeout=DEFAULT_TIMEOUT_S,
        )
        if r.status_code == 400:
            raise WebMCPError(r.json().get("detail", "acción rechazada por la app"))
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise WebMCPError(f"acción falló en {base_url}: {e}") from e


def snapshot(base_url: str) -> Dict[str, Any]:
    """Snapshot del estado actual (evidencia)."""
    try:
        r = httpx.get(f"{_base_url(base_url)}/api/webmcp/snapshot", timeout=DEFAULT_TIMEOUT_S)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise WebMCPError(f"snapshot falló en {base_url}: {e}") from e


def run_script(base_url: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Ejecuta una secuencia de acciones y preserva evidencia.

    Devuelve {url, actions_count, action_log, snapshot} — el action_log
    registra cada acción con su resultado (evidencia trazable).
    """
    if not actions:
        raise WebMCPError("sin acciones para ejecutar")
    if len(actions) > MAX_ACTIONS:
        raise WebMCPError(f"demasiadas acciones (máx {MAX_ACTIONS})")

    base = _base_url(base_url)
    action_log: List[Dict[str, Any]] = []

    # 1. contexto inicial (evidencia de estado previo)
    try:
        initial_context = get_context(base)
    except WebMCPError:
        initial_context = {}

    # 2. acciones
    for i, action in enumerate(actions):
        start = time.time()
        try:
            result = act(base, action)
            ok, error = True, None
            if isinstance(result, dict) and result.get("ok") is False:
                ok, error = False, result.get("error")
        except WebMCPError as e:
            ok, error = False, str(e)
            result = None
        action_log.append({
            "index": i,
            "action": action,
            "ok": ok,
            "error": error,
            "result": (result or {}).get("result") if isinstance(result, dict) else None,
            "duration_ms": int((time.time() - start) * 1000),
        })

    # 3. snapshot final (evidencia)
    try:
        final_snapshot = snapshot(base)
    except WebMCPError:
        final_snapshot = {}

    return {
        "url": base,
        "actions_count": len(action_log),
        "action_log": action_log,
        "initial_context": initial_context,
        "snapshot": final_snapshot,
    }
