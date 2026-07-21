from __future__ import annotations

import json
import re

from app.config import settings
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.prompts import EXTRACTION_SYSTEM_PROMPT, FINANCIAL_CHAT_SYSTEM_PROMPT


class ClaudeLLMProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        # Imported lazily so environments without the anthropic package
        # installed (e.g. pure extraction unit tests with a mocked provider)
        # don't fail at import time.
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self._model = model or settings.LLM_MODEL

    async def extract_financial_json(self, normalized_text: str, document_type: str) -> dict:
        user_message = (
            f"document_type: {document_type}\n\n"
            f"--- BEGIN DOCUMENT TEXT ---\n{normalized_text}\n--- END DOCUMENT TEXT ---"
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

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
        messages = list(conversation_history)
        messages.append(
            {
                "role": "user",
                "content": f"Financial context:\n{context}\n\nQuestion: {message}",
            }
        )
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=FINANCIAL_CHAT_SYSTEM_PROMPT,
            messages=messages,
        )
        reply = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()
        if not reply:
            raise LLMProviderError("Claude returned an empty response.")
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
