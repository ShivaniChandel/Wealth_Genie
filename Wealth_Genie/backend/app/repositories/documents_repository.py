from __future__ import annotations

from uuid import UUID

from supabase import Client


class DocumentsRepository:
    def __init__(self, supabase_client: Client):
        self._client = supabase_client

    def get_by_id(self, document_id: UUID, user_id: UUID) -> dict | None:
        result = (
            self._client.table("documents")
            .select("*")
            .eq("id", str(document_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_latest_completed_by_user_id(self, user_id: UUID) -> dict | None:
        result = (
            self._client.table("documents")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "completed")
            .order("uploaded_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def count_completed_by_user_id(self, user_id: UUID) -> int:
        result = (
            self._client.table("documents")
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .eq("status", "completed")
            .execute()
        )
        return result.count or 0

    def update_status(self, document_id: UUID, status: str) -> None:
        self._client.table("documents").update({"status": status}).eq(
            "id", str(document_id)
        ).execute()

    def download_file(self, storage_path: str) -> bytes:
        return self._client.storage.from_("documents").download(storage_path)
