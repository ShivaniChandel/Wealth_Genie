"""
Savings Agent output schema — Milestone 5 scope only.

The Savings Agent reads only UniversalFinancialProfile.accounts and .summary.
All monetary and calculated fields are Decimal-backed. Values that cannot be
computed from the normalized profile remain None rather than being represented
as zero.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas_ext.financial import Recommendation


class SavingsAnalysisResult(BaseModel):
    """
    Root output of SavingsAgent.analyze(). Persisted as `content` in the
    `recommendations` table with agent = 'savings_agent'.
    """
    model_config = ConfigDict(extra="ignore")

    total_savings: Decimal = Decimal("0")

    # None when normalized summary data is unavailable or income is zero.
    monthly_income: Optional[Decimal] = None
    monthly_expenses: Optional[Decimal] = None
    savings_rate_percent: Optional[Decimal] = None

    # None when savings or monthly expenses cannot be determined.
    emergency_fund_months: Optional[Decimal] = None
    recommended_emergency_fund: Optional[Decimal] = None
    emergency_fund_gap: Optional[Decimal] = None

    recommendations: List[Recommendation] = Field(default_factory=list)

    # True when summary savings data or a savings-account closing balance exists.
    has_savings_data: bool = False
