"""
LLM Service — Motor de agentes vía API DeepSeek (compatible con OpenAI SDK).

Cada agente usa su SOUL.md/AGENTS.md como system prompt y ejecuta tareas
con la API de DeepSeek. La API key se lee de DEEPSEEK_API_KEY en .env.
"""
import os
import json
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def is_configured() -> bool:
    return bool(DEEPSEEK_API_KEY) and OpenAI is not None


def get_client():
    if not is_configured():
        raise RuntimeError(
            "DEEPSEEK_API_KEY no configurada. Agregala en backend/.env "
            "(https://platform.deepseek.com)"
        )
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


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
                "[MODO SIMULADO] DeepSeek no configurado (falta DEEPSEEK_API_KEY en backend/.env).\n\n"
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
