"""GenericAgentAdapter — runtime embebido: usa el LLM Harness para dispatch.

Este es el runtime por defecto de Mission Control. El harness orquesta providers
con fallback, cost tracking, y routing inteligente. Token efficiency: trunca
system prompt (SOUL.md) y contexto a presupuestos medibles.
"""

import time
from typing import Optional

from .base import AgentAdapter, AgentIdentity, DispatchResult

MAX_SYSTEM_PROMPT_CHARS = 4000
MAX_CONTEXT_CHARS = 6000
MAX_TASK_CHARS = 4000
MAX_OUTPUT_TOKENS = 2000


def _truncate(s: str, max_chars: int) -> str:
    if not s:
        return ""
    return s[:max_chars] if len(s) > max_chars else s


class GenericAgentAdapter(AgentAdapter):
    runtime_name = "generic"

    def get_capabilities(self) -> list:
        return ["llm_chat", "context_window", "token_usage_tracking", "multi_provider", "fallback", "cost_tracking"]

    def dispatch_task(self, identity: AgentIdentity, task: str, context: Optional[str] = None) -> DispatchResult:
        from app.services.llm_harness import run_with_harness, HarnessConfig, HarnessError, CostTracker
        from app.services.llm import get_config
        from app.services.capability_readiness import provider_readiness

        start = time.time()

        system_prompt = _truncate(identity.system_prompt or "", MAX_SYSTEM_PROMPT_CHARS)
        task_limited = _truncate(task, MAX_TASK_CHARS)
        context_limited = _truncate(context or "", MAX_CONTEXT_CHARS)

        messages = [{"role": "system", "content": system_prompt}]
        if context_limited:
            messages.append({"role": "user", "content": f"## CONTEXTO\n{context_limited}\n"})
        messages.append({"role": "user", "content": f"## TAREA\n{task_limited}"})

        cfg = get_config(provider=identity.provider or None, model=identity.model or None)

        readiness = provider_readiness(provider=cfg.get("provider"), model=cfg.get("model"))
        if not readiness["ready"]:
            action = readiness.get("action")
            error = readiness["reason"] + (f". {action}" if action else "")
            return DispatchResult(
                ok=False,
                status="failed",
                error=error,
                provider=cfg.get("provider"),
                model=cfg.get("model"),
                runtime=self.runtime_name,
                simulated=True,
                duration_ms=int((time.time() - start) * 1000),
                meta={"reason": "llm_not_ready", "readiness": readiness["state"]},
            )

        fallback_providers = identity.config.get("fallback_providers", [])
        routing_strategy = identity.config.get("routing_strategy")

        harness_config = HarnessConfig(
            provider=cfg["provider"],
            model=cfg["model"],
            api_key=cfg["api_key"],
            base_url=cfg.get("base_url"),
            fallback_providers=fallback_providers,
            max_retries=2,
            timeout_seconds=60,
            metadata={
                "agent_id": identity.agent_id,
                "agent_name": identity.name,
                "role": identity.role,
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

            return DispatchResult(
                ok=result.ok,
                status="completed" if result.ok else "failed",
                output=result.output,
                error=result.error,
                model=result.model,
                provider=result.provider,
                runtime=self.runtime_name,
                usage=usage_dict,
                duration_ms=result.latency_ms or int((time.time() - start) * 1000),
                meta={
                    "retries": result.retries,
                    "fallback_used": result.fallback_used,
                },
            )

        except HarnessError as e:
            return DispatchResult(
                ok=False,
                status="failed",
                error=str(e)[:300],
                provider=cfg.get("provider"),
                model=cfg.get("model"),
                runtime=self.runtime_name,
                duration_ms=int((time.time() - start) * 1000),
            )
