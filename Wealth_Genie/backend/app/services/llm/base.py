"""
LLM provider abstraction.

Business logic (UniversalExtractor, future agents) depends ONLY on this
interface. Concrete providers (claude.py, gemini.py, openai.py, local.py)
are swappable via app/services/llm/factory.py without touching any caller.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProviderError(RuntimeError):
    """Raised when a provider fails to produce usable output."""


class LLMProvider(ABC):
    @abstractmethod
    async def extract_financial_json(self, normalized_text: str, document_type: str) -> dict:
        """
        Convert normalized document text into a dict matching the Universal
        Financial JSON schema (app/schemas_ext/financial.py).

        Implementations must:
          - Return valid JSON only (no prose, no markdown fences).
          - Never fabricate data not present in `normalized_text`.
          - Leave unknown sections as empty lists/dicts rather than omitting keys.

        Raises:
            LLMProviderError: if the provider cannot produce parseable JSON.
        """
        raise NotImplementedError
