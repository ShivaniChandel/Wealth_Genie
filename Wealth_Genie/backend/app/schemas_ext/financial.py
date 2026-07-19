"""
Universal Financial JSON schema.

This is the single normalised contract between the Universal Extractor and every
downstream AI agent (Debt, Savings, Budget, AI CFO). It mirrors
docs/05_UNIVERSAL_FINANCIAL_JSON.md exactly.

Rules enforced here:
  - Sections not present in a given document are left as empty lists/dicts,
    never null (matches "Universal Extractor" responsibilities in
    08_AI_AGENT_ARCHITECTURE.md).
  - All monetary fields are `Decimal`-backed via pydantic to avoid float drift,
    per 11_DEVELOPMENT_GUIDELINES.md rule #2 (deterministic calculations).
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import List, Optional
from datetime import date

from pydantic import BaseModel, Field, ConfigDict


class AccountType(str, Enum):
    savings = "savings"
    current = "current"
    salary = "salary"


class TransactionType(str, Enum):
    credit = "credit"
    debit = "debit"


class LoanType(str, Enum):
    home = "home"
    personal = "personal"
    auto = "auto"
    education = "education"
    other = "other"


class RecommendationAgent(str, Enum):
    debt_agent = "debt_agent"
    savings_agent = "savings_agent"
    budget_agent = "budget_agent"
    ai_cfo = "ai_cfo"


class RecommendationPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class UserInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")
    account_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_type: Optional[AccountType] = None
    currency: Optional[str] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    statement_period_start: Optional[date] = None
    statement_period_end: Optional[date] = None


class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    transaction_id: Optional[str] = None
    account_id: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    category: Optional[str] = None


class Loan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    loan_id: Optional[str] = None
    lender: Optional[str] = None
    loan_type: Optional[LoanType] = None
    principal: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    emi: Optional[Decimal] = None
    tenure_remaining_months: Optional[int] = None


class CreditCard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    card_id: Optional[str] = None
    issuer: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None
    minimum_due: Optional[Decimal] = None
    due_date: Optional[date] = None
    interest_rate: Optional[Decimal] = None


class Summary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_monthly_income: Optional[Decimal] = None
    total_monthly_expenses: Optional[Decimal] = None
    total_debt: Optional[Decimal] = None
    total_savings: Optional[Decimal] = None
    net_worth_estimate: Optional[Decimal] = None
    savings_rate_percent: Optional[Decimal] = None


class Analysis(BaseModel):
    """Populated later by the Debt/Savings/Budget agents. Empty at extraction time."""
    model_config = ConfigDict(extra="ignore")
    debt_agent: dict = Field(default_factory=dict)
    savings_agent: dict = Field(default_factory=dict)
    budget_agent: dict = Field(default_factory=dict)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent: RecommendationAgent
    priority: RecommendationPriority
    title: str
    detail: str


class UniversalFinancialProfile(BaseModel):
    """Root of the Universal Financial JSON document."""
    model_config = ConfigDict(extra="ignore")

    user: UserInfo = Field(default_factory=UserInfo)
    accounts: List[Account] = Field(default_factory=list)
    transactions: List[Transaction] = Field(default_factory=list)
    loans: List[Loan] = Field(default_factory=list)
    credit_cards: List[CreditCard] = Field(default_factory=list)
    summary: Summary = Field(default_factory=Summary)
    analysis: Analysis = Field(default_factory=Analysis)
    recommendations: List[Recommendation] = Field(default_factory=list)
