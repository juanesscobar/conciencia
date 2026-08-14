"""Anthropic adapter — Claude models."""

import time
from typing import List, Dict, Optional

from ..base import ProviderAdapter, HarnessResult, UsageMetrics, ProviderError

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicAdapter(ProviderAdapter):
    """Anthropic provider adapter (Claude models)."""

    provider_name = "anthropic"
    default_model = "claude-sonnet-4-20250514"
    default_base_url = ""

    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    }

    def execute(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.4,
        timeout_seconds: int = 60,
    ) -> HarnessResult:
        if not ANTHROPIC_AVAILABLE:
            raise ProviderError(self.provider_name, "anthropic SDK not installed", retryable=False)

        if not api_key:
            raise ProviderError(self.provider_name, "API key required", retryable=False)

        client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
        )

        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        start = time.time()
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or None,
                messages=user_messages,
            )
            latency_ms = int((time.time() - start) * 1000)

            output_text = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        output_text += block.text

            usage = None
            if response.usage:
                usage = UsageMetrics(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                    cost_usd=self.calculate_cost(
                        UsageMetrics(
                            prompt_tokens=response.usage.input_tokens,
                            completion_tokens=response.usage.output_tokens,
                        ),
                        model,
                    ),
                )

            return HarnessResult(
                output=output_text,
                provider=self.provider_name,
                model=response.model or model,
                usage=usage,
                latency_ms=latency_ms,
            )

        except anthropic.AuthenticationError as e:
            raise ProviderError(self.provider_name, f"Authentication failed: {e}", retryable=False)
        except anthropic.RateLimitError as e:
            raise ProviderError(self.provider_name, f"Rate limit exceeded: {e}", retryable=True)
        except anthropic.APITimeoutError as e:
            raise ProviderError(self.provider_name, f"Request timeout: {e}", retryable=True)
        except anthropic.APIError as e:
            raise ProviderError(self.provider_name, f"API error: {e}", retryable=False)
        except Exception as e:
            raise ProviderError(self.provider_name, f"Unexpected error: {e}", retryable=False)

    def calculate_cost(self, usage: UsageMetrics, model: str) -> float:
        pricing = self.PRICING.get(model)
        if not pricing:
            for key in self.PRICING:
                if key in model:
                    pricing = self.PRICING[key]
                    break
        if not pricing:
            pricing = self.PRICING["claude-sonnet-4-20250514"]

        input_cost = (usage.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.completion_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def get_pricing(self, model: str) -> Dict[str, float]:
        pricing = self.PRICING.get(model)
        if not pricing:
            for key in self.PRICING:
                if key in model:
                    return self.PRICING[key]
        return pricing or self.PRICING["claude-sonnet-4-20250514"]
