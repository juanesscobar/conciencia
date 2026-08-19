"""Cost tracking — usage recording, budgets, and alerts."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import defaultdict

from .base import UsageMetrics

log = logging.getLogger("llm_harness.cost")


@dataclass
class UsageRecord:
    """Single usage record."""
    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetConfig:
    """Budget configuration."""
    limit_usd: float
    period: str = "monthly"  # daily, weekly, monthly, total
    alert_threshold: float = 0.8  # alert at 80% of budget
    hard_stop: bool = False  # stop execution if budget exceeded


class CostTracker:
    """Tracks LLM usage and costs with budget enforcement.

    Usage:
        tracker = CostTracker()
        tracker.set_budget(BudgetConfig(limit_usd=10.0, period="monthly"))

        # Record usage
        tracker.record(provider="deepseek", model="deepseek-chat", usage=usage_metrics)

        # Check budget
        if tracker.is_budget_exceeded():
            raise BudgetExceededError()

        # Get stats
        stats = tracker.get_stats()
    """

    def __init__(self):
        self.records: List[UsageRecord] = []
        self.budgets: Dict[str, BudgetConfig] = {}
        self._stats_cache: Dict[str, Any] = {}

    def record(
        self,
        provider: str,
        model: str,
        usage: UsageMetrics,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record a usage event.

        Args:
            provider: Provider name
            model: Model identifier
            usage: Token usage metrics
            metadata: Optional metadata (agent_id, task_id, project_id, etc.)

        Returns:
            UsageRecord
        """
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            provider=provider,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cost_usd=usage.cost_usd or 0.0,
            metadata=metadata or {},
        )
        self.records.append(record)
        self._stats_cache.clear()
        self._persist(record)
        return record

    @staticmethod
    def _persist(record: "UsageRecord") -> None:
        """Persiste el costo en la DB (best-effort, nunca rompe el flujo)."""
        try:
            from app.database import SessionLocal
            from app.models.cost_record import CostRecord

            db = SessionLocal()
            try:
                db.add(CostRecord(
                    provider=record.provider,
                    model=record.model,
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    total_tokens=record.total_tokens,
                    cost_usd=record.cost_usd,
                    meta=record.metadata,
                ))
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            log.debug("cost persistence skipped", exc_info=True)

        log.info(
            f"Usage recorded: provider={provider}, model={model}, "
            f"tokens={usage.total_tokens}, cost=${usage.cost_usd:.6f}"
        )
        return record

    def set_budget(self, budget: BudgetConfig, scope: str = "global") -> None:
        """Set a budget for a scope (global, project, agent, etc.).

        Args:
            budget: Budget configuration
            scope: Budget scope identifier
        """
        self.budgets[scope] = budget
        log.info(f"Budget set for scope '{scope}': ${budget.limit_usd:.2f} ({budget.period})")

    def get_spent(self, scope: str = "global", period: Optional[str] = None) -> float:
        """Get total spent for a scope and period.

        Args:
            scope: Budget scope
            period: Period filter (daily, weekly, monthly, total)

        Returns:
            Total cost in USD
        """
        now = datetime.utcnow()
        cutoff = None

        if period == "daily":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            days_since_monday = now.weekday()
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff = cutoff.replace(day=cutoff.day - days_since_monday)
        elif period == "monthly":
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total = 0.0
        for record in self.records:
            if cutoff and record.timestamp < cutoff:
                continue
            if scope != "global":
                record_scope = record.metadata.get("scope", "global")
                if record_scope != scope:
                    continue
            total += record.cost_usd

        return round(total, 6)

    def is_budget_exceeded(self, scope: str = "global") -> bool:
        """Check if budget is exceeded for a scope.

        Args:
            scope: Budget scope

        Returns:
            True if budget exceeded
        """
        budget = self.budgets.get(scope) or self.budgets.get("global")
        if not budget:
            return False

        spent = self.get_spent(scope, budget.period)
        return spent >= budget.limit_usd

    def is_budget_warning(self, scope: str = "global") -> bool:
        """Check if budget is approaching limit (alert threshold).

        Args:
            scope: Budget scope

        Returns:
            True if budget warning triggered
        """
        budget = self.budgets.get(scope) or self.budgets.get("global")
        if not budget:
            return False

        spent = self.get_spent(scope, budget.period)
        threshold = budget.limit_usd * budget.alert_threshold
        return spent >= threshold - 1e-9  # tolerance for floating point

    def get_stats(self, scope: str = "global") -> Dict[str, Any]:
        """Get usage statistics.

        Args:
            scope: Budget scope

        Returns:
            Dict with stats (total_cost, total_tokens, by_provider, by_model, etc.)
        """
        if scope in self._stats_cache:
            return self._stats_cache[scope]

        total_cost = 0.0
        total_tokens = 0
        by_provider: Dict[str, float] = defaultdict(float)
        by_model: Dict[str, float] = defaultdict(float)

        for record in self.records:
            if scope != "global":
                record_scope = record.metadata.get("scope", "global")
                if record_scope != scope:
                    continue

            total_cost += record.cost_usd
            total_tokens += record.total_tokens
            by_provider[record.provider] += record.cost_usd
            by_model[record.model] += record.cost_usd

        stats = {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "total_records": len(self.records),
            "by_provider": dict(by_provider),
            "by_model": dict(by_model),
        }

        self._stats_cache[scope] = stats
        return stats

    def export_records(self, scope: str = "global") -> List[Dict[str, Any]]:
        """Export usage records as dicts.

        Args:
            scope: Budget scope

        Returns:
            List of record dicts
        """
        records = []
        for record in self.records:
            if scope != "global":
                record_scope = record.metadata.get("scope", "global")
                if record_scope != scope:
                    continue

            records.append({
                "timestamp": record.timestamp.isoformat(),
                "provider": record.provider,
                "model": record.model,
                "prompt_tokens": record.prompt_tokens,
                "completion_tokens": record.completion_tokens,
                "total_tokens": record.total_tokens,
                "cost_usd": record.cost_usd,
                "metadata": record.metadata,
            })
        return records
