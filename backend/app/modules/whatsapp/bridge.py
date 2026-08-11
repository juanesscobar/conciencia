"""Bridge hacia el sidecar Node (wa-bridge/server.js) que maneja WhatsApp Web.

El sidecar escucha en 127.0.0.1 (WA_BRIDGE_PORT, default 8123). Este módulo lo
levanta bajo demanda (si node está disponible), chequea salud y proxya llamadas.
"""

import os
import shutil
import subprocess
import threading
import time

import httpx

WA_BRIDGE_URL = os.getenv("WA_BRIDGE_URL", "http://127.0.0.1:8123")
WA_BRIDGE_PORT = int(os.getenv("WA_BRIDGE_PORT", "8123"))

_proc: "subprocess.Popen | None" = None
_lock = threading.Lock()
_healthy = False


def _bridge_dir() -> str:
    local = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
        "wa-bridge",
    )
    if os.path.isdir(local):
        return local
    return "/app/wa-bridge"


def _http() -> httpx.Client:
    return httpx.Client(base_url=WA_BRIDGE_URL, timeout=30)


def _is_healthy() -> bool:
    try:
        with _http() as c:
            r = c.get("/health")
            return r.status_code == 200 and r.json().get("ok")
    except Exception:  # noqa: BLE001
        return False


def _spawn() -> bool:
    """Levanta el sidecar Node si node está disponible. Devuelve si quedó sano."""
    global _proc
    if not shutil.which("node"):
        return False
    if _is_healthy():
        return True
    try:
        _proc = subprocess.Popen(
            ["node", "server.js"],
            cwd=_bridge_dir(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for _ in range(40):  # hasta ~10s
            time.sleep(0.25)
            if _is_healthy():
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


def ensure_running() -> bool:
    global _healthy
    with _lock:
        if _is_healthy():
            _healthy = True
            return True
        if _spawn():
            _healthy = True
            return True
        _healthy = False
        return False


def _call(method: str, path: str, **kwargs) -> dict:
    if not ensure_running():
        return {"ok": False, "error": "El bridge de WhatsApp no está disponible (node/wa-bridge no instalado)."}
    try:
        with _http() as c:
            r = c.request(method, path, **kwargs)
            data = r.json()
            if not isinstance(data, dict):
                data = {"ok": bool(r.status_code < 400)}
            if r.status_code >= 400:
                data.setdefault("ok", False)
            return data
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def get_status() -> dict:
    """Estado de la sesión: disconnected | starting | qr | connecting | connected | error."""
    status = _call("GET", "/status")
    return status if status.get("ok") else {"ok": False, "state": "error", "error": status.get("error", "bridge caído")}


def connect() -> dict:
    """Pide al sidecar arrancar el cliente (genera QR en /status)."""
    return _call("POST", "/connect")


def disconnect() -> dict:
    """Cierra sesión y borra el estado guardado."""
    return _call("POST", "/disconnect")


def send_message(to_phone: str, message: str) -> dict:
    """Envía un mensaje a un número (formato E.164, ej: 595981123456)."""
    return _call("POST", "/send", json={"to": to_phone, "message": message})
