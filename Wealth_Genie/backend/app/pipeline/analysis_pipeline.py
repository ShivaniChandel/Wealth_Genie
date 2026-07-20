"""
run_analysis_pipeline

Background worker invoked via FastAPI BackgroundTasks after upload, per
13_ASYNC_PROCESSING.md. Milestone 3 scope: steps 1-3 of that document
(status transitions + Universal Extractor + financial_profiles persistence).

Milestone 4 (AI CFO Commit 4): added Debt Agent, Savings Agent, and Budget
Agent (deterministic per-agent analyses), each persisted to recommendations.
AICFOAgent then synthesises the three specialist outputs into a single
report, persisted via ReportsRepository, with the AI CFO output itself
also persisted to recommendations (agent="ai_cfo"). analysis_jobs.status
transitions to 'completed' with the generated report_id once all of the
above has been persisted.
"""

from __future__ import annotations

import traceback
from uuid import UUID

from supabase import Client

from app.repositories.analysis_jobs_repository import AnalysisJobsRepository
from app.repositories.documents_repository import DocumentsRepository
from app.repositories.financial_profiles_repository import FinancialProfilesRepository
from app.repositories.recommendations_repository import RecommendationsRepository
from app.repositories.reports_repository import ReportsRepository
from app.services.agents.ai_cfo_agent import AICFOAgent
from app.services.agents.budget_agent import BudgetAgent
from app.services.agents.debt_agent import DebtAgent
from app.services.agents.savings_agent import SavingsAgent
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
    recommendations_repo = RecommendationsRepository(supabase_client)
    reports_repo = ReportsRepository(supabase_client)

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

        financial_profile_id = profiles_repo.create(
            user_id=user_id,
            document_id=document_id,
            profile=outcome.profile,
        )

        # Milestone 4: deterministic debt analysis. Reads only the just-
        # persisted profile's in-memory copy (outcome.profile) — no re-fetch
        # needed since it's the same object.
        debt_analysis = DebtAgent(outcome.profile).analyze()
        recommendations_repo.create(
            user_id=user_id,
            financial_profile_id=financial_profile_id,
            agent="debt_agent",
            content=debt_analysis,
        )

        savings_analysis = SavingsAgent(outcome.profile).analyze()
        recommendations_repo.create(
            user_id=user_id,
            financial_profile_id=financial_profile_id,
            agent="savings_agent",
            content=savings_analysis,
        )

        budget_analysis = BudgetAgent(outcome.profile).analyze()
        recommendations_repo.create(
            user_id=user_id,
            financial_profile_id=financial_profile_id,
            agent="budget_agent",
            content=budget_analysis,
        )

        # Milestone 4: AI CFO synthesises the three specialist outputs into
        # a single report. Per 08_AI_AGENT_ARCHITECTURE.md, AICFOAgent is a
        # synthesiser, not an orchestrator — it consumes the already-computed
        # DebtAnalysisResult, SavingsAnalysisResult, and BudgetAnalysisResult
        # directly, without re-running or duplicating their logic.
        ai_cfo_analysis = AICFOAgent(
            debt_analysis, savings_analysis, budget_analysis
        ).analyze()
        recommendations_repo.create(
            user_id=user_id,
            financial_profile_id=financial_profile_id,
            agent="ai_cfo",
            content=ai_cfo_analysis,
        )
        report_id = reports_repo.create(
            user_id=user_id,
            financial_profile_id=financial_profile_id,
            content=ai_cfo_analysis,
        )

        documents_repo.update_status(document_id, "completed")

        jobs_repo.mark_completed(job_id, report_id)

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
