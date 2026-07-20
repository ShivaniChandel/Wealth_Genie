from decimal import Decimal

from app.schemas_ext.financial import UniversalFinancialProfile
from app.services.agents.savings_agent import SavingsAgent


def _profile(**kwargs) -> UniversalFinancialProfile:
    return UniversalFinancialProfile.model_validate(kwargs)


def test_no_savings_data_returns_zeroed_result():
    result = SavingsAgent(_profile(accounts=[], summary={})).analyze()

    assert result.has_savings_data is False
    assert result.total_savings == Decimal("0")
    assert result.savings_rate_percent is None
    assert result.emergency_fund_months is None
    assert result.recommendations == []


def test_total_savings_uses_summary_value():
    result = SavingsAgent(
        _profile(
            accounts=[
                {"account_type": "savings", "closing_balance": 1000},
                {"account_type": "savings", "closing_balance": 2000},
            ],
            summary={"total_savings": 5000},
        )
    ).analyze()

    assert result.total_savings == Decimal("5000")


def test_total_savings_falls_back_to_savings_account_balances_only():
    result = SavingsAgent(
        _profile(
            accounts=[
                {"account_type": "savings", "closing_balance": 1000},
                {"account_type": "salary", "closing_balance": 9000},
                {"account_type": "current", "closing_balance": 4000},
            ],
            summary={},
        )
    ).analyze()

    assert result.total_savings == Decimal("1000")
    assert result.has_savings_data is True


def test_savings_rate_is_calculated_from_monthly_summary_values():
    result = SavingsAgent(
        _profile(summary={"total_monthly_income": 10000, "total_monthly_expenses": 8000})
    ).analyze()

    assert result.savings_rate_percent == Decimal("20")


def test_savings_rate_uses_extracted_value_when_monthly_values_are_incomplete():
    result = SavingsAgent(_profile(summary={"savings_rate_percent": 15})).analyze()

    assert result.savings_rate_percent == Decimal("15")


def test_emergency_fund_thresholds_are_deterministic():
    below_three = SavingsAgent(
        _profile(summary={"total_savings": 2000, "total_monthly_expenses": 1000})
    ).analyze()
    between_three_and_six = SavingsAgent(
        _profile(summary={"total_savings": 4000, "total_monthly_expenses": 1000})
    ).analyze()
    six_or_more = SavingsAgent(
        _profile(summary={"total_savings": 6000, "total_monthly_expenses": 1000})
    ).analyze()

    assert below_three.emergency_fund_months == Decimal("2")
    assert any(r.priority.value == "high" for r in below_three.recommendations)
    assert between_three_and_six.emergency_fund_months == Decimal("4")
    assert any(r.priority.value == "medium" for r in between_three_and_six.recommendations)
    assert six_or_more.emergency_fund_months == Decimal("6")
    assert six_or_more.recommendations == []


def test_low_savings_rate_at_or_below_twenty_percent_is_flagged():
    low_rate = SavingsAgent(
        _profile(summary={"total_monthly_income": 10000, "total_monthly_expenses": 8000})
    ).analyze()
    healthy_rate = SavingsAgent(
        _profile(summary={"total_monthly_income": 10000, "total_monthly_expenses": 7900})
    ).analyze()

    assert any(r.title == "Savings rate is low" for r in low_rate.recommendations)
    assert all(r.title != "Savings rate is low" for r in healthy_rate.recommendations)


def test_missing_or_zero_income_never_raises():
    missing_income = SavingsAgent(_profile(summary={"total_monthly_expenses": 1000})).analyze()
    zero_income = SavingsAgent(
        _profile(summary={"total_monthly_income": 0, "total_monthly_expenses": 1000})
    ).analyze()

    assert missing_income.savings_rate_percent is None
    assert zero_income.savings_rate_percent is None
