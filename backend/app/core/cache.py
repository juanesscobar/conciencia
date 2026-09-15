"""Cache TTL en memoria (spec §36) — thread-safe, dict local + hook redis opcional.

Uso: cache_get/cache_set con TTL en segundos. Claves planas o "prefijo:clave".
En local es un dict; si REDIS_URL está configurado se puede extender acá sin
tocar a los llamadores.
"""

import threading
import time
from typing import Any, Optional

DEFAULT_TTL = 300  # 5 min


class TTLCache:
    """Dict con expiración por entrada (lazy pruning al acceder)."""

    def __init__(self, default_ttl: int = DEFAULT_TTL) -> None:
        self._default_ttl = default_ttl
        self._data: dict = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            ts, value = hit
            if time.time() - ts >= self._default_ttl:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._data[key] = (time.time(), value)
            if ttl is not None:
                # TTL por entrada: guardamos el valor con su expiración propia
                self._data[key] = (time.time() - self._default_ttl + ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)


_cache = TTLCache()


def cache_get(key: str) -> Optional[Any]:
    return _cache.get(key)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    _cache.set(key, value, ttl=ttl)


def cache_delete(key: str) -> None:
    _cache.delete(key)


def cache_clear() -> None:
    """Invalida todo (se llama en create/update/delete/import/hunt)."""
    _cache.clear()


def invalidate_prefix(prefix: str) -> None:
    """Borra claves que empiezan con `prefix`."""
    with _cache._lock:
        for k in [k for k in _cache._data if k.startswith(prefix)]:
            _cache._data.pop(k, None)
