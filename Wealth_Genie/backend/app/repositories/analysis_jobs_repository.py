from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from supabase import Client


class AnalysisJobsRepository:
    def __init__(self, supabase_client: Client):
        self._client = supabase_client

    def create(self, document_id: UUID, user_id: UUID) -> UUID:
        job_id = uuid4()
        self._client.table("analysis_jobs").insert(
            {
                "id": str(job_id),
                "document_id": str(document_id),
                "user_id": str(user_id),
                "status": "queued",
            }
        ).execute()
        return job_id

    def get_by_id(self, job_id: UUID, user_id: UUID) -> dict | None:
        result = (
            self._client.table("analysis_jobs")
            .select("*")
            .eq("id", str(job_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def mark_running(self, job_id: UUID) -> None:
        self._client.table("analysis_jobs").update(
            {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", str(job_id)).execute()

    def mark_completed(self, job_id: UUID, report_id: Optional[UUID] = None) -> None:
        payload = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if report_id is not None:
            payload["report_id"] = str(report_id)
        self._client.table("analysis_jobs").update(payload).eq("id", str(job_id)).execute()

    def mark_failed(self, job_id: UUID, error_message: str) -> None:
        self._client.table("analysis_jobs").update(
            {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message[:2000],
            }
        ).eq("id", str(job_id)).execute()
