from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.config import settings
from app.models import User
from scripts.seed import seed_demo_user


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.test"


def test_register_success_normalizes_email(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "  NewUser@Example.Test ", "password": "Password123", "full_name": "New User"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "newuser@example.test"
    assert set(response.json()) == {"id", "email", "full_name"}


def test_register_duplicate_email_returns_conflict(client) -> None:
    email = unique_email("duplicate")
    payload = {"email": email, "password": "Password123", "full_name": "First"}

    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json={**payload, "email": email.upper()})

    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "conflict", "message": "Email already registered"}
    }


def test_register_short_password_returns_validation_error(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email("short"), "password": "short", "full_name": "Short"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_login_success_and_auth_me(client) -> None:
    email = unique_email("login")
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123", "full_name": "Login User"},
    )

    login = client.post(
        "/api/v1/auth/login",
        json={"email": f"  {email.upper()} ", "password": "Password123"},
    )

    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60
    assert body["user"]["email"] == email
    assert "password_hash" not in body["user"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert me.status_code == 200
    assert me.json()["email"] == email


def test_wrong_password_and_unknown_email_have_same_response(client) -> None:
    email = unique_email("same-response")
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123", "full_name": "Same Response"},
    )

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword123"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email("unknown"), "password": "WrongPassword123"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_expired_token_is_rejected(client) -> None:
    token = create_access_token(
        subject=str(uuid4()),
        expires_delta=timedelta(seconds=-1),
        issued_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_tampered_token_is_rejected(client) -> None:
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "wrong-secret",
        algorithm="HS256",
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_missing_token_on_auth_me_is_rejected(client) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_seed_script_is_idempotent(db: Session) -> None:
    first = seed_demo_user(db)
    second = seed_demo_user(db)

    assert first.id == second.id
    assert db.query(User).filter(User.email == "demo@docflow.app").count() == 1
