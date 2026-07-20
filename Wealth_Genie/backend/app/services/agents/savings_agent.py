"""
SavingsAgent — deterministic savings analysis. Milestone 5 scope only.

Reads only UniversalFinancialProfile.accounts and .summary. Never touches raw
files, transactions, the extractor, validators, or an LLM provider. All
arithmetic is Decimal-backed (11_DEVELOPMENT_GUIDELINES.md rule #2).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.schemas_ext.financial import (
    Account,
    AccountType,
    Recommendation,
    RecommendationAgent,
    RecommendationPriority,
    UniversalFinancialProfile,
)
from app.schemas_ext.savings_analysis import SavingsAnalysisResult


_LOW_SAVINGS_RATE_THRESHOLD = Decimal("20")  # percent
_MIN_EMERGENCY_FUND_MONTHS = Decimal("3")
_RECOMMENDED_EMERGENCY_FUND_MONTHS = Decimal("6")


class SavingsAgent:
    def __init__(self, profile: UniversalFinancialProfile):
        self._profile = profile

    def analyze(self) -> SavingsAnalysisResult:
        total_savings, has_savings_data = self._total_savings(self._profile.accounts)
        income = self._profile.summary.total_monthly_income
        expenses = self._profile.summary.total_monthly_expenses
        savings_rate = self._compute_savings_rate(income, expenses)
        if savings_rate is None:
            savings_rate = self._profile.summary.savings_rate_percent

        emergency_fund_months = self._compute_emergency_fund_months(
            total_savings, expenses, has_savings_data
        )
        recommended_emergency_fund = (
            expenses * _RECOMMENDED_EMERGENCY_FUND_MONTHS
            if expenses is not None and expenses > 0
            else None
        )
        emergency_fund_gap = (
            max(recommended_emergency_fund - total_savings, Decimal("0"))
            if recommended_emergency_fund is not None and has_savings_data
            else None
        )

        return SavingsAnalysisResult(
            total_savings=total_savings,
            monthly_income=income,
            monthly_expenses=expenses,
            savings_rate_percent=savings_rate,
            emergency_fund_months=emergency_fund_months,
            recommended_emergency_fund=recommended_emergency_fund,
            emergency_fund_gap=emergency_fund_gap,
            recommendations=self._build_recommendations(
                savings_rate, emergency_fund_months
            ),
            has_savings_data=has_savings_data,
        )

    def _total_savings(self, accounts: list[Account]) -> tuple[Decimal, bool]:
        summary_savings = self._profile.summary.total_savings
        if summary_savings is not None:
            return summary_savings, True

        balances = [
            account.closing_balance
            for account in accounts
            if account.account_type == AccountType.savings
            and account.closing_balance is not None
        ]
        return sum(balances, Decimal("0")), bool(balances)

    @staticmethod
    def _compute_savings_rate(
        income: Optional[Decimal], expenses: Optional[Decimal]
    ) -> Optional[Decimal]:
        if income is None or income == 0 or expenses is None:
            return None
        return ((income - expenses) / income) * Decimal("100")

    @staticmethod
    def _compute_emergency_fund_months(
        total_savings: Decimal,
        expenses: Optional[Decimal],
        has_savings_data: bool,
    ) -> Optional[Decimal]:
        if not has_savings_data or expenses is None or expenses <= 0:
            return None
        return total_savings / expenses

    @staticmethod
    def _build_recommendations(
        savings_rate: Optional[Decimal], emergency_fund_months: Optional[Decimal]
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        if emergency_fund_months is not None:
            if emergency_fund_months < _MIN_EMERGENCY_FUND_MONTHS:
                recommendations.append(
                    Recommendation(
                        agent=RecommendationAgent.savings_agent,
                        priority=RecommendationPriority.high,
                        title="Emergency fund is below three months of expenses",
                        detail=(
                            f"Current savings cover {emergency_fund_months:.1f} months "
                            "of expenses. Build an emergency fund covering at least "
                            "three months of expenses."
                        ),
                    )
                )
            elif emergency_fund_months < _RECOMMENDED_EMERGENCY_FUND_MONTHS:
                recommendations.append(
                    Recommendation(
                        agent=RecommendationAgent.savings_agent,
                        priority=RecommendationPriority.medium,
                        title="Emergency fund is partially funded",
                        detail=(
                            f"Current savings cover {emergency_fund_months:.1f} months "
                            "of expenses. Continue building toward six months of coverage."
                        ),
                    )
                )

        if savings_rate is not None and savings_rate <= _LOW_SAVINGS_RATE_THRESHOLD:
            recommendations.append(
                Recommendation(
                    agent=RecommendationAgent.savings_agent,
                    priority=RecommendationPriority.medium,
                    title="Savings rate is low",
                    detail=(
                        f"Your savings rate is {savings_rate:.1f}%, at or below the "
                        f"{_LOW_SAVINGS_RATE_THRESHOLD:.0f}% target."
                    ),
                )
            )

        return recommendations
