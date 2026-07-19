from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.pipeline.analysis_pipeline import run_analysis_pipeline
from app.services.extraction.enums import ExtractionError


@pytest.mark.asyncio
async def test_pipeline_marks_completed_on_success():
    document_id, user_id, job_id = uuid4(), uuid4(), uuid4()
    fake_supabase = MagicMock()

    with patch("app.pipeline.analysis_pipeline.DocumentsRepository") as MockDocsRepo, \
         patch("app.pipeline.analysis_pipeline.AnalysisJobsRepository") as MockJobsRepo, \
         patch("app.pipeline.analysis_pipeline.FinancialProfilesRepository") as MockProfilesRepo, \
         patch("app.pipeline.analysis_pipeline.get_llm_provider") as mock_get_llm, \
         patch("app.pipeline.analysis_pipeline.UniversalExtractor") as MockExtractor:

        docs_repo = MockDocsRepo.return_value
        jobs_repo = MockJobsRepo.return_value
        profiles_repo = MockProfilesRepo.return_value
        docs_repo.download_file.return_value = b"%PDF-1.4 fake"

        extractor_instance = MockExtractor.return_value
        fake_outcome = MagicMock()
        extractor_instance.extract = AsyncMock(return_value=fake_outcome)

        await run_analysis_pipeline(
            supabase_client=fake_supabase,
            document_id=document_id,
            user_id=user_id,
            job_id=job_id,
            document_type="bank_statement",
            file_name="statement.pdf",
            storage_path=f"documents/{user_id}/{document_id}.pdf",
        )

        jobs_repo.mark_running.assert_called_once_with(job_id)
        docs_repo.update_status.assert_any_call(document_id, "processing")
        profiles_repo.create.assert_called_once()
        docs_repo.update_status.assert_any_call(document_id, "completed")
        jobs_repo.mark_completed.assert_called_once_with(job_id)
        jobs_repo.mark_failed.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_marks_failed_on_extraction_error():
    document_id, user_id, job_id = uuid4(), uuid4(), uuid4()
    fake_supabase = MagicMock()

    with patch("app.pipeline.analysis_pipeline.DocumentsRepository") as MockDocsRepo, \
         patch("app.pipeline.analysis_pipeline.AnalysisJobsRepository") as MockJobsRepo, \
         patch("app.pipeline.analysis_pipeline.FinancialProfilesRepository"), \
         patch("app.pipeline.analysis_pipeline.get_llm_provider"), \
         patch("app.pipeline.analysis_pipeline.UniversalExtractor") as MockExtractor:

        docs_repo = MockDocsRepo.return_value
        jobs_repo = MockJobsRepo.return_value
        docs_repo.download_file.return_value = b"broken"

        extractor_instance = MockExtractor.return_value
        extractor_instance.extract = AsyncMock(side_effect=ExtractionError("bad file"))

        await run_analysis_pipeline(
            supabase_client=fake_supabase,
            document_id=document_id,
            user_id=user_id,
            job_id=job_id,
            document_type="bank_statement",
            file_name="statement.pdf",
            storage_path=f"documents/{user_id}/{document_id}.pdf",
        )

        docs_repo.update_status.assert_any_call(document_id, "failed")
        jobs_repo.mark_failed.assert_called_once()
        jobs_repo.mark_completed.assert_not_called()
