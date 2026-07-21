from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import List, Literal, Optional


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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    financial_profile_id: UUID
