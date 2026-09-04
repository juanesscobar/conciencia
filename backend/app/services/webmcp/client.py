"""WebMCPClient — interactúa con una app web WebMCP-enabled (Fase K).

El cliente habla el bridge HTTP que la app WebMCP expone (el JS de
`window.webmcp` de la página usa el mismo bridge). Permite que una MISIÓN
interactúe con la app: consultar contexto, ejecutar acciones y tomar
snapshots — y preservar evidencia (action log + snapshot final).
"""

import logging
import os
import socket
import time
from ipaddress import ip_address
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

import httpx

log = logging.getLogger("webmcp")

DEFAULT_TIMEOUT_S = 15.0
MAX_ACTIONS = 50


class WebMCPError(Exception):
    pass


def _base_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise WebMCPError("URL WebMCP inválida: solo se permiten http/https con host")
    if parsed.username or parsed.password:
        raise WebMCPError("URL WebMCP inválida: no se permiten credenciales embebidas")

    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    allowed_hosts = {
        host.strip().lower()
        for host in os.getenv("WEBMCP_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }
    host = parsed.hostname.lower().rstrip(".")
    if environment == "production":
        if not allowed_hosts or host not in allowed_hosts:
            raise WebMCPError(
                f"host WebMCP no permitido en producción: {host}; "
                "configurá WEBMCP_ALLOWED_HOSTS"
            )
    elif allowed_hosts and host not in allowed_hosts:
        raise WebMCPError(f"host WebMCP no permitido: {host}")

    # Resolver ahora detecta hosts inválidos y permite auditar destinos privados.
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port)}
    except socket.gaierror as exc:
        raise WebMCPError(f"host WebMCP no resoluble: {host}") from exc
    if environment == "production" and host not in allowed_hosts:
        if any(ip_address(addr).is_private or ip_address(addr).is_loopback for addr in addresses):
            raise WebMCPError("destino WebMCP privado no permitido")
    return value


def _json_response(response: httpx.Response, operation: str) -> Dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise WebMCPError(f"respuesta WebMCP inválida durante {operation}: JSON esperado") from exc
    if not isinstance(payload, dict):
        raise WebMCPError(f"respuesta WebMCP inválida durante {operation}: objeto esperado")
    return payload


def get_context(base_url: str) -> Dict[str, Any]:
    """Contexto de la app: qué puede ver el agente."""
    try:
        r = httpx.get(f"{_base_url(base_url)}/api/webmcp/context", timeout=DEFAULT_TIMEOUT_S)
        r.raise_for_status()
        return _json_response(r, "context")
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
            raise WebMCPError(_json_response(r, "act").get("detail", "acción rechazada por la app"))
        r.raise_for_status()
        return _json_response(r, "act")
    except httpx.HTTPError as e:
        raise WebMCPError(f"acción falló en {base_url}: {e}") from e


def snapshot(base_url: str) -> Dict[str, Any]:
    """Snapshot del estado actual (evidencia)."""
    try:
        r = httpx.get(f"{_base_url(base_url)}/api/webmcp/snapshot", timeout=DEFAULT_TIMEOUT_S)
        r.raise_for_status()
        return _json_response(r, "snapshot")
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
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or not str(action.get("type") or "").strip():
            raise WebMCPError(f"acción WebMCP inválida en posición {index}: type requerido")

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
