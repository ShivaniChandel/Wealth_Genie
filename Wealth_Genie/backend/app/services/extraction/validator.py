from __future__ import annotations

from pydantic import ValidationError

from app.schemas_ext.financial import UniversalFinancialProfile


class FinancialJsonValidationError(ValueError):
    def __init__(self, validation_error: ValidationError | str):
        if isinstance(validation_error, ValidationError):
            self.validation_error = validation_error
            super().__init__(str(validation_error))
        else:
            self.validation_error = None
            super().__init__(validation_error)


def validate_statement_period(profile: UniversalFinancialProfile) -> None:
    for account in profile.accounts:
        if (
            account.statement_period_start
            and account.statement_period_end
            and account.statement_period_start > account.statement_period_end
        ):
            raise FinancialJsonValidationError(
                "Statement period start cannot be after statement period end."
            )


def validate_balances(profile: UniversalFinancialProfile) -> None:
    for account in profile.accounts:
        if (
            account.opening_balance is not None
            and account.opening_balance < 0
        ):
            raise FinancialJsonValidationError(
                "Opening balance cannot be negative."
            )

        if (
            account.closing_balance is not None
            and account.closing_balance < 0
        ):
            raise FinancialJsonValidationError(
                "Closing balance cannot be negative."
            )


def validate_transactions(profile: UniversalFinancialProfile) -> None:
    account_periods = {
        account.account_id: (
            account.statement_period_start,
            account.statement_period_end,
        )
        for account in profile.accounts
        if account.account_id
    }

    for tx in profile.transactions:
        if tx.amount is not None and tx.amount <= 0:
            raise FinancialJsonValidationError(
                "Transaction amount must be greater than zero."
            )

        if (
            tx.account_id
            and tx.date
            and tx.account_id in account_periods
        ):
            start, end = account_periods[tx.account_id]

            if start and tx.date < start:
                raise FinancialJsonValidationError(
                    "Transaction date is before statement period."
                )

            if end and tx.date > end:
                raise FinancialJsonValidationError(
                    "Transaction date is after statement period."
                )


def validate_summary(profile: UniversalFinancialProfile) -> None:
    rate = profile.summary.savings_rate_percent

    if (
        rate is not None
        and (rate < -100 or rate > 100)
    ):
        raise FinancialJsonValidationError(
            "Savings rate must be between -100 and 100."
        )


def validate_business_rules(profile: UniversalFinancialProfile) -> None:
    validate_statement_period(profile)
    validate_balances(profile)
    validate_transactions(profile)
    validate_summary(profile)

def validate_financial_json(data: dict) -> UniversalFinancialProfile:
    """
    Validate the LLM JSON using Pydantic, then run deterministic business rules.
    """

    try:
        profile = UniversalFinancialProfile.model_validate(data)
    except ValidationError as exc:
        raise FinancialJsonValidationError(exc) from exc

    validate_business_rules(profile)

    return profile