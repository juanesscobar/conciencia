"""OpenRouter adapter — multi-model gateway (OpenAI-compatible API)."""

import time
from typing import List, Dict, Optional

from ..base import ProviderAdapter, HarnessResult, UsageMetrics, ProviderError

try:
    from openai import OpenAI
    from openai import APIError, APITimeoutError, RateLimitError, AuthenticationError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenRouterAdapter(ProviderAdapter):
    """OpenRouter provider adapter (multi-model gateway)."""

    provider_name = "openrouter"
    default_model = "deepseek/deepseek-chat"
    default_base_url = "https://openrouter.ai/api/v1"

    PRICING = {
        "deepseek/deepseek-chat": {"input": 0.27, "output": 1.10},
        "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
        "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "google/gemini-2.0-flash": {"input": 0.075, "output": 0.30},
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
        if not OPENAI_AVAILABLE:
            raise ProviderError(self.provider_name, "openai SDK not installed", retryable=False)

        if not api_key:
            raise ProviderError(self.provider_name, "API key required", retryable=False)

        client = OpenAI(
            api_key=api_key,
            base_url=base_url or self.default_base_url,
            timeout=timeout_seconds,
        )

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            latency_ms = int((time.time() - start) * 1000)

            usage = None
            if response.usage:
                usage = UsageMetrics(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    cost_usd=self.calculate_cost(
                        UsageMetrics(
                            prompt_tokens=response.usage.prompt_tokens,
                            completion_tokens=response.usage.completion_tokens,
                        ),
                        model,
                    ),
                )

            return HarnessResult(
                output=response.choices[0].message.content,
                provider=self.provider_name,
                model=response.model or model,
                usage=usage,
                latency_ms=latency_ms,
            )

        except AuthenticationError as e:
            raise ProviderError(self.provider_name, f"Authentication failed: {e}", retryable=False)
        except RateLimitError as e:
            raise ProviderError(self.provider_name, f"Rate limit exceeded: {e}", retryable=True)
        except APITimeoutError as e:
            raise ProviderError(self.provider_name, f"Request timeout: {e}", retryable=True)
        except APIError as e:
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
            pricing = self.PRICING["deepseek/deepseek-chat"]

        input_cost = (usage.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.completion_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def get_pricing(self, model: str) -> Dict[str, float]:
        pricing = self.PRICING.get(model)
        if not pricing:
            for key in self.PRICING:
                if key in model:
                    return self.PRICING[key]
        return pricing or self.PRICING["deepseek/deepseek-chat"]
