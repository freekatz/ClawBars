"""C10: Auth edge case tests."""
import secrets
import time

import jwt
import pytest
from httpx import AsyncClient

from app.config import settings


async def test_expired_jwt_returns_401(client: AsyncClient):
    """Expired access token → 401."""
    payload = {
        "sub": "fake-user-id",
        "type": "access",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_refresh_with_invalid_token(client: AsyncClient):
    """Refresh with garbage token → 401."""
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-valid-token"},
    )
    assert r.status_code == 401


async def test_password_too_short(client: AsyncClient):
    """Registration with <6 char password rejected."""
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": f"short_{secrets.token_hex(4)}@test.local", "password": "abc", "name": "Short"},
    )
    assert r.status_code in (400, 422)


async def test_duplicate_email_rejected(client: AsyncClient):
    """Second registration with same email → 409."""
    email = f"dup_{secrets.token_hex(4)}@test.local"
    r1 = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "First"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Second"},
    )
    assert r2.status_code == 409


async def test_admin_x_admin_key_works(client: AsyncClient, admin_headers: dict):
    """X-Admin-Key header grants admin access."""
    r = await client.get("/api/v1/admin/configs", headers=admin_headers)
    assert r.status_code == 200


async def test_admin_jwt_works(client: AsyncClient, db_session):
    """Admin user JWT also grants admin access."""
    import bcrypt
    from nanoid import generate
    from app.models.user import User
    from app.middleware.auth import create_access_token

    admin_user = User(
        id=generate(size=21),
        email=f"admin_{secrets.token_hex(4)}@test.local",
        password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
        name="Admin User",
        role="admin",
        status="active",
    )
    db_session.add(admin_user)
    await db_session.commit()

    token = create_access_token(admin_user.id)
    r = await client.get("/api/v1/admin/configs", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


async def test_wrong_admin_key_rejected(client: AsyncClient):
    """Invalid X-Admin-Key → 403."""
    r = await client.get("/api/v1/admin/configs", headers={"X-Admin-Key": "wrong-key"})
    assert r.status_code == 403


async def test_refresh_with_access_token_rejected(client: AsyncClient, registered_user: dict):
    """Cannot use access_token as refresh_token → 401."""
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    access = r_login.json()["data"]["access_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401
