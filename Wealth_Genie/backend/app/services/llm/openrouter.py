"""
OpenRouter implementation of LLMProvider.

This is the only file in the codebase permitted to import the `openai` SDK
(used here purely as an OpenAI-compatible HTTP client pointed at OpenRouter's
Chat Completions endpoint). Everything else talks to `LLMProvider` (base.py).

OpenRouter proxies many underlying models (Gemini, Llama, Claude, GPT, etc.)
behind a single OpenAI-compatible API, so the same client works regardless of
which model string is configured via LLM_MODEL.
"""

from __future__ import annotations

import json
import re

import openai

from app.config import settings
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.prompts import EXTRACTION_SYSTEM_PROMPT, FINANCIAL_CHAT_SYSTEM_PROMPT

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterLLMProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        resolved_key = api_key or settings.OPENROUTER_API_KEY
        if not resolved_key:
            raise LLMProviderError(
                "OPENROUTER_API_KEY is not set. Configure it in the environment "
                "(see .env.example) before using the openrouter LLM provider."
            )

        self._client = openai.AsyncOpenAI(
            api_key=resolved_key,
            base_url=_OPENROUTER_BASE_URL,
        )
        self._model = model or settings.LLM_MODEL

    async def extract_financial_json(self, normalized_text: str, document_type: str) -> dict:
        user_message = (
            f"document_type: {document_type}\n\n"
            f"--- BEGIN DOCUMENT TEXT ---\n{normalized_text}\n--- END DOCUMENT TEXT ---"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
        except openai.AuthenticationError as exc:
            raise LLMProviderError(
                f"OpenRouter authentication failed (invalid or missing OPENROUTER_API_KEY): {exc}"
            ) from exc
        except openai.PermissionDeniedError as exc:
            raise LLMProviderError(
                f"OpenRouter denied access to model '{self._model}': {exc}"
            ) from exc
        except openai.RateLimitError as exc:
            raise LLMProviderError(f"OpenRouter rate limit exceeded: {exc}") from exc
        except openai.APITimeoutError as exc:
            raise LLMProviderError(f"OpenRouter request timed out: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMProviderError(f"Could not reach OpenRouter (network error): {exc}") from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError(
                f"OpenRouter returned an error (status {exc.status_code}): {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMProviderError(f"OpenRouter request failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        raw_text = (choice.message.content if choice and choice.message else "") or ""
        raw_text = raw_text.strip()

        if not raw_text:
            raise LLMProviderError("OpenRouter returned an empty response.")

        return self._parse_json(raw_text)

    async def answer_financial_question(
        self,
        message: str,
        financial_profile: dict,
        report: dict | None,
        conversation_history: list[dict],
    ) -> str:
        context = json.dumps(
            {"financial_profile": financial_profile, "latest_report": report},
            default=str,
        )
        messages = [{"role": "system", "content": FINANCIAL_CHAT_SYSTEM_PROMPT}]
        messages.extend(conversation_history)
        messages.append(
            {
                "role": "user",
                "content": f"Financial context:\n{context}\n\nQuestion: {message}",
            }
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=1024,
                messages=messages,
            )
        except openai.AuthenticationError as exc:
            raise LLMProviderError(
                f"OpenRouter authentication failed (invalid or missing OPENROUTER_API_KEY): {exc}"
            ) from exc
        except openai.PermissionDeniedError as exc:
            raise LLMProviderError(
                f"OpenRouter denied access to model '{self._model}': {exc}"
            ) from exc
        except openai.RateLimitError as exc:
            raise LLMProviderError(f"OpenRouter rate limit exceeded: {exc}") from exc
        except openai.APITimeoutError as exc:
            raise LLMProviderError(f"OpenRouter request timed out: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMProviderError(f"Could not reach OpenRouter (network error): {exc}") from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError(
                f"OpenRouter returned an error (status {exc.status_code}): {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMProviderError(f"OpenRouter request failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        reply = (choice.message.content if choice and choice.message else "") or ""
        reply = reply.strip()
        if not reply:
            raise LLMProviderError("OpenRouter returned an empty response.")
        return reply

    @staticmethod
    def _parse_json(raw_text: str) -> dict:
        # Defensive: strip accidental markdown fences even though the prompt
        # forbids them, since LLM output is never fully deterministic.
        cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(f"LLM did not return valid JSON: {exc}") from exc
