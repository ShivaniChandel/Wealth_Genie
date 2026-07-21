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
@patch("app.main.FinancialProfilesRepository")
@patch("app.main.DocumentsRepository")
def test_dashboard_returns_latest_completed_profile_data(
    mock_documents_repo_cls, mock_profiles_repo_cls, mock_reports_repo_cls
):
    user_id, document_id, profile_id, report_id = uuid4(), uuid4(), uuid4(), uuid4()
    documents_repo = mock_documents_repo_cls.return_value
    profiles_repo = mock_profiles_repo_cls.return_value
    reports_repo = mock_reports_repo_cls.return_value
    documents_repo.count_completed_by_user_id.return_value = 2
    documents_repo.get_latest_completed_by_user_id.return_value = {"id": str(document_id)}
    profiles_repo.get_by_document_id.return_value = {
        "id": str(profile_id),
        "created_at": "2026-07-22T10:00:00+00:00",
        "profile_json": {
            "summary": {
                "total_monthly_income": "10000",
                "total_monthly_expenses": "7000",
                "total_debt": "5000",
                "total_savings": "12000",
                "savings_rate_percent": "30",
                "net_worth_estimate": "7000",
            }
        },
    }
    reports_repo.get_by_financial_profile_id.return_value = {"id": str(report_id)}

    response = client.get("/api/v1/dashboard", headers=_headers(str(user_id)))

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["total_monthly_income"] == "10000"
    assert data["latest_report_id"] == str(report_id)
    assert data["documents_processed"] == 2
    assert data["last_updated"] == "2026-07-22T10:00:00Z"
    documents_repo.count_completed_by_user_id.assert_called_once_with(user_id=user_id)
    documents_repo.get_latest_completed_by_user_id.assert_called_once_with(user_id=user_id)
    profiles_repo.get_by_document_id.assert_called_once_with(
        document_id=document_id, user_id=user_id
    )
    reports_repo.get_by_financial_profile_id.assert_called_once_with(
        financial_profile_id=profile_id, user_id=user_id
    )


@patch("app.main.ReportsRepository")
@patch("app.main.FinancialProfilesRepository")
@patch("app.main.DocumentsRepository")
def test_dashboard_returns_zero_values_without_completed_profile(
    mock_documents_repo_cls, mock_profiles_repo_cls, mock_reports_repo_cls
):
    user_id = uuid4()
    documents_repo = mock_documents_repo_cls.return_value
    documents_repo.count_completed_by_user_id.return_value = 0
    documents_repo.get_latest_completed_by_user_id.return_value = None

    response = client.get("/api/v1/dashboard", headers=_headers(str(user_id)))

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user_id),
        "total_monthly_income": "0",
        "total_monthly_expenses": "0",
        "total_debt": "0",
        "total_savings": "0",
        "savings_rate_percent": "0",
        "net_worth_estimate": "0",
        "latest_report_id": None,
        "documents_processed": 0,
        "last_updated": None,
    }
    mock_profiles_repo_cls.return_value.get_by_document_id.assert_not_called()
    mock_reports_repo_cls.return_value.get_by_financial_profile_id.assert_not_called()
