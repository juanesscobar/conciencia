"""Base abstractions for the LLM Harness — provider-agnostic contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HarnessError(Exception):
    """Base exception for harness errors."""
    pass


class ProviderError(HarnessError):
    """Provider-specific error (rate limit, auth, timeout, etc.)."""
    def __init__(self, provider: str, message: str, retryable: bool = False):
        self.provider = provider
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


@dataclass
class HarnessConfig:
    """Configuration for a harness execution."""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    fallback_providers: List[str] = field(default_factory=list)
    max_retries: int = 2
    timeout_seconds: int = 60
    budget_usd: Optional[float] = None  # max cost for this execution
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.provider = self.provider.strip().lower()
        self.model = self.model.strip()
        if self.fallback_providers:
            self.fallback_providers = [p.strip().lower() for p in self.fallback_providers]


@dataclass
class UsageMetrics:
    """Token usage and cost metrics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Optional[float] = None

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class HarnessResult:
    """Result of a harness execution."""
    output: Optional[str] = None
    error: Optional[str] = None
    provider: str = ""
    model: str = ""
    usage: Optional[UsageMetrics] = None
    latency_ms: int = 0
    retries: int = 0
    fallback_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.output is not None and self.error is None


class ProviderAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    Each provider (DeepSeek, OpenAI, Anthropic, etc.) must implement this interface.
    The harness orchestrates providers via this common contract.
    """

    provider_name: str = ""
    default_model: str = ""
    default_base_url: str = ""

    @abstractmethod
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
        """Execute a completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            api_key: Provider API key
            base_url: Optional custom base URL
            max_tokens: Max output tokens
            temperature: Sampling temperature
            timeout_seconds: Request timeout

        Returns:
            HarnessResult with output, usage, latency

        Raises:
            ProviderError: If the provider call fails
        """
        pass

    @abstractmethod
    def calculate_cost(self, usage: UsageMetrics, model: str) -> float:
        """Calculate cost in USD for the given usage and model.

        Args:
            usage: Token usage metrics
            model: Model identifier

        Returns:
            Cost in USD
        """
        pass

    def get_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing info for a model (input/output per 1M tokens).

        Args:
            model: Model identifier

        Returns:
            Dict with 'input' and 'output' prices per 1M tokens
        """
        return {"input": 0.0, "output": 0.0}
