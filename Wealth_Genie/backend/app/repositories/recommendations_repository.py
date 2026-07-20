from __future__ import annotations

from uuid import UUID, uuid4

from supabase import Client

from app.schemas_ext.debt_analysis import DebtAnalysisResult


class RecommendationsRepository:
    """
    Persists individual agent outputs to the `recommendations` table, per
    06_DATABASE_SCHEMA.md. One row per agent per financial_profile
    (agent in: debt_agent | savings_agent | budget_agent | ai_cfo).
    """

    def __init__(self, supabase_client: Client):
        self._client = supabase_client

    def create(
        self,
        user_id: UUID,
        financial_profile_id: UUID,
        agent: str,
        content: DebtAnalysisResult,
    ) -> UUID:
        recommendation_id = uuid4()
        # mode="json" ensures Decimal fields serialize to JSON-safe types
        # for the jsonb `content` column, matching the pattern used in
        # FinancialProfilesRepository.create().
        self._client.table("recommendations").insert(
            {
                "id": str(recommendation_id),
                "user_id": str(user_id),
                "financial_profile_id": str(financial_profile_id),
                "agent": agent,
                "content": content.model_dump(mode="json"),
            }
        ).execute()
        return recommendation_id

    def get_by_financial_profile_id(
        self, financial_profile_id: UUID, user_id: UUID
    ) -> list[dict]:
        result = (
            self._client.table("recommendations")
            .select("*")
            .eq("financial_profile_id", str(financial_profile_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return result.data or []

    def get_by_agent(
        self, financial_profile_id: UUID, user_id: UUID, agent: str
    ) -> dict | None:
        result = (
            self._client.table("recommendations")
            .select("*")
            .eq("financial_profile_id", str(financial_profile_id))
            .eq("user_id", str(user_id))
            .eq("agent", agent)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None