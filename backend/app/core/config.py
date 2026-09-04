"""Config unificada del core (spec §20/§31).

Un solo punto de lectura para settings: env primero, tabla `settings` después
(mismo orden que el resto de la app). Los módulos (leadhunter, futuros) no
deben leer `os.getenv` a mano: usan esto.
"""

import json
import os
from typing import Any, Dict, Optional


def _db_setting(key: str) -> str:
    """Lee un setting persistente de la DB (tabla settings)."""
    try:
        from app.database import SessionLocal
        from app.models.setting import Setting
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == key).first()
            return setting.value if setting and setting.value else ""
        finally:
            db.close()
    except Exception:
        return ""


def get_setting(key: str, default: str = "") -> str:
    """Env primero, DB después (overlay igual que routers/settings)."""
    return os.getenv(key) or _db_setting(key) or default


def get_bool_setting(key: str, default: bool = False) -> bool:
    raw = get_setting(key, "1" if default else "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def get_int_setting(key: str, default: int = 0) -> int:
    try:
        return int(get_setting(key, str(default)))
    except (TypeError, ValueError):
        return default


def get_json_setting(key: str, default: Optional[Any] = None) -> Any:
    raw = get_setting(key, "")
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# --- agrupaciones por dominio (spec §31: admin modifica sin código) ---

def search_defaults() -> Dict[str, Any]:
    """Geografía default: país PY, allowlist, scope (spec §8/§9)."""
    return {
        "default_country": get_setting("SEARCH_DEFAULT_COUNTRY", "PY"),
        "allowed_countries": [c.strip().upper() for c in get_setting("SEARCH_ALLOWED_COUNTRIES", "PY,BR,AR,UY").split(",") if c.strip()],
        "default_region": get_setting("SEARCH_DEFAULT_REGION", "") or None,
        "default_city": get_setting("SEARCH_DEFAULT_CITY", "") or None,
        "scope": (get_setting("SEARCH_SCOPE", "") or get_setting("LEADHUNTER_SCOPE", "") or "country").strip().lower(),
    }


def ranking_weights() -> Dict[str, Dict[str, float]]:
    """Pesos de ranking/scoring (spec §15/§16) — JSON en RANKING_WEIGHTS."""
    return get_json_setting("RANKING_WEIGHTS") or {}


def embedding_config() -> Dict[str, Any]:
    """Config de búsqueda semántica (spec §14)."""
    return {
        "enabled": get_bool_setting("EMBEDDING_ENABLED", False),
        "model": get_setting("EMBEDDING_MODEL", "text-embedding-3-small"),
        "provider": get_setting("EMBEDDING_PROVIDER", "openai"),
        "backend": get_setting("EMBEDDING_BACKEND", "memory"),
        "base_url": get_setting("EMBEDDING_BASE_URL", ""),
    }
