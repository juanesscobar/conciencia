"""Ollama adapter — local models (OpenAI-compatible API)."""

import time
from typing import List, Dict, Optional

from ..base import ProviderAdapter, HarnessResult, UsageMetrics, ProviderError

try:
    from openai import OpenAI
    from openai import APIError, APITimeoutError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OllamaAdapter(ProviderAdapter):
    """Ollama provider adapter (local models via OpenAI-compatible API)."""

    provider_name = "ollama"
    default_model = "llama3.2"
    default_base_url = "http://localhost:11434/v1"

    PRICING = {
        "llama3.2": {"input": 0.0, "output": 0.0},
        "llama3.1": {"input": 0.0, "output": 0.0},
        "mistral": {"input": 0.0, "output": 0.0},
        "codellama": {"input": 0.0, "output": 0.0},
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

        client = OpenAI(
            api_key=api_key or "ollama",
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
                    cost_usd=0.0,
                )

            return HarnessResult(
                output=response.choices[0].message.content,
                provider=self.provider_name,
                model=response.model or model,
                usage=usage,
                latency_ms=latency_ms,
            )

        except APITimeoutError as e:
            raise ProviderError(self.provider_name, f"Request timeout: {e}", retryable=True)
        except APIError as e:
            raise ProviderError(self.provider_name, f"API error: {e}", retryable=False)
        except Exception as e:
            raise ProviderError(self.provider_name, f"Unexpected error: {e}", retryable=False)

    def calculate_cost(self, usage: UsageMetrics, model: str) -> float:
        return 0.0

    def get_pricing(self, model: str) -> Dict[str, float]:
        return {"input": 0.0, "output": 0.0}
