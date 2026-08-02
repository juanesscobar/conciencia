"""
LLM Service — Motor de agentes vía API DeepSeek (compatible con OpenAI SDK).

Cada agente usa su SOUL.md/AGENTS.md como system prompt y ejecuta tareas
con la API de DeepSeek. La API key se resuelve en este orden:
  1. Variable de entorno DEEPSEEK_API_KEY (seteada por el router de settings)
  2. Setting persistente DEEPSEEK_API_KEY en la DB (tabla settings)
  3. backend/.env
"""
import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _load_key_from_db() -> str:
    """Intenta leer DEEPSEEK_API_KEY desde la tabla settings."""
    try:
        from app.database import SessionLocal
        from app.models.setting import Setting
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == "DEEPSEEK_API_KEY").first()
            return setting.value if setting and setting.value else ""
        finally:
            db.close()
    except Exception:
        return ""


def get_api_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        key = _load_key_from_db()
    return key


def is_configured() -> bool:
    return bool(get_api_key()) and OpenAI is not None


def get_client():
    if not is_configured():
        raise RuntimeError(
            "DEEPSEEK_API_KEY no configurada. Agregala desde el Dashboard → Settings, "
            "o en backend/.env (https://platform.deepseek.com)"
        )
    return OpenAI(api_key=get_api_key(), base_url=DEEPSEEK_BASE_URL)


def run_agent(agent_name: str, system_prompt: str, task: str, context: Optional[str] = None) -> dict:
    """
    Ejecuta un agente contra DeepSeek.

    Args:
        agent_name: nombre del agente (para logging)
        system_prompt: SOUL.md + AGENTS.md del agente
        task: la tarea a ejecutar
        context: contexto adicional (proyecto, historial, etc.)

    Returns:
        dict con {output, usage, model}
    """
    if not is_configured():
        return {
            "output": (
                "[MODO SIMULADO] DeepSeek no configurado. "
                "Agregá tu DEEPSEEK_API_KEY desde el Dashboard → Settings (configuración de agentes).\n\n"
                f"Agente: {agent_name}\nTarea recibida: {task[:200]}"
            ),
            "usage": None,
            "model": DEEPSEEK_MODEL,
            "simulated": True,
        }

    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if context:
        messages.append({"role": "user", "content": f"## CONTEXTO\n{context}\n"})
    messages.append({"role": "user", "content": f"## TAREA\n{task}"})

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=2000,
        )
        return {
            "output": response.choices[0].message.content,
            "usage": response.usage.model_dump() if response.usage else None,
            "model": response.model,
            "simulated": False,
        }
    except Exception as e:
        return {
            "output": None,
            "error": str(e),
            "model": DEEPSEEK_MODEL,
            "simulated": False,
        }
