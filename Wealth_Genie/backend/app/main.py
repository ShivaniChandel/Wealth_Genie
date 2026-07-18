from fastapi import FastAPI, Depends, HTTPException, status, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from supabase import create_client, Client
from uuid import UUID, uuid4
import os

from app.config import settings
from app.schemas import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
    TokenVerificationResponse,
    ErrorResponse,
    UploadResponse
)
from app.auth import get_current_user_id, verify_jwt

app = FastAPI(title="FinPilot AI - Wealth Genie API", version="1.0.0")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

# Custom exception handlers to match the Standard Error Schema
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "Error",
            "detail": str(exc.detail),
            "status_code": exc.status_code
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "detail": str(exc.errors()),
            "status_code": 400
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "status_code": 500
        }
    )

# ----------------- AUTH ROUTERS -----------------

@app.post(
    "/api/v1/auth/register",
    response_model=UserRegisterResponse,
    status_code=201,
    responses={400: {"model": ErrorResponse}}
)
def register_user(request: UserRegisterRequest):
    try:
        response = supabase_client.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed: empty user returned"
            )
            
        access_token = ""
        if response.session:
            access_token = response.session.access_token
            
        return UserRegisterResponse(
            user_id=UUID(response.user.id),
            email=response.user.email,
            access_token=access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post(
    "/api/v1/auth/login",
    response_model=UserLoginResponse,
    responses={401: {"model": ErrorResponse}}
)
def login_user(request: UserLoginRequest):
    try:
        response = supabase_client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response.session or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        return UserLoginResponse(
            access_token=response.session.access_token,
            user_id=UUID(response.user.id)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@app.post(
    "/api/v1/auth/logout",
    status_code=204,
    responses={401: {"model": ErrorResponse}}
)
def logout_user(user_id: UUID = Depends(get_current_user_id)):
    # For MVP, FastAPI logout is a stateless no-op
    return

@app.get(
    "/api/v1/auth/verify-token",
    response_model=TokenVerificationResponse,
    responses={401: {"model": ErrorResponse}}
)
def verify_token(user_id: UUID = Depends(get_current_user_id), authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    payload = verify_jwt(token)
    return TokenVerificationResponse(
        user_id=user_id,
        email=payload.get("email", ""),
        aud=payload.get("aud", ""),
        role=payload.get("role", "")
    )

# Startup event to ensure documents storage bucket exists
@app.on_event("startup")
async def startup_event():
    try:
        supabase_client.storage.get_bucket("documents")
    except Exception:
        try:
            # Create bucket as private
            supabase_client.storage.create_bucket("documents", {"public": False})
        except Exception as e:
            print(f"Warning: Could not create Supabase Storage bucket 'documents': {str(e)}")

# Document upload endpoint
@app.post(
    "/api/v1/documents/upload",
    response_model=UploadResponse,
    status_code=200,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    user_id: UUID = Depends(get_current_user_id)
):
    # 1. Validate file extension and content type
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if file_ext != ".pdf" or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are allowed."
        )

    # 2. Validate document type
    allowed_types = ["bank_statement", "credit_card", "loan", "salary_slip"]
    if document_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Allowed types: {', '.join(allowed_types)}"
        )

    # 3. Validate file size (max 10MB)
    try:
        file.file.seek(0, 2)  # seek to end
        file_size = file.file.tell()
        file.file.seek(0)      # reset to beginning
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read file metadata: {str(e)}"
        )

    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 10MB."
        )

    document_id = uuid4()
    storage_path = f"documents/{user_id}/{document_id}.pdf"

    # 4. Upload file to Supabase Storage
    try:
        file_bytes = await file.read()
        supabase_client.storage.from_("documents").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )

    # 5. Create database record in 'documents' table
    try:
        supabase_client.table("documents").insert({
            "id": str(document_id),
            "user_id": str(user_id),
            "file_name": file.filename,
            "file_path": storage_path,
            "document_type": document_type,
            "status": "uploaded"
        }).execute()
    except Exception as e:
        # Cleanup file from storage if DB insert fails
        try:
            supabase_client.storage.from_("documents").remove([storage_path])
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document record in database: {str(e)}"
        )

    return UploadResponse(
        document_id=document_id,
        status="uploaded"
    )
