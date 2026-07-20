"""
Debt Agent output schema — Milestone 4 scope only.

Per 08_AI_AGENT_ARCHITECTURE.md: reads UniversalFinancialProfile.loans /
.credit_cards / .summary only. All monetary/rate fields are Decimal-backed
(11_DEVELOPMENT_GUIDELINES.md rule #2). Fields that cannot be computed
(missing income, no credit limit data) are Optional/None, never defaulted
to 0, since 0 would misrepresent "unknown" as "computed zero".

Explicitly OUT of scope for Milestone 4 (deferred):
- avalanche/snowball payoff ordering
- payoff strategy selection
- amortization/payoff timeline projections
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas_ext.financial import Recommendation


class LiabilityType(str, Enum):
    loan = "loan"
    credit_card = "credit_card"


class HighRiskReason(str, Enum):
    high_interest_rate = "high_interest_rate"
    minimum_payment_trap = "minimum_payment_trap"
    high_utilization = "high_utilization"


class HighRiskItem(BaseModel):
    """A single liability flagged by one deterministic risk rule."""
    model_config = ConfigDict(extra="ignore")

    liability_type: LiabilityType
    id: Optional[str] = None
    reason: HighRiskReason


class DebtAnalysisResult(BaseModel):
    """
    Root output of DebtAgent.analyze(). Persisted as `content` in the
    `recommendations` table with agent = 'debt_agent'.
    """
    model_config = ConfigDict(extra="ignore")

    total_outstanding_debt: Decimal = Decimal("0")
    total_loan_debt: Decimal = Decimal("0")
    total_credit_card_debt: Decimal = Decimal("0")

    # None when total_monthly_income is missing or zero — cannot divide.
    debt_to_income_ratio: Optional[Decimal] = None

    # None when no credit card has both outstanding_balance and credit_limit.
    # Σ outstanding_balance / Σ credit_limit across all cards, as a percent (0-100).
    credit_utilization_percent: Optional[Decimal] = None

    high_risk_items: List[HighRiskItem] = Field(default_factory=list)

    recommendations: List[Recommendation] = Field(default_factory=list)

    has_debt: bool = False