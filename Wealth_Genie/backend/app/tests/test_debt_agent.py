from decimal import Decimal

from app.schemas_ext.debt_analysis import HighRiskReason, LiabilityType
from app.schemas_ext.financial import UniversalFinancialProfile
from app.services.agents.debt_agent import DebtAgent


def _profile(**kwargs) -> UniversalFinancialProfile:
    return UniversalFinancialProfile.model_validate(kwargs)


def test_no_liabilities_returns_zeroed_result():
    profile = _profile(loans=[], credit_cards=[], summary={})
    result = DebtAgent(profile).analyze()

    assert result.has_debt is False
    assert result.total_outstanding_debt == Decimal("0")
    assert result.debt_to_income_ratio is None
    assert result.credit_utilization_percent is None
    assert result.high_risk_items == []
    assert result.recommendations == []


def test_total_outstanding_debt_sums_loans_and_cards():
    profile = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 10000, "interest_rate": 8, "emi": 500}],
        credit_cards=[{"card_id": "C1", "outstanding_balance": 2000, "minimum_due": 100, "interest_rate": 15}],
        summary={"total_monthly_income": 8000},
    )
    result = DebtAgent(profile).analyze()

    assert result.total_loan_debt == Decimal("10000")
    assert result.total_credit_card_debt == Decimal("2000")
    assert result.total_outstanding_debt == Decimal("12000")
    assert result.has_debt is True


def test_dti_computed_from_emi_and_minimum_due():
    profile = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 10000, "emi": 300}],
        credit_cards=[{"card_id": "C1", "outstanding_balance": 2000, "minimum_due": 100}],
        summary={"total_monthly_income": 4000},
    )
    result = DebtAgent(profile).analyze()

    assert result.debt_to_income_ratio == Decimal("400") / Decimal("4000")


def test_dti_none_when_income_missing_or_zero():
    profile_missing = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 1000, "emi": 100}],
        credit_cards=[], summary={},
    )
    profile_zero = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 1000, "emi": 100}],
        credit_cards=[], summary={"total_monthly_income": 0},
    )
    assert DebtAgent(profile_missing).analyze().debt_to_income_ratio is None
    assert DebtAgent(profile_zero).analyze().debt_to_income_ratio is None


def test_credit_utilization_computed_across_cards():
    profile = _profile(
        loans=[],
        credit_cards=[
            {"card_id": "C1", "outstanding_balance": 2000, "credit_limit": 5000, "minimum_due": 100},
            {"card_id": "C2", "outstanding_balance": 1000, "credit_limit": 5000, "minimum_due": 50},
        ],
        summary={},
    )
    result = DebtAgent(profile).analyze()
    # (2000 + 1000) / (5000 + 5000) * 100 = 30%
    assert result.credit_utilization_percent == Decimal("30")


def test_credit_utilization_none_when_no_limit_data():
    profile = _profile(
        loans=[],
        credit_cards=[{"card_id": "C1", "outstanding_balance": 2000, "minimum_due": 100}],
        summary={},
    )
    result = DebtAgent(profile).analyze()
    assert result.credit_utilization_percent is None


def test_high_interest_rate_flagged_for_loan_and_card():
    profile = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 1000, "interest_rate": 22, "emi": 50}],
        credit_cards=[{"card_id": "C1", "outstanding_balance": 500, "interest_rate": 25, "minimum_due": 50}],
        summary={},
    )
    result = DebtAgent(profile).analyze()
    reasons = {(item.id, item.reason) for item in result.high_risk_items}
    assert ("L1", HighRiskReason.high_interest_rate) in reasons
    assert ("C1", HighRiskReason.high_interest_rate) in reasons


def test_minimum_payment_trap_flagged():
    profile = _profile(
        loans=[],
        credit_cards=[
            {"card_id": "C1", "outstanding_balance": 10000, "minimum_due": 200},  # 2% -> trap
            {"card_id": "C2", "outstanding_balance": 1000, "minimum_due": 100},   # 10% -> not trap
        ],
        summary={},
    )
    result = DebtAgent(profile).analyze()
    reasons = {(item.id, item.reason) for item in result.high_risk_items}
    assert ("C1", HighRiskReason.minimum_payment_trap) in reasons
    assert ("C2", HighRiskReason.minimum_payment_trap) not in reasons


def test_high_utilization_flagged_per_card():
    profile = _profile(
        loans=[],
        credit_cards=[{"card_id": "C1", "outstanding_balance": 4500, "credit_limit": 5000, "minimum_due": 100}],
        summary={},
    )
    result = DebtAgent(profile).analyze()
    reasons = {(item.id, item.reason) for item in result.high_risk_items}
    assert ("C1", HighRiskReason.high_utilization) in reasons


def test_recommendation_generated_for_high_dti():
    profile = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 10000, "emi": 2000}],
        credit_cards=[],
        summary={"total_monthly_income": 4000},  # DTI = 50%
    )
    result = DebtAgent(profile).analyze()
    titles = [r.title for r in result.recommendations]
    assert "Debt payments are consuming a large share of income" in titles


def test_no_recommendations_when_no_risk_factors():
    profile = _profile(
        loans=[{"loan_id": "L1", "outstanding_balance": 1000, "interest_rate": 5, "emi": 50}],
        credit_cards=[],
        summary={"total_monthly_income": 10000},  # low DTI, low interest
    )
    result = DebtAgent(profile).analyze()
    assert result.recommendations == []


def test_missing_field_data_never_raises():
    profile = _profile(
        loans=[{"loan_id": "L1"}],
        credit_cards=[{"card_id": "C1"}],
        summary={},
    )
    result = DebtAgent(profile).analyze()
    assert result.total_outstanding_debt == Decimal("0")
    assert result.debt_to_income_ratio is None
    assert result.credit_utilization_percent is None