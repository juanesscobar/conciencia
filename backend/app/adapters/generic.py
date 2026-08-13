"""GenericAgentAdapter — runtime embebido: llama al LLM del provider configurado.

Este es el runtime por defecto de Mission Control. El "harness" es eficiente en
tokens: trunca el system prompt (SOUL.md) y el contexto a presupuestos medibles,
y registra usage (prompt/completion/cost) en cada ejecución.
"""

import time
from typing import Optional

from .base import AgentAdapter, AgentIdentity, DispatchResult

# Presupuestos de tokens para el harness (token efficiency)
MAX_SYSTEM_PROMPT_CHARS = 4000      # ~1000 tokens de system prompt (SOUL.md resumido)
MAX_CONTEXT_CHARS = 6000            # contexto adicional limitado
MAX_TASK_CHARS = 4000               # tarea limitada
MAX_OUTPUT_TOKENS = 2000

# Costo por millón de tokens (USD, deepseek-chat)
PRICING_PER_1M = {
    "deepseek": {"input": 0.27, "output": 1.10},
}

DEFAULT_PRICE = {"input": 0.27, "output": 1.10}


def _truncate(s: str, max_chars: int) -> str:
    if not s:
        return ""
    return s[:max_chars] if len(s) > max_chars else s


class GenericAgentAdapter(AgentAdapter):
    runtime_name = "generic"

    def get_capabilities(self) -> list:
        return ["llm_chat", "context_window", "token_usage_tracking"]

    def dispatch_task(self, identity: AgentIdentity, task: str, context: Optional[str] = None) -> DispatchResult:
        from app.services.llm import get_config, is_configured, get_client

        start = time.time()
        cfg = get_config(provider=identity.provider or None, model=identity.model or None)

        # ----- Token efficiency: recortar a presupuestos -----
        system_prompt = _truncate(identity.system_prompt or "", MAX_SYSTEM_PROMPT_CHARS)
        task_limited = _truncate(task, MAX_TASK_CHARS)
        context_limited = _truncate(context or "", MAX_CONTEXT_CHARS)

        if not is_configured() and cfg.get("provider") != "ollama":
            return DispatchResult(
                ok=False,
                status="failed",
                error="DeepSeek no configurado. Agregá tu DEEPSEEK_API_KEY desde Configuración → Integraciones.",
                provider=cfg.get("provider"),
                model=cfg.get("model"),
                runtime=self.runtime_name,
                simulated=True,
                duration_ms=int((time.time() - start) * 1000),
                meta={"reason": "llm_not_configured"},
            )

        try:
            client = get_client()
            messages = [{"role": "system", "content": system_prompt}]
            if context_limited:
                messages.append({"role": "user", "content": f"## CONTEXTO\n{context_limited}\n"})
            messages.append({"role": "user", "content": f"## TAREA\n{task_limited}"})

            response = client.chat.completions.create(
                model=cfg["model"],
                messages=messages,
                temperature=0.4,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            usage = response.usage.model_dump() if response.usage else None
            price = PRICING_PER_1M.get(cfg.get("provider", ""), DEFAULT_PRICE)
            cost = None
            if usage:
                cost = round(
                    (usage.get("prompt_tokens", 0) / 1_000_000 * price["input"])
                    + (usage.get("completion_tokens", 0) / 1_000_000 * price["output"]),
                    6,
                )
            return DispatchResult(
                ok=True,
                status="completed",
                output=response.choices[0].message.content,
                model=response.model or cfg["model"],
                provider=cfg.get("provider"),
                runtime=self.runtime_name,
                usage={**usage, "cost_estimate_usd": cost} if usage else {"cost_estimate_usd": cost},
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:  # noqa: BLE001
            return DispatchResult(
                ok=False,
                status="failed",
                error=str(e)[:300],
                provider=cfg.get("provider"),
                model=cfg.get("model"),
                runtime=self.runtime_name,
                duration_ms=int((time.time() - start) * 1000),
            )
