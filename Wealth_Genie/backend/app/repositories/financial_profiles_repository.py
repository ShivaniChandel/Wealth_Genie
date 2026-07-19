from __future__ import annotations

from uuid import UUID, uuid4

from supabase import Client

from app.schemas_ext.financial import UniversalFinancialProfile


class FinancialProfilesRepository:
    def __init__(self, supabase_client: Client):
        self._client = supabase_client

    def create(
        self, user_id: UUID, document_id: UUID, profile: UniversalFinancialProfile
    ) -> UUID:
        profile_id = uuid4()
        # mode="json" ensures Decimal/date fields serialize to JSON-safe types
        # for the jsonb column, per 06_DATABASE_SCHEMA.md.
        self._client.table("financial_profiles").insert(
            {
                "id": str(profile_id),
                "user_id": str(user_id),
                "document_id": str(document_id),
                "profile_json": profile.model_dump(mode="json"),
            }
        ).execute()
        return profile_id

    def get_by_id(self, profile_id: UUID, user_id: UUID) -> dict | None:
        result = (
            self._client.table("financial_profiles")
            .select("*")
            .eq("id", str(profile_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
