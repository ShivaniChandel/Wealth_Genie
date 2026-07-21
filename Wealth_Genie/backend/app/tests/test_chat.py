import datetime
import os
from unittest.mock import AsyncMock, patch
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


@patch("app.main.get_llm_provider")
@patch("app.main.ReportsRepository")
@patch("app.main.FinancialProfilesRepository")
def test_chat_uses_owned_persisted_profile_and_report(
    mock_profiles_repo_cls, mock_reports_repo_cls, mock_get_llm_provider
):
    user_id, profile_id, report_id = uuid4(), uuid4(), uuid4()
    profile = {"summary": {"total_monthly_income": "10000"}}
    report = {"executive_summary": "Build emergency savings."}
    mock_profiles_repo_cls.return_value.get_latest_by_user_id.return_value = {
        "id": str(profile_id),
        "profile_json": profile,
    }
    mock_reports_repo_cls.return_value.list_by_user_id.return_value = [
        {"id": str(report_id), "content": report}
    ]
    provider = mock_get_llm_provider.return_value
    provider.answer_financial_question = AsyncMock(return_value="You have monthly income of 10000.")

    response = client.post(
        "/api/v1/chat",
        headers=_headers(str(user_id)),
        json={
            "message": "What is my monthly income?",
            "conversation_history": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "You have monthly income of 10000.",
        "financial_profile_id": str(profile_id),
    }
    mock_profiles_repo_cls.return_value.get_latest_by_user_id.assert_called_once_with(user_id=user_id)
    mock_reports_repo_cls.return_value.list_by_user_id.assert_called_once_with(user_id=user_id)
    provider.answer_financial_question.assert_awaited_once_with(
        message="What is my monthly income?",
        financial_profile=profile,
        report=report,
        conversation_history=[{"role": "user", "content": "Hello"}],
    )


@patch("app.main.get_llm_provider")
@patch("app.main.ReportsRepository")
@patch("app.main.FinancialProfilesRepository")
def test_chat_returns_404_for_missing_or_non_owned_profile(
    mock_profiles_repo_cls, mock_reports_repo_cls, mock_get_llm_provider
):
    user_id = uuid4()
    mock_profiles_repo_cls.return_value.get_latest_by_user_id.return_value = None

    response = client.post(
        "/api/v1/chat",
        headers=_headers(str(user_id)),
        json={"message": "Question"},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "Financial profile not found"
    mock_reports_repo_cls.return_value.list_by_user_id.assert_not_called()
    mock_get_llm_provider.assert_not_called()
