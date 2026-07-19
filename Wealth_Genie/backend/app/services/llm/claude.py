"""
Claude (Anthropic) implementation of LLMProvider.

This is the only file in the codebase permitted to import the `anthropic`
SDK. Everything else talks to `LLMProvider` (base.py).
"""
from __future__ import annotations

import json
import re

from app.config import settings
from app.services.llm.base import LLMProvider, LLMProviderError

_EXTRACTION_SYSTEM_PROMPT = """You are a deterministic financial document structuring \
engine. You convert normalized financial-document text into a single JSON object \
matching an exact schema. You NEVER invent values that are not present in the source \
text. Any field you cannot find must be omitted or left as null/empty, never guessed.

Respond with JSON ONLY. No prose, no markdown code fences, no explanations.

Schema (top-level keys, all required, unknown sub-fields may be omitted):
{
  "user": {"id": null, "name": null, "email": null},
  "accounts": [{"account_id": "", "bank_name": "", "account_type": "savings|current|salary",
                "currency": "", "opening_balance": 0, "closing_balance": 0,
                "statement_period_start": "YYYY-MM-DD", "statement_period_end": "YYYY-MM-DD"}],
  "transactions": [{"transaction_id": "", "account_id": "", "date": "YYYY-MM-DD",
                     "description": "", "amount": 0, "type": "credit|debit", "category": ""}],
  "loans": [{"loan_id": "", "lender": "", "loan_type": "home|personal|auto|education|other",
             "principal": 0, "outstanding_balance": 0, "interest_rate": 0, "emi": 0,
             "tenure_remaining_months": 0}],
  "credit_cards": [{"card_id": "", "issuer": "", "credit_limit": 0, "outstanding_balance": 0,
                     "minimum_due": 0, "due_date": "YYYY-MM-DD", "interest_rate": 0}],
  "summary": {"total_monthly_income": 0, "total_monthly_expenses": 0, "total_debt": 0,
              "total_savings": 0, "net_worth_estimate": 0, "savings_rate_percent": 0},
  "recommendations": []
}

The document_type hint tells you what kind of document this is, which sections are
most likely to be populated (e.g. salary_slip -> summary.total_monthly_income and
possibly one transaction; bank_statement -> accounts + transactions; credit_card ->
credit_cards; loan -> loans). Do not force-populate sections irrelevant to the
document type."""


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
            system=_EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

        return self._parse_json(raw_text)

    @staticmethod
    def _parse_json(raw_text: str) -> dict:
        # Defensive: strip accidental markdown fences even though the prompt
        # forbids them, since LLM output is never fully deterministic.
        cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(f"LLM did not return valid JSON: {exc}") from exc
