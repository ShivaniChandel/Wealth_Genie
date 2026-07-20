"""
BudgetAgent — deterministic spending analysis. Milestone 6 scope only.

Reads only UniversalFinancialProfile.transactions and .summary. Never touches
raw files, the extractor, validators, or any LLM provider. All arithmetic is
Decimal-backed (11_DEVELOPMENT_GUIDELINES.md rule #2).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.schemas_ext.budget_analysis import BudgetAnalysisResult, CategorySpend
from app.schemas_ext.financial import (
    Recommendation,
    RecommendationAgent,
    RecommendationPriority,
    Transaction,
    TransactionType,
    UniversalFinancialProfile,
)


class BudgetAgent:
    def __init__(self, profile: UniversalFinancialProfile):
        self._profile = profile

    def analyze(self) -> BudgetAnalysisResult:
        categorized_spending, uncategorized_spending = self._spending_by_category(
            self._profile.transactions
        )
        categorized_total = sum(categorized_spending.values(), Decimal("0"))
        total_debit_spending = categorized_total + uncategorized_spending
        category_results = self._category_results(categorized_spending, categorized_total)
        largest_category, largest_category_percent = self._largest_category(category_results)

        income = self._profile.summary.total_monthly_income
        expenses = self._profile.summary.total_monthly_expenses
        expense_to_income_ratio = self._compute_expense_to_income_ratio(income, expenses)

        return BudgetAnalysisResult(
            total_debit_spending=total_debit_spending,
            categorized_debit_spending=categorized_total,
            uncategorized_debit_spending=uncategorized_spending,
            spending_by_category=category_results,
            monthly_income=income,
            monthly_expenses=expenses,
            expense_to_income_ratio=expense_to_income_ratio,
            largest_spending_category=largest_category,
            largest_spending_category_percent=largest_category_percent,
            recommendations=self._build_recommendations(
                income, expenses, uncategorized_spending
            ),
            has_transaction_data=bool(self._profile.transactions),
        )

    @staticmethod
    def _spending_by_category(
        transactions: list[Transaction],
    ) -> tuple[dict[str, Decimal], Decimal]:
        categorized: dict[str, Decimal] = {}
        uncategorized = Decimal("0")

        for transaction in transactions:
            if transaction.type != TransactionType.debit or transaction.amount is None:
                continue

            category = transaction.category.strip() if transaction.category else ""
            if not category:
                uncategorized += transaction.amount
                continue
            categorized[category] = categorized.get(category, Decimal("0")) + transaction.amount

        return categorized, uncategorized

    @staticmethod
    def _category_results(
        categorized_spending: dict[str, Decimal], categorized_total: Decimal
    ) -> list[CategorySpend]:
        return [
            CategorySpend(
                category=category,
                amount=amount,
                percent_of_categorized_debit_spending=(amount / categorized_total)
                * Decimal("100"),
            )
            for category, amount in categorized_spending.items()
        ]

    @staticmethod
    def _largest_category(
        categories: list[CategorySpend],
    ) -> tuple[Optional[str], Optional[Decimal]]:
        if not categories:
            return None, None

        largest = max(categories, key=lambda item: item.amount)
        return largest.category, largest.percent_of_categorized_debit_spending

    @staticmethod
    def _compute_expense_to_income_ratio(
        income: Optional[Decimal], expenses: Optional[Decimal]
    ) -> Optional[Decimal]:
        if income is None or income == 0 or expenses is None:
            return None
        return expenses / income

    @staticmethod
    def _build_recommendations(
        income: Optional[Decimal], expenses: Optional[Decimal], uncategorized_spending: Decimal
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        if income is not None and expenses is not None and expenses > income:
            recommendations.append(
                Recommendation(
                    agent=RecommendationAgent.budget_agent,
                    priority=RecommendationPriority.high,
                    title="Monthly expenses exceed income",
                    detail=(
                        f"Monthly expenses are {expenses:.1f}, exceeding monthly income "
                        f"of {income:.1f}."
                    ),
                )
            )

        if uncategorized_spending > 0:
            recommendations.append(
                Recommendation(
                    agent=RecommendationAgent.budget_agent,
                    priority=RecommendationPriority.medium,
                    title="Some spending is uncategorized",
                    detail=(
                        f"{uncategorized_spending:.1f} of debit spending has no category, "
                        "which limits reliable budget tracking."
                    ),
                )
            )

        return recommendations
