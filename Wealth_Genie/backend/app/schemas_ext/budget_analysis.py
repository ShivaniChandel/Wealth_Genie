"""
Budget Agent output schema — Milestone 6 scope only.

The Budget Agent reads normalized UniversalFinancialProfile.transactions and
.summary. All monetary and calculated fields are Decimal-backed. Values that
cannot be computed remain None rather than being represented as zero.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas_ext.financial import Recommendation


class CategorySpend(BaseModel):
    """Debit spending observed for one extractor-provided transaction category."""
    model_config = ConfigDict(extra="ignore")

    category: str
    amount: Decimal = Decimal("0")
    percent_of_categorized_debit_spending: Optional[Decimal] = None


class BudgetAnalysisResult(BaseModel):
    """
    Root output of BudgetAgent.analyze(). Persisted as `content` in the
    `recommendations` table with agent = 'budget_agent'.
    """
    model_config = ConfigDict(extra="ignore")

    total_debit_spending: Decimal = Decimal("0")
    categorized_debit_spending: Decimal = Decimal("0")
    uncategorized_debit_spending: Decimal = Decimal("0")
    spending_by_category: List[CategorySpend] = Field(default_factory=list)

    monthly_income: Optional[Decimal] = None
    monthly_expenses: Optional[Decimal] = None
    expense_to_income_ratio: Optional[Decimal] = None

    largest_spending_category: Optional[str] = None
    largest_spending_category_percent: Optional[Decimal] = None

    recommendations: List[Recommendation] = Field(default_factory=list)
    has_transaction_data: bool = False
