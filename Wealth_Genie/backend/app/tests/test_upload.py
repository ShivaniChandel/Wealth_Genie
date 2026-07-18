import pytest
import jwt
import datetime
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import MagicMock, patch

# Set up test environment variables
import os
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-key-12345"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"

from app.main import app, supabase_client
from app.config import settings

client = TestClient(app)

def generate_test_token(user_id: str, email: str):
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

# Test upload validation failure: non-PDF file
def test_upload_non_pdf():
    user_id = str(uuid4())
    token = generate_test_token(user_id, "test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send a text file
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    data = {"document_type": "bank_statement"}
    
    response = client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert response.status_code == 400
    assert response.json()["error"] == "Only PDF documents are allowed."

# Test upload validation failure: invalid document type
def test_upload_invalid_document_type():
    user_id = str(uuid4())
    token = generate_test_token(user_id, "test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send a pdf with invalid type
    files = {"file": ("test.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
    data = {"document_type": "invalid_type"}
    
    response = client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert response.status_code == 400
    assert "Invalid document type" in response.json()["error"]

# Test upload validation failure: size exceeds 10MB
def test_upload_file_too_large():
    user_id = str(uuid4())
    token = generate_test_token(user_id, "test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a dummy large payload (10.1 MB)
    large_bytes = b"%PDF-1.4 " + b"0" * (10 * 1024 * 1024 + 100)
    files = {"file": ("large.pdf", large_bytes, "application/pdf")}
    data = {"document_type": "bank_statement"}
    
    response = client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert response.status_code == 400
    assert "exceeds the maximum limit of 10MB" in response.json()["error"]

# Test successful upload with mocked Supabase responses
@patch("app.main.supabase_client")
def test_upload_success(mock_supabase):
    user_id = str(uuid4())
    token = generate_test_token(user_id, "test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup mock behaviors
    mock_storage = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage
    mock_storage.upload.return_value = {"path": "dummy-path"}
    
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = MagicMock()
    
    files = {"file": ("test.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
    data = {"document_type": "bank_statement"}
    
    response = client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    
    assert response.status_code == 200
    res_data = response.json()
    assert "document_id" in res_data
    assert res_data["status"] == "uploaded"
    
    # Verify storage upload and DB insert were called
    mock_supabase.storage.from_.assert_called_with("documents")
    mock_supabase.table.assert_called_with("documents")
