"""
DebtAgent — deterministic debt analysis. Milestone 4 scope only.

Reads ONLY UniversalFinancialProfile.loans / .credit_cards / .summary.
Never touches raw files, the extractor, or any LLM provider. All arithmetic
is Decimal-backed (11_DEVELOPMENT_GUIDELINES.md rule #2).

Deferred to a later milestone (YAGNI): avalanche/snowball ordering, payoff
strategy selection, payoff timeline projections.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app.schemas_ext.debt_analysis import (
    DebtAnalysisResult,
    HighRiskItem,
    HighRiskReason,
    LiabilityType,
)
from app.schemas_ext.financial import (
    CreditCard,
    Loan,
    Recommendation,
    RecommendationAgent,
    RecommendationPriority,
    UniversalFinancialProfile,
)

# Fixed, documented thresholds — not judgment calls requiring an LLM.
_HIGH_INTEREST_RATE_THRESHOLD = Decimal("20")       # percent
_MINIMUM_PAYMENT_TRAP_THRESHOLD = Decimal("0.05")   # minimum_due / outstanding_balance
_HIGH_UTILIZATION_THRESHOLD = Decimal("80")         # percent, per-card and overall
_HIGH_DTI_THRESHOLD = Decimal("0.40")               # ratio, triggers a recommendation


class DebtAgent:
    def __init__(self, profile: UniversalFinancialProfile):
        self._profile = profile

    def analyze(self) -> DebtAnalysisResult:
        loans = self._profile.loans
        cards = self._profile.credit_cards

        total_loan_debt = self._sum_decimal(l.outstanding_balance for l in loans)
        total_credit_card_debt = self._sum_decimal(c.outstanding_balance for c in cards)
        total_outstanding_debt = total_loan_debt + total_credit_card_debt
        has_debt = bool(loans or cards)

        dti = self._compute_dti(loans, cards)
        utilization = self._compute_utilization(cards)
        high_risk_items = self._detect_high_risk(loans, cards, utilization)

        return DebtAnalysisResult(
            total_outstanding_debt=total_outstanding_debt,
            total_loan_debt=total_loan_debt,
            total_credit_card_debt=total_credit_card_debt,
            debt_to_income_ratio=dti,
            credit_utilization_percent=utilization,
            high_risk_items=high_risk_items,
            recommendations=self._build_recommendations(dti, utilization, high_risk_items),
            has_debt=has_debt,
        )

    # ---- calculations ----

    @staticmethod
    def _sum_decimal(values) -> Decimal:
        return sum((v for v in values if v is not None), Decimal("0"))

    def _compute_dti(self, loans: List[Loan], cards: List[CreditCard]) -> Optional[Decimal]:
        income = self._profile.summary.total_monthly_income
        if income is None or income == 0:
            return None

        total_payments = self._sum_decimal(l.emi for l in loans) + self._sum_decimal(
            c.minimum_due for c in cards
        )
        return total_payments / income

    @staticmethod
    def _compute_utilization(cards: List[CreditCard]) -> Optional[Decimal]:
        rated = [c for c in cards if c.outstanding_balance is not None and c.credit_limit]
        if not rated:
            return None

        total_balance = sum((c.outstanding_balance for c in rated), Decimal("0"))
        total_limit = sum((c.credit_limit for c in rated), Decimal("0"))
        if total_limit == 0:
            return None

        return (total_balance / total_limit) * Decimal("100")

    @staticmethod
    def _detect_high_risk(
        loans: List[Loan], cards: List[CreditCard], overall_utilization: Optional[Decimal]
    ) -> List[HighRiskItem]:
        flagged: List[HighRiskItem] = []

        for loan in loans:
            if loan.interest_rate is not None and loan.interest_rate >= _HIGH_INTEREST_RATE_THRESHOLD:
                flagged.append(
                    HighRiskItem(
                        liability_type=LiabilityType.loan,
                        id=loan.loan_id,
                        reason=HighRiskReason.high_interest_rate,
                    )
                )

        for card in cards:
            if card.interest_rate is not None and card.interest_rate >= _HIGH_INTEREST_RATE_THRESHOLD:
                flagged.append(
                    HighRiskItem(
                        liability_type=LiabilityType.credit_card,
                        id=card.card_id,
                        reason=HighRiskReason.high_interest_rate,
                    )
                )

            if (
                card.minimum_due is not None
                and card.outstanding_balance is not None
                and card.outstanding_balance > 0
                and (card.minimum_due / card.outstanding_balance) < _MINIMUM_PAYMENT_TRAP_THRESHOLD
            ):
                flagged.append(
                    HighRiskItem(
                        liability_type=LiabilityType.credit_card,
                        id=card.card_id,
                        reason=HighRiskReason.minimum_payment_trap,
                    )
                )

            if (
                card.outstanding_balance is not None
                and card.credit_limit
                and card.credit_limit > 0
                and (card.outstanding_balance / card.credit_limit) * Decimal("100")
                >= _HIGH_UTILIZATION_THRESHOLD
            ):
                flagged.append(
                    HighRiskItem(
                        liability_type=LiabilityType.credit_card,
                        id=card.card_id,
                        reason=HighRiskReason.high_utilization,
                    )
                )

        return flagged

    # ---- deterministic recommendations (template-based, no LLM) ----

    @staticmethod
    def _build_recommendations(
        dti: Optional[Decimal],
        utilization: Optional[Decimal],
        high_risk_items: List[HighRiskItem],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []

        if dti is not None and dti > _HIGH_DTI_THRESHOLD:
            recs.append(
                Recommendation(
                    agent=RecommendationAgent.debt_agent,
                    priority=RecommendationPriority.high,
                    title="Debt payments are consuming a large share of income",
                    detail=(
                        f"Monthly debt payments are {dti * 100:.1f}% of income, "
                        f"above the {_HIGH_DTI_THRESHOLD * 100:.0f}% threshold "
                        "generally considered manageable."
                    ),
                )
            )

        if utilization is not None and utilization >= _HIGH_UTILIZATION_THRESHOLD:
            recs.append(
                Recommendation(
                    agent=RecommendationAgent.debt_agent,
                    priority=RecommendationPriority.high,
                    title="Credit utilization is high",
                    detail=(
                        f"Overall credit utilization is {utilization:.1f}%, at or above "
                        f"the {_HIGH_UTILIZATION_THRESHOLD:.0f}% threshold that can affect "
                        "credit standing."
                    ),
                )
            )

        if any(item.reason == HighRiskReason.minimum_payment_trap for item in high_risk_items):
            recs.append(
                Recommendation(
                    agent=RecommendationAgent.debt_agent,
                    priority=RecommendationPriority.medium,
                    title="Some cards are being paid only the minimum",
                    detail=(
                        "One or more credit cards have a minimum payment far below "
                        "the outstanding balance, which extends payoff time significantly."
                    ),
                )
            )

        if any(item.reason == HighRiskReason.high_interest_rate for item in high_risk_items):
            recs.append(
                Recommendation(
                    agent=RecommendationAgent.debt_agent,
                    priority=RecommendationPriority.medium,
                    title="High-interest debt detected",
                    detail=(
                        f"One or more liabilities carry an interest rate at or above "
                        f"{_HIGH_INTEREST_RATE_THRESHOLD:.0f}%."
                    ),
                )
            )

        return recs