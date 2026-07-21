from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AnalysisJobStatusResponse(BaseModel):
    job_id: UUID
    document_id: UUID
    status: str  # queued | running | completed | failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    report_id: Optional[UUID] = None


class FinancialProfileResponse(BaseModel):
    id: UUID
    document_id: UUID
    created_at: datetime
    profile_json: dict


class ReportListItemResponse(BaseModel):
    id: UUID
    financial_profile_id: UUID
    created_at: datetime


class ReportListResponse(BaseModel):
    reports: List[ReportListItemResponse]


class ReportDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    financial_profile_id: UUID
    created_at: datetime
    content: dict


class DashboardResponse(BaseModel):
    user_id: UUID
    total_monthly_income: Decimal = Decimal("0")
    total_monthly_expenses: Decimal = Decimal("0")
    total_debt: Decimal = Decimal("0")
    total_savings: Decimal = Decimal("0")
    savings_rate_percent: Decimal = Decimal("0")
    net_worth_estimate: Decimal = Decimal("0")
    latest_report_id: Optional[UUID] = None
    documents_processed: int = 0
    last_updated: Optional[datetime] = None
