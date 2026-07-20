"""
Test-first contract for AICFOAgent — Commit 1 scope only.

AICFOAgent itself is NOT implemented in this commit (see PROJECT_CONTEXT.md /
08_AI_AGENT_ARCHITECTURE.md: "The AI CFO does NOT orchestrate, call, or
trigger the specialist agents" — it only reads their already-computed
outputs). This file defines the expected behaviour ahead of that
implementation.

Per 08_AI_AGENT_ARCHITECTURE.md and the DebtAgent/SavingsAgent/BudgetAgent
pattern, AICFOAgent is expected to be constructed directly from the three
specialist agents' outputs (not the raw UniversalFinancialProfile, and not
by calling the specialist agents itself):

    AICFOAgent(
        debt_analysis=DebtAnalysisResult(...),
        savings_analysis=SavingsAnalysisResult(...),
        budget_analysis=BudgetAnalysisResult(...),
    ).analyze() -> AICFOAnalysisResult

`pytest.importorskip` is used so this file collects successfully (no
ImportError) even though `app.services.agents.ai_cfo_agent` does not exist
yet — tests are skipped, not errored, until that module is added in a later
commit.
"""
from decimal import Decimal

import pytest

from app.schemas_ext.budget_analysis import BudgetAnalysisResult
from app.schemas_ext.debt_analysis import DebtAnalysisResult
from app.schemas_ext.financial import (
    Recommendation,
    RecommendationAgent,
    RecommendationPriority,
)
from app.schemas_ext.savings_analysis import SavingsAnalysisResult

ai_cfo_agent = pytest.importorskip(
    "app.services.agents.ai_cfo_agent",
    reason="AICFOAgent is implemented in a later commit (Commit 1 is schema-only).",
)
AICFOAgent = ai_cfo_agent.AICFOAgent


def _debt(**kwargs) -> DebtAnalysisResult:
    return DebtAnalysisResult.model_validate(kwargs)


def _savings(**kwargs) -> SavingsAnalysisResult:
    return SavingsAnalysisResult.model_validate(kwargs)


def _budget(**kwargs) -> BudgetAnalysisResult:
    return BudgetAnalysisResult.model_validate(kwargs)


def _rec(agent: RecommendationAgent, title: str, priority=RecommendationPriority.medium) -> Recommendation:
    return Recommendation(agent=agent, priority=priority, title=title, detail=title)


# ---------------------------------------------------------------------------
# Health score deductions
# ---------------------------------------------------------------------------


def test_perfect_inputs_yield_full_score():
    result = AICFOAgent(
        debt_analysis=_debt(debt_to_income_ratio=Decimal("0.1")),
        savings_analysis=_savings(
            savings_rate_percent=Decimal("30"), emergency_fund_months=Decimal("6")
        ),
        budget_analysis=_budget(
            monthly_income=Decimal("5000"),
            monthly_expenses=Decimal("3000"),
            uncategorized_debit_spending=Decimal("0"),
        ),
    ).analyze()

    assert result.overall_financial_health_score == 100


def test_high_dti_deducts_25():
    result = AICFOAgent(
        debt_analysis=_debt(debt_to_income_ratio=Decimal("0.45")),
        savings_analysis=_savings(),
        budget_analysis=_budget(),
    ).analyze()

    assert result.overall_financial_health_score == 75


def test_high_credit_utilization_deducts_20():
    result = AICFOAgent(
        debt_analysis=_debt(credit_utilization_percent=Decimal("85")),
        savings_analysis=_savings(),
        budget_analysis=_budget(),
    ).analyze()

    assert result.overall_financial_health_score == 80


def test_low_emergency_fund_deducts_20():
    result = AICFOAgent(
        debt_analysis=_debt(),
        savings_analysis=_savings(emergency_fund_months=Decimal("2")),
        budget_analysis=_budget(),
    ).analyze()

    assert result.overall_financial_health_score == 80


def test_low_savings_rate_deducts_10():
    result = AICFOAgent(
        debt_analysis=_debt(),
        savings_analysis=_savings(savings_rate_percent=Decimal("15")),
        budget_analysis=_budget(),
    ).analyze()

    assert result.overall_financial_health_score == 90


def test_expenses_exceeding_income_deducts_25():
    result = AICFOAgent(
        debt_analysis=_debt(),
        savings_analysis=_savings(),
        budget_analysis=_budget(
            monthly_income=Decimal("4000"), monthly_expenses=Decimal("4500")
        ),
    ).analyze()

    assert result.overall_financial_health_score == 75


def test_uncategorized_spending_deducts_10():
    result = AICFOAgent(
        debt_analysis=_debt(),
        savings_analysis=_savings(),
        budget_analysis=_budget(uncategorized_debit_spending=Decimal("500")),
    ).analyze()

    assert result.overall_financial_health_score == 90


def test_multiple_deductions_stack():
    result = AICFOAgent(
        debt_analysis=_debt(
            debt_to_income_ratio=Decimal("0.5"),
            credit_utilization_percent=Decimal("90"),
        ),
        savings_analysis=_savings(
            emergency_fund_months=Decimal("1"), savings_rate_percent=Decimal("5")
        ),
        budget_analysis=_budget(
            monthly_income=Decimal("3000"),
            monthly_expenses=Decimal("3500"),
            uncategorized_debit_spending=Decimal("100"),
        ),
    ).analyze()

    # 100 - 25 (dti) - 20 (utilization) - 20 (emergency fund) - 10 (savings rate)
    # - 25 (expenses > income) - 10 (uncategorized) = -10 -> clamped to 0
    assert result.overall_financial_health_score == 0


def test_score_is_clamped_to_zero_minimum():
    result = AICFOAgent(
        debt_analysis=_debt(
            debt_to_income_ratio=Decimal("0.9"),
            credit_utilization_percent=Decimal("99"),
        ),
        savings_analysis=_savings(
            emergency_fund_months=Decimal("0"), savings_rate_percent=Decimal("0")
        ),
        budget_analysis=_budget(
            monthly_income=Decimal("1000"),
            monthly_expenses=Decimal("9000"),
            uncategorized_debit_spending=Decimal("100"),
        ),
    ).analyze()

    assert result.overall_financial_health_score >= 0


def test_score_is_clamped_to_hundred_maximum():
    # No agent output should ever push the score above 100 even if some
    # hypothetical future rule produced a bonus; verifies clamping logic
    # exists on the upper bound too.
    result = AICFOAgent(
        debt_analysis=_debt(),
        savings_analysis=_savings(),
        budget_analysis=_budget(),
    ).analyze()

    assert result.overall_financial_health_score <= 100


# ---------------------------------------------------------------------------
# Unknown / missing values produce no deduction
# ---------------------------------------------------------------------------


def test_missing_values_produce_no_deduction_and_never_raise():
    result = AICFOAgent(
        debt_analysis=_debt(),
        savings_analysis=_savings(),
        budget_analysis=_budget(),
    ).analyze()

    assert result.overall_financial_health_score == 100


def test_missing_values_never_throw_with_partial_data():
    # Only some fields populated; the rest are None/default. Must not raise.
    result = AICFOAgent(
        debt_analysis=_debt(debt_to_income_ratio=None, credit_utilization_percent=None),
        savings_analysis=_savings(emergency_fund_months=None, savings_rate_percent=None),
        budget_analysis=_budget(monthly_income=None, monthly_expenses=None),
    ).analyze()

    assert result.overall_financial_health_score == 100


# ---------------------------------------------------------------------------
# Recommendation combination / ordering
# ---------------------------------------------------------------------------


def test_recommendations_preserve_source_agent_order():
    debt_rec = _rec(RecommendationAgent.debt_agent, "Debt issue")
    savings_rec = _rec(RecommendationAgent.savings_agent, "Savings issue")
    budget_rec = _rec(RecommendationAgent.budget_agent, "Budget issue")

    result = AICFOAgent(
        debt_analysis=_debt(recommendations=[debt_rec]),
        savings_analysis=_savings(recommendations=[savings_rec]),
        budget_analysis=_budget(recommendations=[budget_rec]),
    ).analyze()

    assert [r.title for r in result.recommendations] == [
        "Debt issue",
        "Savings issue",
        "Budget issue",
    ]


def test_recommendations_are_not_duplicated_or_mutated():
    debt_rec = _rec(RecommendationAgent.debt_agent, "Debt issue")

    result = AICFOAgent(
        debt_analysis=_debt(recommendations=[debt_rec]),
        savings_analysis=_savings(recommendations=[]),
        budget_analysis=_budget(recommendations=[]),
    ).analyze()

    assert result.recommendations == [debt_rec]


def test_priority_recommendations_are_ordered_high_before_medium_before_low():
    low_rec = _rec(RecommendationAgent.budget_agent, "Low issue", RecommendationPriority.low)
    high_rec = _rec(RecommendationAgent.debt_agent, "High issue", RecommendationPriority.high)
    medium_rec = _rec(RecommendationAgent.savings_agent, "Medium issue", RecommendationPriority.medium)

    result = AICFOAgent(
        debt_analysis=_debt(recommendations=[high_rec]),
        savings_analysis=_savings(recommendations=[medium_rec]),
        budget_analysis=_budget(recommendations=[low_rec]),
    ).analyze()

    assert [r.title for r in result.priority_recommendations] == [
        "High issue",
        "Medium issue",
        "Low issue",
    ]


def test_no_recommendations_when_all_agents_have_none():
    result = AICFOAgent(
        debt_analysis=_debt(recommendations=[]),
        savings_analysis=_savings(recommendations=[]),
        budget_analysis=_budget(recommendations=[]),
    ).analyze()

    assert result.recommendations == []
    assert result.priority_recommendations == []


# ---------------------------------------------------------------------------
# Executive summary generation is deterministic (no LLM call)
# ---------------------------------------------------------------------------


def test_executive_summary_is_deterministic_for_identical_inputs():
    debt = _debt(debt_to_income_ratio=Decimal("0.5"))
    savings = _savings(savings_rate_percent=Decimal("10"))
    budget = _budget(monthly_income=Decimal("4000"), monthly_expenses=Decimal("4500"))

    result_a = AICFOAgent(
        debt_analysis=debt, savings_analysis=savings, budget_analysis=budget
    ).analyze()
    result_b = AICFOAgent(
        debt_analysis=debt, savings_analysis=savings, budget_analysis=budget
    ).analyze()

    assert result_a.executive_summary == result_b.executive_summary
    assert isinstance(result_a.executive_summary, str)
    assert result_a.executive_summary != ""


def test_executive_summary_reflects_score_without_new_calculations():
    # The AI CFO must not compute any new financial metric to build the
    # summary — only read the already-computed score/fields.
    good = AICFOAgent(
        debt_analysis=_debt(debt_to_income_ratio=Decimal("0.1")),
        savings_analysis=_savings(savings_rate_percent=Decimal("30")),
        budget_analysis=_budget(monthly_income=Decimal("5000"), monthly_expenses=Decimal("3000")),
    ).analyze()

    poor = AICFOAgent(
        debt_analysis=_debt(debt_to_income_ratio=Decimal("0.9")),
        savings_analysis=_savings(savings_rate_percent=Decimal("0")),
        budget_analysis=_budget(monthly_income=Decimal("1000"), monthly_expenses=Decimal("9000")),
    ).analyze()

    assert good.executive_summary != poor.executive_summary
