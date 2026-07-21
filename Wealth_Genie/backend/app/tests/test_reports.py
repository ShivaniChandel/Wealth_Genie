import datetime
import os
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-key-12345"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"

from app.config import settings
from app.main import app


client = TestClient(app)


def _headers(user_id: str) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": user_id,
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        },
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@patch("app.main.ReportsRepository")
def test_list_reports_returns_only_list_fields_for_authenticated_user(mock_reports_repo_cls):
    user_id, report_id, profile_id = uuid4(), uuid4(), uuid4()
    mock_reports_repo_cls.return_value.list_by_user_id.return_value = [
        {
            "id": str(report_id),
            "user_id": str(user_id),
            "financial_profile_id": str(profile_id),
            "created_at": "2026-07-22T10:00:00+00:00",
            "content": {"executive_summary": "summary"},
        }
    ]

    response = client.get("/api/v1/reports", headers=_headers(str(user_id)))

    assert response.status_code == 200
    assert response.json() == {
        "reports": [
            {
                "id": str(report_id),
                "financial_profile_id": str(profile_id),
                "created_at": "2026-07-22T10:00:00Z",
            }
        ]
    }
    mock_reports_repo_cls.return_value.list_by_user_id.assert_called_once_with(user_id=user_id)


@patch("app.main.ReportsRepository")
def test_get_report_returns_owned_report(mock_reports_repo_cls):
    user_id, report_id, profile_id = uuid4(), uuid4(), uuid4()
    mock_reports_repo_cls.return_value.get_by_id.return_value = {
        "id": str(report_id),
        "user_id": str(user_id),
        "financial_profile_id": str(profile_id),
        "created_at": "2026-07-22T10:00:00+00:00",
        "content": {"executive_summary": "summary"},
    }

    response = client.get(f"/api/v1/reports/{report_id}", headers=_headers(str(user_id)))

    assert response.status_code == 200
    assert response.json()["content"] == {"executive_summary": "summary"}
    mock_reports_repo_cls.return_value.get_by_id.assert_called_once_with(
        report_id=report_id, user_id=user_id
    )


@patch("app.main.ReportsRepository")
def test_get_report_returns_404_when_missing_or_not_owned(mock_reports_repo_cls):
    user_id, report_id = uuid4(), uuid4()
    mock_reports_repo_cls.return_value.get_by_id.return_value = None

    response = client.get(f"/api/v1/reports/{report_id}", headers=_headers(str(user_id)))

    assert response.status_code == 404
    assert response.json()["error"] == "Report not found"
    mock_reports_repo_cls.return_value.get_by_id.assert_called_once_with(
        report_id=report_id, user_id=user_id
    )
