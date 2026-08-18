"""
Token efficiency layer for the LLM Harness — "harness engineering" for tokens.

Provides:
- prompt token estimation (deterministic heuristic, no external deps)
- context window budgeting: always keep system prompt, prune oldest messages,
  compact the middle when pruning alone is not enough
- output token caps
- pre-flight cost guard: estimate cost BEFORE calling the provider and abort
  early when over budget

This module is provider-agnostic and dependency-free (pure stdlib).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("llm_harness.tokens")

# Rough heuristic: mixed ES/EN business text ≈ 4 chars/token.
CHARS_PER_TOKEN = 4.0
PER_MESSAGE_OVERHEAD_TOKENS = 4  # role + formatting overhead per message

COMPACT_PLACEHOLDER = (
    "[historial compactado: {n} mensajes anteriores omitidos por presupuesto de contexto]"
)


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text chunk (heuristic, no tokenizer needed)."""
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimate total tokens for a message list."""
    total = 0
    for m in messages:
        content = m.get("content") or ""
        role = m.get("role") or ""
        total += estimate_tokens(f"{role} {content}") + PER_MESSAGE_OVERHEAD_TOKENS
    return total


def _estimate_cost(prompt_tokens: int, output_tokens: int, pricing: Dict[str, float]) -> float:
    """Estimate USD cost from pricing dict {input: $/1M, output: $/1M}."""
    input_price = float(pricing.get("input", 0.0))
    output_price = float(pricing.get("output", 0.0))
    return (prompt_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)


@dataclass
class TokenOptimizer:
    """Optimizes a message list before it is sent to a provider.

    Modes (all optional, driven by config):
      - max_context_tokens:  context window budget. System prompt is always kept;
                            oldest non-system messages are pruned first; if pruning
                            would leave fewer than `min_keep_messages`, the middle
                            of the history is replaced with a compact placeholder.
      - max_output_tokens:   cap on generated output (passed to the provider).
      - budget_usd:          pre-flight cost guard using the provider's pricing.
    """

    max_context_tokens: int = 0           # 0 = context budgeting disabled
    max_output_tokens: int = 2000         # cap on generated output
    reserve_ratio: float = 0.15           # keep this fraction of budget for the response
    min_keep_messages: int = 3            # never prune below this many messages
    always_keep_system: bool = True       # never drop the system prompt

    def optimize(
        self,
        messages: List[Dict[str, str]],
        pricing: Optional[Dict[str, float]] = None,
        budget_usd: Optional[float] = None,
    ) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
        """Return (optimized_messages, stats).

        stats keys:
          original_tokens, final_tokens, pruned_messages, compacted_messages,
          cost_guard_triggered
        """
        stats: Dict[str, int] = {
            "original_tokens": 0,
            "final_tokens": 0,
            "pruned_messages": 0,
            "compacted_messages": 0,
            "cost_guard_triggered": 0,
        }

        if not messages:
            return messages, stats

        original_tokens = estimate_messages_tokens(messages)
        stats["original_tokens"] = original_tokens

        work: List[Dict[str, str]] = list(messages)

        # --- Pre-flight cost guard -------------------------------------------
        if budget_usd and pricing:
            est = _estimate_cost(original_tokens, self.max_output_tokens, pricing)
            if est > budget_usd:
                log.warning(
                    "Cost guard: est $%.6f > budget $%.6f — pruning history before call",
                    est,
                    budget_usd,
                )
                stats["cost_guard_triggered"] = 1
                work = self._prune_to_fit(work, hard_keep=self.min_keep_messages)
                stats["pruned_messages"] += len(messages) - len(work)

        # --- Context window budgeting -----------------------------------------
        if self.max_context_tokens > 0:
            budget = int(self.max_context_tokens * (1.0 - self.reserve_ratio))
            usage = estimate_messages_tokens(work)
            if usage > budget:
                work, pruned, compacted = self._fit_context(work, budget)
                stats["pruned_messages"] += pruned
                stats["compacted_messages"] += compacted

        stats["final_tokens"] = estimate_messages_tokens(work)

        saved = stats["original_tokens"] - stats["final_tokens"]
        if saved > 0:
            log.info(
                "TokenOptimizer: %d -> %d tokens (saved %d, pruned=%d, compacted=%d, cost_guard=%d)",
                stats["original_tokens"],
                stats["final_tokens"],
                saved,
                stats["pruned_messages"],
                stats["compacted_messages"],
                stats["cost_guard_triggered"],
            )
        return work, stats

    # --- internals -----------------------------------------------------------

    def _split_system(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        system, rest = [], []
        for m in messages:
            (system if m.get("role") == "system" else rest).append(m)
        return system, rest

    def _fit_context(
        self, messages: List[Dict[str, str]], budget: int
    ) -> Tuple[List[Dict[str, str]], int, int]:
        """Fit messages into token budget. Returns (messages, pruned, compacted)."""
        system, rest = self._split_system(messages)
        kept_system = system if self.always_keep_system else []

        # 1) Prune oldest non-system messages while still above min_keep.
        pruned = 0
        while (
            len(rest) > self.min_keep_messages
            and estimate_messages_tokens(kept_system + rest) > budget
        ):
            rest.pop(0)  # oldest first
            pruned += 1

        # 2) If still over budget, compact the middle into a placeholder.
        compacted = 0
        if estimate_messages_tokens(kept_system + rest) > budget and len(rest) > 2:
            middle = rest[1:-1]
            tail = rest[-1:]
            rest = [rest[0], {"role": "system", "content": COMPACT_PLACEHOLDER.format(n=len(middle))}, *tail]
            compacted = len(middle)

        return kept_system + rest, pruned, compacted

    def _prune_to_fit(self, messages: List[Dict[str, str]], hard_keep: int) -> List[Dict[str, str]]:
        """Hard prune (cost guard): system + last N messages only."""
        system, rest = self._split_system(messages)
        kept = system + rest[-hard_keep:]
        return kept
