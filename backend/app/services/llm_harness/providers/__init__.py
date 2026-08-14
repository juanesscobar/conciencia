"""Provider adapters — concrete implementations for each LLM provider."""

from .deepseek import DeepSeekAdapter
from .openai_provider import OpenAIAdapter
from .anthropic import AnthropicAdapter
from .google import GoogleAdapter
from .ollama import OllamaAdapter
from .openrouter import OpenRouterAdapter

__all__ = [
    "DeepSeekAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GoogleAdapter",
    "OllamaAdapter",
    "OpenRouterAdapter",
]
