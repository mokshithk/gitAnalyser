import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.security import hash_password, verify_password, create_access_token, decode_access_token

client = TestClient(app)

def test_password_hashing():
    pwd = "student_secret_pass_123"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h) is True
    assert verify_password("wrong_password", h) is False

def test_jwt_token_roundtrip():
    data = {"sub": "42", "role": "user", "email": "test@example.com"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["role"] == "user"
    assert decoded["email"] == "test@example.com"

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["database"] == "healthy"

def test_user_register_and_login():
    import uuid
    rand_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "MySecretPassword123"

    # Register
    reg_res = client.post("/api/auth/register", json={
        "email": rand_email,
        "password": pwd,
        "role": "user"
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == rand_email
    token = reg_data["access_token"]

    # Access /me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == rand_email

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": rand_email,
        "password": pwd
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Wrong password login
    bad_login = client.post("/api/auth/login", json={
        "email": rand_email,
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401
