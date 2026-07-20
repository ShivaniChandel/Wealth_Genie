"""
AICFOAgent — deterministic synthesis of specialist agent outputs. Commit 2 scope.

Per 08_AI_AGENT_ARCHITECTURE.md, the AI CFO is a synthesiser, not an
orchestrator: it does NOT call, trigger, or duplicate the Debt/Savings/Budget
agents' logic. It is constructed directly from their already-computed
outputs (DebtAnalysisResult, SavingsAnalysisResult, BudgetAnalysisResult) and
only combines/derives a report from those values.

All deduction thresholds mirror the thresholds already used by the
specialist agents (DebtAgent._HIGH_DTI_THRESHOLD,
DebtAgent._HIGH_UTILIZATION_THRESHOLD, SavingsAgent._MIN_EMERGENCY_FUND_MONTHS,
SavingsAgent._LOW_SAVINGS_RATE_THRESHOLD) so the AI CFO never introduces new
judgment calls — it reads and reacts to values the specialists already flag.

Missing (None) values never produce a deduction and never raise.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app.schemas_ext.ai_cfo_analysis import AICFOAnalysisResult
from app.schemas_ext.budget_analysis import BudgetAnalysisResult
from app.schemas_ext.debt_analysis import DebtAnalysisResult
from app.schemas_ext.financial import Recommendation, RecommendationPriority
from app.schemas_ext.savings_analysis import SavingsAnalysisResult

# Deduction thresholds — match the specialist agents' existing thresholds
# (DebtAgent / SavingsAgent) rather than introducing new judgment calls.
_HIGH_DTI_THRESHOLD = Decimal("0.40")
_HIGH_UTILIZATION_THRESHOLD = Decimal("80")
_MIN_EMERGENCY_FUND_MONTHS = Decimal("3")
_LOW_SAVINGS_RATE_THRESHOLD = Decimal("20")

_HIGH_DTI_DEDUCTION = 25
_HIGH_UTILIZATION_DEDUCTION = 20
_LOW_EMERGENCY_FUND_DEDUCTION = 20
_LOW_SAVINGS_RATE_DEDUCTION = 10
_EXPENSES_EXCEED_INCOME_DEDUCTION = 25
_UNCATEGORIZED_SPENDING_DEDUCTION = 10

_MAX_SCORE = 100
_MIN_SCORE = 0

_PRIORITY_ORDER = {
    RecommendationPriority.high: 0,
    RecommendationPriority.medium: 1,
    RecommendationPriority.low: 2,
}


class AICFOAgent:
    def __init__(
        self,
        debt_analysis: DebtAnalysisResult,
        savings_analysis: SavingsAnalysisResult,
        budget_analysis: BudgetAnalysisResult,
    ):
        self._debt_analysis = debt_analysis
        self._savings_analysis = savings_analysis
        self._budget_analysis = budget_analysis

    def analyze(self) -> AICFOAnalysisResult:
        score = self._compute_health_score()
        recommendations = self._combine_recommendations()
        priority_recommendations = self._order_by_priority(recommendations)

        return AICFOAnalysisResult(
            executive_summary=self._build_executive_summary(
                score, priority_recommendations
            ),
            overall_financial_health_score=score,
            debt_analysis=self._debt_analysis,
            savings_analysis=self._savings_analysis,
            budget_analysis=self._budget_analysis,
            priority_recommendations=priority_recommendations,
            recommendations=recommendations,
        )

    # ---- health score ----

    def _compute_health_score(self) -> int:
        score = _MAX_SCORE
        score -= self._dti_deduction()
        score -= self._utilization_deduction()
        score -= self._emergency_fund_deduction()
        score -= self._savings_rate_deduction()
        score -= self._expenses_exceed_income_deduction()
        score -= self._uncategorized_spending_deduction()
        return max(_MIN_SCORE, min(_MAX_SCORE, score))

    def _dti_deduction(self) -> int:
        dti: Optional[Decimal] = self._debt_analysis.debt_to_income_ratio
        if dti is not None and dti > _HIGH_DTI_THRESHOLD:
            return _HIGH_DTI_DEDUCTION
        return 0

    def _utilization_deduction(self) -> int:
        utilization: Optional[Decimal] = self._debt_analysis.credit_utilization_percent
        if utilization is not None and utilization >= _HIGH_UTILIZATION_THRESHOLD:
            return _HIGH_UTILIZATION_DEDUCTION
        return 0

    def _emergency_fund_deduction(self) -> int:
        months: Optional[Decimal] = self._savings_analysis.emergency_fund_months
        if months is not None and months < _MIN_EMERGENCY_FUND_MONTHS:
            return _LOW_EMERGENCY_FUND_DEDUCTION
        return 0

    def _savings_rate_deduction(self) -> int:
        rate: Optional[Decimal] = self._savings_analysis.savings_rate_percent
        if rate is not None and rate <= _LOW_SAVINGS_RATE_THRESHOLD:
            return _LOW_SAVINGS_RATE_DEDUCTION
        return 0

    def _expenses_exceed_income_deduction(self) -> int:
        income: Optional[Decimal] = self._budget_analysis.monthly_income
        expenses: Optional[Decimal] = self._budget_analysis.monthly_expenses
        if income is not None and expenses is not None and expenses > income:
            return _EXPENSES_EXCEED_INCOME_DEDUCTION
        return 0

    def _uncategorized_spending_deduction(self) -> int:
        uncategorized: Decimal = self._budget_analysis.uncategorized_debit_spending
        if uncategorized is not None and uncategorized > 0:
            return _UNCATEGORIZED_SPENDING_DEDUCTION
        return 0

    # ---- recommendations ----

    def _combine_recommendations(self) -> List[Recommendation]:
        # debt -> savings -> budget order, per 08_AI_AGENT_ARCHITECTURE.md
        # agent execution order. Reuses the specialists' Recommendation
        # objects as-is (no duplication or mutation).
        return [
            *self._debt_analysis.recommendations,
            *self._savings_analysis.recommendations,
            *self._budget_analysis.recommendations,
        ]

    @staticmethod
    def _order_by_priority(
        recommendations: List[Recommendation],
    ) -> List[Recommendation]:
        return sorted(
            recommendations,
            key=lambda rec: _PRIORITY_ORDER[rec.priority],
        )

    # ---- executive summary (deterministic, no LLM call) ----

    @staticmethod
    def _build_executive_summary(
        score: int, priority_recommendations: List[Recommendation]
    ) -> str:
        if score >= 80:
            health = "in excellent shape"
        elif score >= 60:
            health = "in good shape with some areas to improve"
        elif score >= 40:
            health = "showing signs of financial strain"
        else:
            health = "in need of urgent attention"

        summary = (
            f"Your overall financial health score is {score}/100, "
            f"indicating your finances are {health}."
        )

        if priority_recommendations:
            summary += f" Top priority: {priority_recommendations[0].title}."

        return summary
