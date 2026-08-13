"""
LLM Service — Motor de agentes (DeepSeek).

La configuración se resuelve en este orden:
  1. Settings persistentes en DB (tabla settings: DEEPSEEK_API_KEY, LLM_MODEL)
  2. Variables de entorno (backend/.env): DEEPSEEK_API_KEY, LLM_MODEL
"""
import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"


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


def get_config(provider: Optional[str] = None, model: Optional[str] = None) -> dict:
    """Resuelve la config activa de DeepSeek.

    provider/model se ignoran (DeepSeek-only); se mantienen por compatibilidad de firma.
    """
    api_key = (
        os.getenv("DEEPSEEK_API_KEY")
        or _db_setting("DEEPSEEK_API_KEY")
        or os.getenv("LLM_API_KEY")
        or _db_setting("LLM_API_KEY")
    )
    active_model = (
        model
        or os.getenv("LLM_MODEL")
        or _db_setting("LLM_MODEL")
        or DEEPSEEK_DEFAULT_MODEL
    )
    base_url = (
        os.getenv("LLM_BASE_URL")
        or _db_setting("LLM_BASE_URL")
        or DEEPSEEK_BASE_URL
    )
    return {
        "provider": "deepseek",
        "api_key": api_key or "",
        "model": active_model,
        "base_url": base_url,
    }


def is_configured() -> bool:
    cfg = get_config()
    return bool(cfg["api_key"]) and OpenAI is not None


def get_client():
    cfg = get_config()
    if not is_configured():
        raise RuntimeError(
            "LLM no configurado. Agregá tu DEEPSEEK_API_KEY desde Configuración → Integraciones."
        )
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def test_connection(provider: Optional[str] = None, api_key: Optional[str] = None,
                    model: Optional[str] = None, base_url: Optional[str] = None) -> dict:
    """Prueba una conexión DeepSeek con la config dada (o la activa). Devuelve resultado."""
    import time

    cfg = get_config()
    api_key = (api_key or cfg["api_key"]).strip()
    model = model or cfg["model"]
    base_url = (base_url or cfg["base_url"]).strip() or DEEPSEEK_BASE_URL

    if not api_key:
        return {"ok": False, "error": "Falta DEEPSEEK_API_KEY"}

    if OpenAI is None:
        return {"ok": False, "error": "openai SDK no instalado"}

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        start = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Respondé solo: OK"}],
            max_tokens=5,
            temperature=0,
        )
        latency = int((time.time() - start) * 1000)
        return {
            "ok": True,
            "provider": "deepseek",
            "model": resp.model or model,
            "latency_ms": latency,
            "reply": (resp.choices[0].message.content or "")[:40],
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "provider": "deepseek", "model": model, "error": str(e)[:300]}


def run_agent(agent_name: str, system_prompt: str, task: str, context: Optional[str] = None) -> dict:
    """
    Ejecuta un agente contra el proveedor LLM configurado.

    Returns:
        dict con {output, usage, model, provider, simulated}
    """
    cfg = get_config()

    if not is_configured():
        return {
            "output": (
                "[MODO SIMULADO] DeepSeek no configurado. Agregá tu DEEPSEEK_API_KEY desde "
                "Configuración → Integraciones.\n\n"
                f"Agente: {agent_name}\nTarea recibida: {task[:200]}"
            ),
            "usage": None,
            "model": cfg["model"],
            "provider": cfg["provider"],
            "simulated": True,
        }

    try:
        client = get_client()
    except RuntimeError as e:
        return {"output": None, "error": str(e), "model": cfg["model"], "provider": cfg["provider"], "simulated": False}

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if context:
        messages.append({"role": "user", "content": f"## CONTEXTO\n{context}\n"})
    messages.append({"role": "user", "content": f"## TAREA\n{task}"})

    try:
        response = client.chat.completions.create(
            model=cfg["model"],
            messages=messages,
            temperature=0.4,
            max_tokens=2000,
        )
        return {
            "output": response.choices[0].message.content,
            "usage": response.usage.model_dump() if response.usage else None,
            "model": response.model,
            "provider": cfg["provider"],
            "simulated": False,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "output": None,
            "error": str(e),
            "model": cfg["model"],
            "provider": cfg["provider"],
            "simulated": False,
        }
