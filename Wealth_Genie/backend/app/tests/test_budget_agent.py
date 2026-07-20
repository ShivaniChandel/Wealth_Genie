from decimal import Decimal

from app.schemas_ext.financial import UniversalFinancialProfile
from app.services.agents.budget_agent import BudgetAgent


def _profile(**kwargs) -> UniversalFinancialProfile:
    return UniversalFinancialProfile.model_validate(kwargs)


def test_no_transactions_returns_zeroed_result():
    result = BudgetAgent(_profile(transactions=[], summary={})).analyze()

    assert result.has_transaction_data is False
    assert result.total_debit_spending == Decimal("0")
    assert result.spending_by_category == []
    assert result.largest_spending_category is None
    assert result.largest_spending_category_percent is None
    assert result.recommendations == []


def test_only_debit_transactions_are_counted_and_grouped_by_category():
    result = BudgetAgent(
        _profile(
            transactions=[
                {"type": "debit", "amount": 250, "category": "food"},
                {"type": "debit", "amount": 150, "category": "food"},
                {"type": "debit", "amount": 100, "category": "transport"},
                {"type": "credit", "amount": 1000, "category": "salary"},
            ],
            summary={},
        )
    ).analyze()

    assert result.total_debit_spending == Decimal("500")
    assert result.categorized_debit_spending == Decimal("500")
    assert [(item.category, item.amount) for item in result.spending_by_category] == [
        ("food", Decimal("400")),
        ("transport", Decimal("100")),
    ]


def test_missing_or_blank_category_is_uncategorized_spending():
    result = BudgetAgent(
        _profile(
            transactions=[
                {"type": "debit", "amount": 100},
                {"type": "debit", "amount": 50, "category": ""},
            ],
            summary={},
        )
    ).analyze()

    assert result.uncategorized_debit_spending == Decimal("150")
    assert result.categorized_debit_spending == Decimal("0")
    assert result.spending_by_category == []
    assert any(r.title == "Some spending is uncategorized" for r in result.recommendations)


def test_largest_category_and_percentage_are_exposed_without_a_recommendation():
    result = BudgetAgent(
        _profile(
            transactions=[
                {"type": "debit", "amount": 600, "category": "housing"},
                {"type": "debit", "amount": 400, "category": "food"},
            ],
            summary={},
        )
    ).analyze()

    assert result.largest_spending_category == "housing"
    assert result.largest_spending_category_percent == Decimal("60")
    assert result.recommendations == []


def test_expenses_exceeding_income_generates_high_priority_recommendation():
    result = BudgetAgent(
        _profile(summary={"total_monthly_income": 5000, "total_monthly_expenses": 6000})
    ).analyze()

    assert result.expense_to_income_ratio == Decimal("1.2")
    assert any(
        r.title == "Monthly expenses exceed income" and r.priority.value == "high"
        for r in result.recommendations
    )


def test_expense_to_income_ratio_is_none_when_income_is_missing_or_zero():
    missing_income = BudgetAgent(_profile(summary={"total_monthly_expenses": 1000})).analyze()
    zero_income = BudgetAgent(
        _profile(summary={"total_monthly_income": 0, "total_monthly_expenses": 1000})
    ).analyze()

    assert missing_income.expense_to_income_ratio is None
    assert zero_income.expense_to_income_ratio is None
