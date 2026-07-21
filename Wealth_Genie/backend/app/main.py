from fastapi import FastAPI, Depends, HTTPException, status, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from supabase import create_client, Client
from uuid import UUID, uuid4
from decimal import Decimal
import os

from app.config import settings
from app.schemas import (
    TokenVerificationResponse,
    ErrorResponse,
    UploadResponse,
    ChatRequest,
    ChatResponse,
)
from app.schemas_ext.analysis import (
    AnalysisJobStatusResponse,
    DashboardResponse,
    FinancialProfileResponse,
    ReportDetailResponse,
    ReportListItemResponse,
    ReportListResponse,
)
from app.auth import get_current_user_id, verify_jwt
from app.repositories.analysis_jobs_repository import AnalysisJobsRepository
from app.repositories.documents_repository import DocumentsRepository
from app.repositories.financial_profiles_repository import FinancialProfilesRepository
from app.repositories.reports_repository import ReportsRepository
from app.pipeline.analysis_pipeline import run_analysis_pipeline
from app.services.llm.factory import get_llm_provider

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

@app.post(
    "/api/v1/auth/logout",
    status_code=204,
    responses={401: {"model": ErrorResponse}}
)
def logout_user(user_id: UUID = Depends(get_current_user_id)):
    # For MVP, FastAPI logout is a stateless no-op
    return

# Document upload endpoint
@app.post(
    "/api/v1/documents/upload",
    response_model=UploadResponse,
    status_code=202,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def upload_document(
    background_tasks: BackgroundTasks,
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

    # 6. Milestone 3: create the analysis_jobs row and enqueue the background
    #    extraction pipeline, per 13_ASYNC_PROCESSING.md.
    jobs_repo = AnalysisJobsRepository(supabase_client)
    try:
        analysis_job_id = jobs_repo.create(document_id=document_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analysis job: {str(e)}"
        )

    background_tasks.add_task(
        run_analysis_pipeline,
        supabase_client,
        document_id,
        user_id,
        analysis_job_id,
        document_type,
        file.filename,
        storage_path,
    )

    return UploadResponse(
        document_id=document_id,
        analysis_job_id=analysis_job_id,
        status="queued"
    )


# ----------------- ANALYSIS ROUTERS (Milestone 3) -----------------

@app.get(
    "/api/v1/analysis/status/{job_id}",
    response_model=AnalysisJobStatusResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
def get_analysis_status(job_id: UUID, user_id: UUID = Depends(get_current_user_id)):
    jobs_repo = AnalysisJobsRepository(supabase_client)
    job = jobs_repo.get_by_id(job_id=job_id, user_id=user_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")

    return AnalysisJobStatusResponse(
        job_id=job["id"],
        document_id=job["document_id"],
        status=job["status"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        error_message=job.get("error_message"),
        report_id=job.get("report_id"),
    )


@app.get(
    "/api/v1/analysis/{financial_profile_id}",
    response_model=FinancialProfileResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
def get_financial_profile(financial_profile_id: UUID, user_id: UUID = Depends(get_current_user_id)):
    profiles_repo = FinancialProfilesRepository(supabase_client)
    profile = profiles_repo.get_by_id(profile_id=financial_profile_id, user_id=user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial profile not found")

    return FinancialProfileResponse(
        id=profile["id"],
        document_id=profile["document_id"],
        created_at=profile["created_at"],
        profile_json=profile["profile_json"],
    )


# ----------------- REPORT ROUTERS -----------------

@app.get(
    "/api/v1/reports",
    response_model=ReportListResponse,
    responses={401: {"model": ErrorResponse}}
)
def list_reports(user_id: UUID = Depends(get_current_user_id)):
    reports_repo = ReportsRepository(supabase_client)
    reports = reports_repo.list_by_user_id(user_id=user_id)
    return ReportListResponse(
        reports=[
            ReportListItemResponse(
                id=report["id"],
                financial_profile_id=report["financial_profile_id"],
                created_at=report["created_at"],
            )
            for report in reports
        ]
    )


@app.get(
    "/api/v1/reports/{report_id}",
    response_model=ReportDetailResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
def get_report(report_id: UUID, user_id: UUID = Depends(get_current_user_id)):
    reports_repo = ReportsRepository(supabase_client)
    report = reports_repo.get_by_id(report_id=report_id, user_id=user_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return ReportDetailResponse(
        id=report["id"],
        user_id=report["user_id"],
        financial_profile_id=report["financial_profile_id"],
        created_at=report["created_at"],
        content=report["content"],
    )


# ----------------- DASHBOARD ROUTERS -----------------

@app.get(
    "/api/v1/dashboard",
    response_model=DashboardResponse,
    responses={401: {"model": ErrorResponse}}
)
def get_dashboard(user_id: UUID = Depends(get_current_user_id)):
    documents_repo = DocumentsRepository(supabase_client)
    profiles_repo = FinancialProfilesRepository(supabase_client)
    reports_repo = ReportsRepository(supabase_client)

    documents_processed = documents_repo.count_completed_by_user_id(user_id=user_id)
    document = documents_repo.get_latest_completed_by_user_id(user_id=user_id)
    if document is None:
        return DashboardResponse(user_id=user_id, documents_processed=documents_processed)

    profile = profiles_repo.get_by_document_id(
        document_id=UUID(document["id"]), user_id=user_id
    )
    if profile is None:
        return DashboardResponse(user_id=user_id, documents_processed=documents_processed)

    summary = profile.get("profile_json", {}).get("summary", {})
    report = reports_repo.get_by_financial_profile_id(
        financial_profile_id=UUID(profile["id"]), user_id=user_id
    )
    return DashboardResponse(
        user_id=user_id,
        total_monthly_income=summary.get("total_monthly_income") or Decimal("0"),
        total_monthly_expenses=summary.get("total_monthly_expenses") or Decimal("0"),
        total_debt=summary.get("total_debt") or Decimal("0"),
        total_savings=summary.get("total_savings") or Decimal("0"),
        savings_rate_percent=summary.get("savings_rate_percent") or Decimal("0"),
        net_worth_estimate=summary.get("net_worth_estimate") or Decimal("0"),
        latest_report_id=report["id"] if report is not None else None,
        documents_processed=documents_processed,
        last_updated=profile["created_at"],
    )


# ----------------- CHAT ROUTERS -----------------

@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def chat(request: ChatRequest, user_id: UUID = Depends(get_current_user_id)):
    profiles_repo = FinancialProfilesRepository(supabase_client)
    reports_repo = ReportsRepository(supabase_client)
    profile = profiles_repo.get_latest_by_user_id(user_id=user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial profile not found")

    reports = reports_repo.list_by_user_id(user_id=user_id)
    report = reports[0] if reports else None
    provider = get_llm_provider()
    reply = await provider.answer_financial_question(
        message=request.message,
        financial_profile=profile["profile_json"],
        report=report["content"] if report is not None else None,
        conversation_history=[message.model_dump() for message in request.conversation_history],
    )
    return ChatResponse(reply=reply, financial_profile_id=profile["id"])
