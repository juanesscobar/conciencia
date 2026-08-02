"""
System Logger — buffer circular de eventos de la app para el panel de logs.

Captura requests, ejecuciones de agentes, errores y eventos del sistema
en memoria (últimos N eventos). Expuesto vía /api/v1/system/logs.
"""
import logging
import time
from collections import deque
from threading import Lock

MAX_LOGS = 200

_logs = deque(maxlen=MAX_LOGS)
_lock = Lock()


class SystemLogHandler(logging.Handler):
    def emit(self, record):
        try:
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "source": record.name,
                "message": record.getMessage()[:500],
            }
            with _lock:
                _logs.appendleft(entry)
        except Exception:
            pass


def add_log(level: str, source: str, message: str):
    """Agrega un evento manual (requests, agentes, etc.)."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "level": level,
        "source": source,
        "message": message[:500],
    }
    with _lock:
        _logs.appendleft(entry)


def get_logs(limit: int = 50) -> list:
    with _lock:
        return list(_logs)[:limit]


def setup_logging():
    """Instala el handler en el logger raíz y los principales."""
    handler = SystemLogHandler()
    handler.setLevel(logging.INFO)
    root = logging.getLogger()
    root.addHandler(handler)

    # Loggear arranque
    add_log("INFO", "system", "Mission Control backend iniciado")
