"""
Factory for LLMProvider implementations.

Adding a new provider (Gemini, OpenAI, local model) means:
  1. Create app/services/llm/<provider>.py implementing LLMProvider.
  2. Register it in _PROVIDERS below.
No other file in the codebase needs to change.
"""
from __future__ import annotations

from app.config import settings
from app.services.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "claude":
        from app.services.llm.claude import ClaudeLLMProvider
        return ClaudeLLMProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider_name}'. "
        f"Supported: claude. Add a new provider module to enable others."
    )
