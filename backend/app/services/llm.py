"""
LLM Service — Wrapper sobre el LLM Harness para compatibilidad.

Este módulo mantiene la interfaz `run_agent()` para compatibilidad con código existente
(LeadHunter, proposals, etc.), pero internamente usa el LLM Harness con fallback,
cost tracking, y routing inteligente.

La configuración se resuelve en este orden:
  1. Settings persistentes en DB (tabla settings: LLM_PROVIDER, DEEPSEEK_API_KEY, etc.)
  2. Variables de entorno (backend/.env)
  3. Fallback providers configurados en LLM_FALLBACK_PROVIDERS
"""
import json
import os
from typing import Optional

from app.services.llm_harness import (
    run_with_harness,
    HarnessConfig,
    HarnessError,
    CostTracker,
    UsageMetrics,
)


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


def _get_api_key(provider: str) -> str:
    """Obtiene la API key para un provider específico."""
    key_env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    env_key = key_env_map.get(provider, f"{provider.upper()}_API_KEY")
    return os.getenv(env_key) or _db_setting(env_key) or ""


def _get_fallback_providers() -> list:
    """Obtiene la lista de fallback providers configurados."""
    fallback_str = os.getenv("LLM_FALLBACK_PROVIDERS") or _db_setting("LLM_FALLBACK_PROVIDERS")
    if not fallback_str:
        return []
    try:
        return json.loads(fallback_str)
    except (json.JSONDecodeError, TypeError):
        return []


def get_config(provider: Optional[str] = None, model: Optional[str] = None) -> dict:
    """Resuelve la config activa del proveedor LLM.

    Si se pasa provider/model explícitos (ej: del registro del agente),
    esos prevalecen sobre la config global.
    """
    active_provider = os.getenv("LLM_PROVIDER") or _db_setting("LLM_PROVIDER") or "deepseek"
    active_provider = active_provider.strip().lower()

    if provider:
        active_provider = provider.strip().lower()

    api_key = _get_api_key(active_provider)
    active_model = os.getenv("LLM_MODEL") or _db_setting("LLM_MODEL")

    # Defaults por provider
    defaults = {
        "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
        "anthropic": {"base_url": "", "model": "claude-sonnet-4-20250514"},
        "google": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.0-flash"},
        "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "deepseek/deepseek-chat"},
        "ollama": {"base_url": "http://localhost:11434/v1", "model": "llama3.2"},
    }

    provider_defaults = defaults.get(active_provider, defaults["deepseek"])
    base_url = os.getenv("LLM_BASE_URL") or _db_setting("LLM_BASE_URL") or provider_defaults["base_url"]

    return {
        "provider": active_provider,
        "api_key": api_key,
        "model": model or active_model or provider_defaults["model"],
        "base_url": base_url,
    }


def is_configured() -> bool:
    """Return readiness of the selected provider used by actual execution."""
    from app.services.capability_readiness import provider_readiness

    return provider_readiness()["ready"]


def run_agent(agent_name: str, system_prompt: str, task: str, context: Optional[str] = None) -> dict:
    """
    Ejecuta un agente usando el LLM Harness con fallback automático.

    Returns:
        dict con {output, usage, model, provider, simulated, cost_usd, fallback_used}
    """
    cfg = get_config()

    if not is_configured():
        return {
            "output": (
                "[MODO SIMULADO] LLM no configurado. Agregá tu API key desde "
                "Configuración → Integraciones.\n\n"
                f"Agente: {agent_name}\nTarea recibida: {task[:200]}"
            ),
            "usage": None,
            "model": cfg["model"],
            "provider": cfg["provider"],
            "simulated": True,
        }

    # Construir mensajes
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if context:
        messages.append({"role": "user", "content": f"## CONTEXTO\n{context}\n"})
    messages.append({"role": "user", "content": f"## TAREA\n{task}"})

    # Configurar harness
    fallback_providers = _get_fallback_providers()
    # Filtrar el provider actual de los fallbacks
    fallback_providers = [p for p in fallback_providers if p != cfg["provider"]]

    # --- Token efficiency settings (harness engineering) ---
    def _int_setting(key: str, default: int) -> int:
        try:
            return int(os.getenv(key) or _db_setting(key) or default)
        except (TypeError, ValueError):
            return default

    efficient_mode = (
        os.getenv("LLM_EFFICIENT_MODE") or _db_setting("LLM_EFFICIENT_MODE") or "true"
    ).lower() in ("1", "true", "yes", "on")

    budget_usd = None
    try:
        raw_budget = os.getenv("LLM_BUDGET_USD") or _db_setting("LLM_BUDGET_USD") or ""
        if raw_budget:
            budget_usd = float(raw_budget)
    except (TypeError, ValueError):
        budget_usd = None

    harness_config = HarnessConfig(
        provider=cfg["provider"],
        model=cfg["model"],
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        fallback_providers=fallback_providers,
        max_retries=2,
        timeout_seconds=60,
        budget_usd=budget_usd,
        efficient_mode=efficient_mode,
        max_context_tokens=_int_setting("LLM_MAX_CONTEXT_TOKENS", 0),
        max_output_tokens=_int_setting("LLM_MAX_OUTPUT_TOKENS", 2000),
        metadata={
            "agent_name": agent_name,
            "source": "run_agent",
        },
    )

    cost_tracker = CostTracker()

    try:
        result = run_with_harness(messages, harness_config, cost_tracker)

        usage_dict = None
        if result.usage:
            usage_dict = {
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
                "cost_estimate_usd": result.usage.cost_usd,
            }

        return {
            "output": result.output,
            "usage": usage_dict,
            "model": result.model,
            "provider": result.provider,
            "simulated": False,
            "cost_usd": result.usage.cost_usd if result.usage else 0.0,
            "fallback_used": result.fallback_used,
            "retries": result.retries,
            "token_stats": result.metadata.get("token_stats", {}),
        }

    except HarnessError as e:
        return {
            "output": None,
            "error": str(e),
            "model": cfg["model"],
            "provider": cfg["provider"],
            "simulated": False,
        }


def test_connection(provider: Optional[str] = None, api_key: Optional[str] = None,
                    model: Optional[str] = None, base_url: Optional[str] = None) -> dict:
    """Prueba una conexión LLM con la config dada (o la activa). Devuelve resultado."""
    import time

    cfg = get_config(provider=provider, model=model)
    provider = provider or cfg["provider"]
    api_key = (api_key or cfg["api_key"]).strip()
    model = model or cfg["model"]
    base_url = (base_url or cfg["base_url"]).strip()

    if not api_key and provider != "ollama":
        return {"ok": False, "error": "Falta la API key del proveedor"}

    # Defaults por provider
    defaults = {
        "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
        "anthropic": {"base_url": "", "model": "claude-sonnet-4-20250514"},
        "google": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.0-flash"},
        "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "deepseek/deepseek-chat"},
        "ollama": {"base_url": "http://localhost:11434/v1", "model": "llama3.2"},
    }

    provider_defaults = defaults.get(provider, defaults["deepseek"])
    base_url = base_url or provider_defaults["base_url"]
    model = model or provider_defaults["model"]

    # Usar el provider adapter del harness
    from app.services.llm_harness import get_provider

    adapter = get_provider(provider)
    if not adapter:
        return {"ok": False, "error": f"Provider '{provider}' no soportado"}

    try:
        result = adapter.execute(
            messages=[{"role": "user", "content": "Respondé solo: OK"}],
            model=model,
            api_key=api_key or "ollama",
            base_url=base_url,
            max_tokens=5,
            temperature=0,
            timeout_seconds=10,
        )
        return {
            "ok": True,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "reply": (result.output or "")[:40],
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "provider": provider, "model": model, "error": str(e)[:300]}
