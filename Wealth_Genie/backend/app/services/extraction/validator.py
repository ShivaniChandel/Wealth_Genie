from __future__ import annotations

from pydantic import ValidationError

from app.schemas_ext.financial import UniversalFinancialProfile


class FinancialJsonValidationError(ValueError):
    def __init__(self, validation_error: ValidationError):
        self.validation_error = validation_error
        super().__init__(str(validation_error))


def validate_financial_json(data: dict) -> UniversalFinancialProfile:
    """
    Validates a raw dict (typically produced by an LLMProvider) against the
    Universal Financial JSON schema. Raises FinancialJsonValidationError with
    the full pydantic error detail on failure — callers must not silently
    swallow malformed structured output.
    """
    try:
        return UniversalFinancialProfile.model_validate(data)
    except ValidationError as exc:
        raise FinancialJsonValidationError(exc) from exc
