import pytest
import jwt
import datetime
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import MagicMock, patch
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import serialization

import os
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-key-12345"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"

from app.main import app
from app.config import settings

client = TestClient(app)


def generate_test_token(user_id: str, email: str, role: str = "authenticated", aud: str = "authenticated", expired: bool = False):
    exp_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    if expired:
        exp_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "aud": aud,
        "exp": exp_time
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def test_verify_token_success():
    user_id = str(uuid4())
    email = "test@example.com"
    token = generate_test_token(user_id, email)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/verify-token", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["email"] == email
    assert data["aud"] == "authenticated"
    assert data["role"] == "authenticated"


def test_verify_token_expired():
    user_id = str(uuid4())
    email = "test@example.com"
    token = generate_test_token(user_id, email, expired=True)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/verify-token", headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert data["error"] == "Token has expired"
    assert data["status_code"] == 401


def test_verify_token_invalid_role():
    user_id = str(uuid4())
    email = "test@example.com"
    token = generate_test_token(user_id, email, role="anon")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/verify-token", headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "Invalid token" in data["error"]
    assert data["status_code"] == 401


def test_verify_token_invalid_aud():
    user_id = str(uuid4())
    email = "test@example.com"
    token = generate_test_token(user_id, email, aud="invalid-audience")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/verify-token", headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "audience" in data["error"].lower()
    assert data["status_code"] == 401


def test_verify_token_missing_header():
    response = client.get("/api/v1/auth/verify-token")
    assert response.status_code == 401
    data = response.json()
    assert data["status_code"] == 401


def test_logout_success():
    user_id = str(uuid4())
    token = generate_test_token(user_id, "test@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 204


def test_logout_expired():
    user_id = str(uuid4())
    token = generate_test_token(user_id, "test@example.com", expired=True)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 401


def test_logout_missing_header():
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401


def test_verify_token_rs256_mocked():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    user_id = str(uuid4())
    email = "test_rs256@example.com"
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    token = jwt.encode(payload, pem_private, algorithm="RS256")

    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key

    with patch("app.auth.jwks_client.get_signing_key_from_jwt", return_value=mock_signing_key):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/verify-token", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["email"] == email


def test_verify_token_es256_mocked():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    user_id = str(uuid4())
    email = "test_es256@example.com"
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }

    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    token = jwt.encode(payload, pem_private, algorithm="ES256")

    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key

    with patch("app.auth.jwks_client.get_signing_key_from_jwt", return_value=mock_signing_key):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/verify-token", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["email"] == email
