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
         patch("app.pipeline.analysis_pipeline.RecommendationsRepository") as MockRecsRepo, \
         patch("app.pipeline.analysis_pipeline.DebtAgent") as MockDebtAgent, \
         patch("app.pipeline.analysis_pipeline.get_llm_provider") as mock_get_llm, \
         patch("app.pipeline.analysis_pipeline.UniversalExtractor") as MockExtractor:

        docs_repo = MockDocsRepo.return_value
        jobs_repo = MockJobsRepo.return_value
        profiles_repo = MockProfilesRepo.return_value
        recs_repo = MockRecsRepo.return_value
        docs_repo.download_file.return_value = b"%PDF-1.4 fake"

        fake_profile_id = uuid4()
        profiles_repo.create.return_value = fake_profile_id

        extractor_instance = MockExtractor.return_value
        fake_outcome = MagicMock()
        extractor_instance.extract = AsyncMock(return_value=fake_outcome)

        fake_debt_result = MagicMock()
        MockDebtAgent.return_value.analyze.return_value = fake_debt_result

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

        # Milestone 4 assertions
        MockDebtAgent.assert_called_once_with(fake_outcome.profile)
        MockDebtAgent.return_value.analyze.assert_called_once()
        recs_repo.create.assert_called_once_with(
            user_id=user_id,
            financial_profile_id=fake_profile_id,
            agent="debt_agent",
            content=fake_debt_result,
        )

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
         patch("app.pipeline.analysis_pipeline.RecommendationsRepository"), \
         patch("app.pipeline.analysis_pipeline.DebtAgent"), \
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


@pytest.mark.asyncio
async def test_pipeline_marks_failed_if_debt_agent_raises():
    """
    Milestone 4: confirms the existing generic except Exception clause still
    catches failures from the new DebtAgent step without needing a dedicated
    except clause for it.
    """
    document_id, user_id, job_id = uuid4(), uuid4(), uuid4()
    fake_supabase = MagicMock()

    with patch("app.pipeline.analysis_pipeline.DocumentsRepository") as MockDocsRepo, \
         patch("app.pipeline.analysis_pipeline.AnalysisJobsRepository") as MockJobsRepo, \
         patch("app.pipeline.analysis_pipeline.FinancialProfilesRepository") as MockProfilesRepo, \
         patch("app.pipeline.analysis_pipeline.RecommendationsRepository") as MockRecsRepo, \
         patch("app.pipeline.analysis_pipeline.DebtAgent") as MockDebtAgent, \
         patch("app.pipeline.analysis_pipeline.get_llm_provider"), \
         patch("app.pipeline.analysis_pipeline.UniversalExtractor") as MockExtractor:

        docs_repo = MockDocsRepo.return_value
        jobs_repo = MockJobsRepo.return_value
        profiles_repo = MockProfilesRepo.return_value
        docs_repo.download_file.return_value = b"%PDF-1.4 fake"
        profiles_repo.create.return_value = uuid4()

        extractor_instance = MockExtractor.return_value
        extractor_instance.extract = AsyncMock(return_value=MagicMock())

        MockDebtAgent.return_value.analyze.side_effect = RuntimeError("boom")

        await run_analysis_pipeline(
            supabase_client=fake_supabase,
            document_id=document_id,
            user_id=user_id,
            job_id=job_id,
            document_type="bank_statement",
            file_name="statement.pdf",
            storage_path=f"documents/{user_id}/{document_id}.pdf",
        )

        MockRecsRepo.return_value.create.assert_not_called()
        docs_repo.update_status.assert_any_call(document_id, "failed")
        jobs_repo.mark_failed.assert_called_once()
        jobs_repo.mark_completed.assert_not_called()