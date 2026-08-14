"""Smart routing — select the best provider/model for a task."""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

from .base import HarnessConfig
from .harness import PROVIDER_REGISTRY

log = logging.getLogger("llm_harness.routing")


class RoutingStrategy(str, Enum):
    """Routing strategy for provider selection."""
    COST_OPTIMIZED = "cost_optimized"  # cheapest provider
    LATENCY_OPTIMIZED = "latency_optimized"  # fastest provider
    QUALITY_OPTIMIZED = "quality_optimized"  # most capable model
    BALANCED = "balanced"  # balance cost/quality/latency


@dataclass
class RoutingContext:
    """Context for routing decisions."""
    task_type: Optional[str] = None  # code_review, creative, analysis, etc.
    complexity: Optional[str] = None  # simple, medium, complex
    max_cost_usd: Optional[float] = None
    max_latency_ms: Optional[int] = None
    preferred_providers: Optional[List[str]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def select_provider(
    context: RoutingContext,
    strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    api_keys: Optional[Dict[str, str]] = None,
) -> HarnessConfig:
    """Select the best provider/model for a task.

    Args:
        context: Routing context (task type, complexity, constraints)
        strategy: Routing strategy (cost, latency, quality, balanced)
        api_keys: Dict of provider -> api_key (only configured providers considered)

    Returns:
        HarnessConfig with selected provider/model/fallback
    """
    api_keys = api_keys or {}
    available_providers = [p for p in PROVIDER_REGISTRY.keys() if p in api_keys or p == "ollama"]

    if not available_providers:
        raise ValueError("No providers configured")

    if context.preferred_providers:
        preferred = [p for p in context.preferred_providers if p in available_providers]
        if preferred:
            available_providers = preferred

    if strategy == RoutingStrategy.COST_OPTIMIZED:
        return _route_by_cost(context, available_providers, api_keys)
    elif strategy == RoutingStrategy.LATENCY_OPTIMIZED:
        return _route_by_latency(context, available_providers, api_keys)
    elif strategy == RoutingStrategy.QUALITY_OPTIMIZED:
        return _route_by_quality(context, available_providers, api_keys)
    else:
        return _route_balanced(context, available_providers, api_keys)


def _route_by_cost(
    context: RoutingContext,
    providers: List[str],
    api_keys: Dict[str, str],
) -> HarnessConfig:
    """Select cheapest provider/model."""
    best_provider = None
    best_model = None
    best_cost = float("inf")

    for provider_name in providers:
        adapter = PROVIDER_REGISTRY[provider_name]
        model = _select_model_for_task(adapter, context)
        pricing = adapter.get_pricing(model)
        estimated_cost = pricing["input"] + pricing["output"]

        if estimated_cost < best_cost:
            best_cost = estimated_cost
            best_provider = provider_name
            best_model = model

    fallback = [p for p in providers if p != best_provider]

    return HarnessConfig(
        provider=best_provider,
        model=best_model,
        api_key=api_keys.get(best_provider),
        fallback_providers=fallback,
        budget_usd=context.max_cost_usd,
        metadata=context.metadata,
    )


def _route_by_latency(
    context: RoutingContext,
    providers: List[str],
    api_keys: Dict[str, str],
) -> HarnessConfig:
    """Select fastest provider/model (heuristic: smaller models are faster)."""
    fast_models = {
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-20241022",
        "google": "gemini-2.0-flash",
        "ollama": "llama3.2",
        "openrouter": "deepseek/deepseek-chat",
    }

    for provider_name in providers:
        if provider_name in fast_models:
            fallback = [p for p in providers if p != provider_name]
            return HarnessConfig(
                provider=provider_name,
                model=fast_models[provider_name],
                api_key=api_keys.get(provider_name),
                fallback_providers=fallback,
                budget_usd=context.max_cost_usd,
                metadata=context.metadata,
            )

    return _route_by_cost(context, providers, api_keys)


def _route_by_quality(
    context: RoutingContext,
    providers: List[str],
    api_keys: Dict[str, str],
) -> HarnessConfig:
    """Select most capable model."""
    quality_models = {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4o",
        "google": "gemini-1.5-pro",
        "deepseek": "deepseek-chat",
        "openrouter": "anthropic/claude-sonnet-4",
        "ollama": "llama3.1",
    }

    for provider_name in ["anthropic", "openai", "google", "deepseek", "openrouter", "ollama"]:
        if provider_name in providers:
            fallback = [p for p in providers if p != provider_name]
            return HarnessConfig(
                provider=provider_name,
                model=quality_models[provider_name],
                api_key=api_keys.get(provider_name),
                fallback_providers=fallback,
                budget_usd=context.max_cost_usd,
                metadata=context.metadata,
            )

    return _route_by_cost(context, providers, api_keys)


def _route_balanced(
    context: RoutingContext,
    providers: List[str],
    api_keys: Dict[str, str],
) -> HarnessConfig:
    """Balance cost, quality, and latency."""
    if context.complexity == "simple":
        return _route_by_cost(context, providers, api_keys)
    elif context.complexity == "complex":
        return _route_by_quality(context, providers, api_keys)
    else:
        balanced_models = {
            "deepseek": "deepseek-chat",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
            "google": "gemini-2.0-flash",
            "openrouter": "deepseek/deepseek-chat",
            "ollama": "llama3.2",
        }

        for provider_name in ["deepseek", "openai", "google", "anthropic", "openrouter", "ollama"]:
            if provider_name in providers:
                fallback = [p for p in providers if p != provider_name]
                return HarnessConfig(
                    provider=provider_name,
                    model=balanced_models[provider_name],
                    api_key=api_keys.get(provider_name),
                    fallback_providers=fallback,
                    budget_usd=context.max_cost_usd,
                    metadata=context.metadata,
                )

        return _route_by_cost(context, providers, api_keys)


def _select_model_for_task(adapter, context: RoutingContext) -> str:
    """Select a model based on task type (heuristic)."""
    if context.task_type == "code":
        code_models = {
            "deepseek": "deepseek-coder",
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "google": "gemini-1.5-pro",
        }
        return code_models.get(adapter.provider_name, adapter.default_model)

    return adapter.default_model
