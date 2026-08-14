"""Tests del LLM Harness — fallback, cost tracking, routing."""

import pytest
from unittest.mock import Mock, patch

from app.services.llm_harness import (
    run_with_harness,
    HarnessConfig,
    HarnessError,
    ProviderError,
    CostTracker,
    UsageMetrics,
    select_provider,
    RoutingStrategy,
)
from app.services.llm_harness.routing import RoutingContext


class TestHarnessFallback:
    """Test fallback chain when primary provider fails."""

    def test_primary_provider_succeeds(self):
        """Primary provider succeeds, no fallback needed."""
        messages = [{"role": "user", "content": "Hello"}]
        config = HarnessConfig(
            provider="deepseek",
            model="deepseek-chat",
            api_key="test-key",
            fallback_providers=["openai"],
        )

        with patch("app.services.llm_harness.harness.get_provider") as mock_get:
            mock_adapter = Mock()
            mock_result = Mock()
            mock_result.ok = True
            mock_result.output = "Response"
            mock_result.provider = "deepseek"
            mock_result.model = "deepseek-chat"
            mock_result.usage = UsageMetrics(prompt_tokens=10, completion_tokens=5, cost_usd=0.001)
            mock_result.latency_ms = 100
            mock_result.fallback_used = False
            mock_result.retries = 0
            mock_adapter.execute.return_value = mock_result
            mock_get.return_value = mock_adapter

            result = run_with_harness(messages, config)

            assert result.ok
            assert result.provider == "deepseek"
            assert not result.fallback_used

    def test_fallback_on_primary_failure(self):
        """Primary fails, fallback succeeds."""
        messages = [{"role": "user", "content": "Hello"}]
        config = HarnessConfig(
            provider="deepseek",
            model="deepseek-chat",
            api_key="test-key",
            fallback_providers=["openai"],
            max_retries=1,
        )

        with patch("app.services.llm_harness.harness.get_provider") as mock_get:
            deepseek_adapter = Mock()
            deepseek_adapter.execute.side_effect = ProviderError("deepseek", "Rate limit", retryable=False)

            openai_adapter = Mock()
            openai_adapter.execute.return_value = Mock(
                ok=True,
                output="Fallback response",
                provider="openai",
                model="gpt-4o-mini",
                usage=UsageMetrics(prompt_tokens=10, completion_tokens=5, cost_usd=0.002),
                latency_ms=150,
            )

            mock_get.side_effect = lambda name: {"deepseek": deepseek_adapter, "openai": openai_adapter}.get(name)

            result = run_with_harness(messages, config)

            assert result.ok
            assert result.provider == "openai"
            assert result.fallback_used

    def test_all_providers_fail(self):
        """All providers fail, raises HarnessError."""
        messages = [{"role": "user", "content": "Hello"}]
        config = HarnessConfig(
            provider="deepseek",
            model="deepseek-chat",
            api_key="test-key",
            fallback_providers=["openai"],
            max_retries=1,
        )

        with patch("app.services.llm_harness.harness.get_provider") as mock_get:
            mock_adapter = Mock()
            mock_adapter.execute.side_effect = ProviderError("test", "Failed", retryable=False)
            mock_get.return_value = mock_adapter

            with pytest.raises(HarnessError, match="All providers failed"):
                run_with_harness(messages, config)


class TestCostTracker:
    """Test cost tracking and budget enforcement."""

    def test_record_usage(self):
        """Record usage and retrieve stats."""
        tracker = CostTracker()
        usage = UsageMetrics(prompt_tokens=100, completion_tokens=50, cost_usd=0.01)

        tracker.record("deepseek", "deepseek-chat", usage)

        stats = tracker.get_stats()
        assert stats["total_cost"] == 0.01
        assert stats["total_tokens"] == 150
        assert stats["by_provider"]["deepseek"] == 0.01

    def test_budget_enforcement(self):
        """Budget exceeded triggers warning."""
        from app.services.llm_harness.cost_tracker import BudgetConfig

        tracker = CostTracker()
        tracker.set_budget(BudgetConfig(limit_usd=0.05, period="total", alert_threshold=0.8, hard_stop=False))

        usage = UsageMetrics(prompt_tokens=100, completion_tokens=50, cost_usd=0.04)
        tracker.record("deepseek", "deepseek-chat", usage)

        assert tracker.is_budget_warning()
        assert not tracker.is_budget_exceeded()

        usage2 = UsageMetrics(prompt_tokens=100, completion_tokens=50, cost_usd=0.02)
        tracker.record("deepseek", "deepseek-chat", usage2)

        assert tracker.is_budget_exceeded()


class TestRouting:
    """Test smart routing strategies."""

    def test_cost_optimized_routing(self):
        """Cost-optimized routing selects cheapest provider."""
        context = RoutingContext(task_type="code", complexity="simple")
        api_keys = {"deepseek": "key1", "openai": "key2", "anthropic": "key3"}

        config = select_provider(context, RoutingStrategy.COST_OPTIMIZED, api_keys)

        assert config.provider in ["deepseek", "ollama"]

    def test_quality_optimized_routing(self):
        """Quality-optimized routing selects most capable model."""
        context = RoutingContext(task_type="code", complexity="complex")
        api_keys = {"deepseek": "key1", "openai": "key2", "anthropic": "key3"}

        config = select_provider(context, RoutingStrategy.QUALITY_OPTIMIZED, api_keys)

        assert config.provider in ["anthropic", "openai"]

    def test_balanced_routing(self):
        """Balanced routing selects middle-ground provider."""
        context = RoutingContext(task_type="code", complexity="medium")
        api_keys = {"deepseek": "key1", "openai": "key2"}

        config = select_provider(context, RoutingStrategy.BALANCED, api_keys)

        assert config.provider in ["deepseek", "openai"]
