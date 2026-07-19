from datetime import datetime
from typing import Optional
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
