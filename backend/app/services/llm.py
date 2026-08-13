"""
LLM Service — Motor de agentes multi-proveedor (OpenAI-compatible).

Proveedores soportados: deepseek · openai · ollama · openrouter
La configuración se resuelve en este orden:
  1. Settings persistentes en DB (tabla settings: LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL)
  2. Variables de entorno (backend/.env)
  3. Backward-compat: DEEPSEEK_API_KEY (env o DB) → provider deepseek
"""
import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

PROVIDER_DEFAULTS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "deepseek/deepseek-chat"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "llama3.2"},
    "anthropic": {"base_url": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-20250514"},
    "google": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.0-flash"},
}

DEFAULT_PROVIDER = "deepseek"


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
    """Resuelve la config activa del proveedor LLM.

    Si se pasa provider/model explícitos (ej: del registro del agente),
    esos prevalecen sobre la config global.
    """
    active_provider = os.getenv("LLM_PROVIDER") or _db_setting("LLM_PROVIDER") or DEFAULT_PROVIDER
    active_provider = active_provider.strip().lower()

    api_key = os.getenv("LLM_API_KEY") or _db_setting("LLM_API_KEY")
    active_model = os.getenv("LLM_MODEL") or _db_setting("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL") or _db_setting("LLM_BASE_URL")

    # Override por agente
    if provider:
        active_provider = provider.strip().lower()
        # La API key se resuelve por provider cuando hay override
        key_env = {
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }.get(active_provider)
        if key_env:
            api_key = os.getenv(key_env) or _db_setting(key_env) or api_key

    # Backward-compat con DEEPSEEK_API_KEY
    if not api_key and active_provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY") or _db_setting("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY") or _db_setting("OPENAI_API_KEY")

    defaults = PROVIDER_DEFAULTS.get(active_provider, PROVIDER_DEFAULTS[DEFAULT_PROVIDER])
    return {
        "provider": active_provider,
        "api_key": api_key or "",
        "model": model or active_model or defaults["model"],
        "base_url": base_url or defaults["base_url"],
    }


def is_configured() -> bool:
    cfg = get_config()
    return bool(cfg["api_key"]) and OpenAI is not None


def get_client():
    cfg = get_config()
    if not is_configured():
        raise RuntimeError(
            "LLM no configurado. Agregá tu API key desde Configuración → Integraciones "
            "(proveedor: deepseek/openai/openrouter/ollama)."
        )
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def test_connection(provider: Optional[str] = None, api_key: Optional[str] = None,
                    model: Optional[str] = None, base_url: Optional[str] = None) -> dict:
    """Prueba una conexión LLM con la config dada (o la activa). Devuelve resultado."""
    import time

    if provider:
        provider = provider.strip().lower()
    cfg = get_config()
    provider = provider or cfg["provider"]
    api_key = (api_key or cfg["api_key"]).strip()
    model = model or cfg["model"]
    base_url = (base_url or cfg["base_url"]).strip()

    if not api_key and provider != "ollama":
        return {"ok": False, "error": "Falta la API key del proveedor"}

    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS[DEFAULT_PROVIDER])
    base_url = base_url or defaults["base_url"]
    model = model or defaults["model"]

    if OpenAI is None:
        return {"ok": False, "error": "openai SDK no instalado"}

    try:
        client = OpenAI(api_key=api_key or "ollama", base_url=base_url)
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
            "provider": provider,
            "model": resp.model or model,
            "latency_ms": latency,
            "reply": (resp.choices[0].message.content or "")[:40],
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "provider": provider, "model": model, "error": str(e)[:300]}


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
                "[MODO SIMULADO] LLM no configurado. Agregá tu API key desde "
                "Configuración → Integraciones (proveedor: deepseek/openai/openrouter/ollama).\n\n"
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
