"""LLM Harness core — orchestrates providers with fallback, retry, and cost tracking."""

import logging
from typing import List, Dict, Optional

from .base import ProviderAdapter, HarnessConfig, HarnessResult, HarnessError, ProviderError, UsageMetrics
from .providers import (
    DeepSeekAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    GoogleAdapter,
    OllamaAdapter,
    OpenRouterAdapter,
)
from .cost_tracker import CostTracker

log = logging.getLogger("llm_harness")

PROVIDER_REGISTRY: Dict[str, ProviderAdapter] = {
    "deepseek": DeepSeekAdapter(),
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "google": GoogleAdapter(),
    "ollama": OllamaAdapter(),
    "openrouter": OpenRouterAdapter(),
}


def get_provider(name: str) -> Optional[ProviderAdapter]:
    """Get a provider adapter by name."""
    return PROVIDER_REGISTRY.get(name.strip().lower())


def list_providers() -> List[str]:
    """List all available provider names."""
    return list(PROVIDER_REGISTRY.keys())


def run_with_harness(
    messages: List[Dict[str, str]],
    config: HarnessConfig,
    cost_tracker: Optional[CostTracker] = None,
) -> HarnessResult:
    """Execute a completion request with fallback chain and retry logic.

    Args:
        messages: List of message dicts with 'role' and 'content'
        config: Harness configuration (provider, model, fallback, budget, etc.)
        cost_tracker: Optional cost tracker for usage recording

    Returns:
        HarnessResult with output, usage, latency, retries, fallback info

    Raises:
        HarnessError: If all providers fail
    """
    if not config.api_key and config.provider != "ollama":
        raise HarnessError(f"API key required for provider '{config.provider}'")

    providers_to_try = [config.provider] + config.fallback_providers
    last_error: Optional[Exception] = None
    total_retries = 0

    # --- Token efficiency (harness engineering) ---
    # Optimize the message list ONCE, before the provider loop:
    #  - context window budgeting (keep system, prune oldest, compact middle)
    #  - pre-flight cost guard using the primary provider's pricing
    token_stats: Dict[str, int] = {}
    if config.efficient_mode:
        from .token_budget import TokenOptimizer

        optimizer = TokenOptimizer(
            max_context_tokens=config.max_context_tokens,
            max_output_tokens=config.max_output_tokens,
        )
        primary = get_provider(providers_to_try[0]) if providers_to_try else None
        pricing = primary.get_pricing(config.model) if primary else None
        messages, token_stats = optimizer.optimize(
            messages, pricing=pricing, budget_usd=config.budget_usd
        )
        if token_stats and token_stats.get("original_tokens", 0) > 0:
            log.info(f"TokenOptimizer stats: {token_stats}")

    for idx, provider_name in enumerate(providers_to_try):
        provider = get_provider(provider_name)
        if not provider:
            log.warning(f"Unknown provider '{provider_name}', skipping")
            continue

        is_fallback = idx > 0
        base_url = config.base_url if not is_fallback else None
        model = config.model if not is_fallback else provider.default_model

        for attempt in range(config.max_retries + 1):
            try:
                result = provider.execute(
                    messages=messages,
                    model=model,
                    api_key=config.api_key or "",
                    base_url=base_url,
                    max_tokens=config.max_output_tokens,
                    timeout_seconds=config.timeout_seconds,
                )

                if cost_tracker and result.usage:
                    cost_tracker.record(
                        provider=result.provider,
                        model=result.model,
                        usage=result.usage,
                        metadata=config.metadata,
                    )

                if is_fallback:
                    result.fallback_used = True
                    result.retries = total_retries

                if token_stats:
                    metadata = getattr(result, "metadata", None)
                    if not isinstance(metadata, dict):
                        metadata = {}
                        result.metadata = metadata
                    metadata["token_stats"] = token_stats

                log.info(
                    f"Harness success: provider={result.provider}, model={result.model}, "
                    f"latency={result.latency_ms}ms, cost=${result.usage.cost_usd if result.usage else 0:.6f}"
                )
                return result

            except ProviderError as e:
                last_error = e
                total_retries += 1

                if not e.retryable or attempt >= config.max_retries:
                    log.warning(
                        f"Harness provider '{provider_name}' failed (attempt {attempt + 1}): {e}"
                    )
                    break

                log.info(f"Retrying provider '{provider_name}' (attempt {attempt + 2})")

    error_msg = f"All providers failed. Last error: {last_error}" if last_error else "No providers available"
    log.error(f"Harness failure: {error_msg}")
    raise HarnessError(error_msg)
