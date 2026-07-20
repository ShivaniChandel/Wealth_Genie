"""
AI CFO output schema — Commit 1 scope only (schema only, no agent logic).

Per 08_AI_AGENT_ARCHITECTURE.md: the AI CFO is a synthesiser, not an
orchestrator. It does not perform new financial calculations and does not
duplicate Debt/Savings/Budget logic — it only combines their already-computed
outputs into a single unified report.

This schema mirrors the existing per-agent result schemas (DebtAnalysisResult,
SavingsAnalysisResult, BudgetAnalysisResult): plain pydantic model, Decimal-free
score field kept as a deterministic int, and the existing `Recommendation`
model reused rather than duplicated.

AICFOAgent itself (which populates this schema) is implemented in a later
commit — this commit adds the schema and its test-first contract only.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas_ext.budget_analysis import BudgetAnalysisResult
from app.schemas_ext.debt_analysis import DebtAnalysisResult
from app.schemas_ext.financial import Recommendation
from app.schemas_ext.savings_analysis import SavingsAnalysisResult


class AICFOAnalysisResult(BaseModel):
    """
    Root output of AICFOAgent.analyze() (agent implemented in a later commit).
    Persisted as `content` in `reports` (agent = 'ai_cfo'), per
    06_DATABASE_SCHEMA.md.
    """
    model_config = ConfigDict(extra="ignore")

    executive_summary: str = ""

    # Deterministic 0-100 score. See AICFOAgent (later commit) for the
    # deduction rules; this schema only defines the field/shape.
    overall_financial_health_score: int = 100

    debt_analysis: DebtAnalysisResult = Field(default_factory=DebtAnalysisResult)
    savings_analysis: SavingsAnalysisResult = Field(default_factory=SavingsAnalysisResult)
    budget_analysis: BudgetAnalysisResult = Field(default_factory=BudgetAnalysisResult)

    # Subset of `recommendations` surfaced as top priorities in the report.
    priority_recommendations: List[Recommendation] = Field(default_factory=list)

    # All recommendations combined from the three specialist agents, in
    # debt -> savings -> budget order (matches 08_AI_AGENT_ARCHITECTURE.md
    # agent execution order).
    recommendations: List[Recommendation] = Field(default_factory=list)
