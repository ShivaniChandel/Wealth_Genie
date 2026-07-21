from __future__ import annotations

from uuid import UUID, uuid4

from supabase import Client

from app.schemas_ext.ai_cfo_analysis import AICFOAnalysisResult


class ReportsRepository:
    """
    Persists the AI CFO synthesised report to the `reports` table, per
    06_DATABASE_SCHEMA.md. One row per financial_profile, written after the
    AI CFO agent has combined the three specialist agents' outputs.
    """

    def __init__(self, supabase_client: Client):
        self._client = supabase_client

    def create(
        self,
        user_id: UUID,
        financial_profile_id: UUID,
        content: AICFOAnalysisResult,
    ) -> UUID:
        report_id = uuid4()
        # mode="json" ensures Decimal fields serialize to JSON-safe types
        # for the jsonb `content` column, matching the pattern used in
        # FinancialProfilesRepository.create() / RecommendationsRepository.create().
        self._client.table("reports").insert(
            {
                "id": str(report_id),
                "user_id": str(user_id),
                "financial_profile_id": str(financial_profile_id),
                "content": content.model_dump(mode="json"),
            }
        ).execute()
        return report_id

    def get_by_id(self, report_id: UUID, user_id: UUID) -> dict | None:
        result = (
            self._client.table("reports")
            .select("*")
            .eq("id", str(report_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_by_financial_profile_id(
        self, financial_profile_id: UUID, user_id: UUID
    ) -> dict | None:
        result = (
            self._client.table("reports")
            .select("*")
            .eq("financial_profile_id", str(financial_profile_id))
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_by_user_id(self, user_id: UUID) -> list[dict]:
        result = (
            self._client.table("reports")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
