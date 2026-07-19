"""
run_analysis_pipeline

Background worker invoked via FastAPI BackgroundTasks after upload, per
13_ASYNC_PROCESSING.md. Milestone 3 scope: steps 1-3 of that document
(status transitions + Universal Extractor + financial_profiles persistence).

Steps 4-7 (Debt/Savings/Budget agents + AI CFO synthesis) are explicitly out
of scope for this milestone and are NOT stubbed here — analysis_jobs.status
transitions straight to 'completed' once the financial profile is persisted,
with report_id left null until those agents exist.
"""

from __future__ import annotations

import traceback
from uuid import UUID

from supabase import Client

from app.repositories.analysis_jobs_repository import AnalysisJobsRepository
from app.repositories.documents_repository import DocumentsRepository
from app.repositories.financial_profiles_repository import FinancialProfilesRepository
from app.services.extraction.enums import (
    ExtractionError,
    UnsupportedDocumentError,
)
from app.services.extraction.universal_extractor import UniversalExtractor
from app.services.extraction.validator import FinancialJsonValidationError
from app.services.llm.base import LLMProviderError
from app.services.llm.factory import get_llm_provider


async def run_analysis_pipeline(
    supabase_client: Client,
    document_id: UUID,
    user_id: UUID,
    job_id: UUID,
    document_type: str,
    file_name: str,
    storage_path: str,
) -> None:
    documents_repo = DocumentsRepository(supabase_client)
    jobs_repo = AnalysisJobsRepository(supabase_client)
    profiles_repo = FinancialProfilesRepository(supabase_client)

    jobs_repo.mark_running(job_id)
    documents_repo.update_status(document_id, "processing")

    try:
        file_bytes = documents_repo.download_file(storage_path)

        extractor = UniversalExtractor(
            llm_provider=get_llm_provider()
        )

        outcome = await extractor.extract(
            file_bytes=file_bytes,
            filename=file_name,
            document_type=document_type,
        )

        profiles_repo.create(
            user_id=user_id,
            document_id=document_id,
            profile=outcome.profile,
        )

        documents_repo.update_status(document_id, "completed")

        # report_id intentionally omitted until later milestones.
        jobs_repo.mark_completed(job_id)

    except (
        UnsupportedDocumentError,
        ExtractionError,
        FinancialJsonValidationError,
        LLMProviderError,
    ) as exc:
        print("\n========== PIPELINE ERROR ==========")
        traceback.print_exc()
        print("====================================\n")

        documents_repo.update_status(document_id, "failed")
        jobs_repo.mark_failed(job_id, str(exc))

    except Exception as exc:
        print("\n========== UNEXPECTED PIPELINE ERROR ==========")
        traceback.print_exc()
        print("===============================================\n")

        documents_repo.update_status(document_id, "failed")
        jobs_repo.mark_failed(job_id, f"Unexpected error: {exc}")