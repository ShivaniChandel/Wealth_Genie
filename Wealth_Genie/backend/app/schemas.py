from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int


class TokenVerificationResponse(BaseModel):
    user_id: UUID
    email: str
    aud: str
    role: str


class UploadResponse(BaseModel):
    """
    Milestone 3 change: extended (additive) to include analysis_job_id so the
    frontend can immediately begin polling GET /analysis/status/{job_id},
    per 07_API_SPECIFICATION.md. `status` now reflects the job queue state
    ("queued") rather than the raw document row state ("uploaded").
    """
    document_id: UUID
    analysis_job_id: UUID
    status: str
