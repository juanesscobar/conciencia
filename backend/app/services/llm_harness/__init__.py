"""LLM Harness — provider-agnostic orchestration with fallback, cost tracking, and smart routing."""

from .base import ProviderAdapter, HarnessConfig, HarnessResult, HarnessError, ProviderError, UsageMetrics
from .harness import run_with_harness, get_provider, list_providers, PROVIDER_REGISTRY
from .cost_tracker import CostTracker, UsageRecord
from .routing import select_provider, RoutingStrategy, RoutingContext

__all__ = [
    "ProviderAdapter",
    "HarnessConfig",
    "HarnessResult",
    "HarnessError",
    "ProviderError",
    "UsageMetrics",
    "run_with_harness",
    "get_provider",
    "list_providers",
    "PROVIDER_REGISTRY",
    "CostTracker",
    "UsageRecord",
    "select_provider",
    "RoutingStrategy",
    "RoutingContext",
]
