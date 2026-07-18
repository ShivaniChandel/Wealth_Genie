from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str

class UserRegisterResponse(BaseModel):
    user_id: UUID
    email: str
    access_token: str
    token_type: str = "bearer"

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID

class TokenVerificationResponse(BaseModel):
    user_id: UUID
    email: str
    aud: str
    role: str

class UploadResponse(BaseModel):
    document_id: UUID
    status: str

