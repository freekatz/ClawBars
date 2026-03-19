"""Tests for user registration, login, and profile endpoints."""
import secrets

import pytest
from httpx import AsyncClient


def _email():
    return f"user_{secrets.token_hex(4)}@test.local"


async def test_register_user_success(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": _email(), "password": "securepass123", "name": "Alice"},
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["id"]
    assert data["role"] == "free"
    assert data["status"] == "active"


async def test_register_duplicate_email(client: AsyncClient):
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123", "name": "Alice"},
    )
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123", "name": "Alice2"},
    )
    assert r.status_code == 409


async def test_register_password_too_short(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": _email(), "password": "short", "name": "Bob"},
    )
    assert r.status_code == 400


async def test_login_success(client: AsyncClient):
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "mypassword123", "name": "Carol"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "mypassword123"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correctpass123", "name": "Dave"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )
    assert r.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.local", "password": "password123"},
    )
    assert r.status_code == 401


async def test_get_me_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_get_me_success(client: AsyncClient, user_headers: dict, registered_user: dict):
    r = await client.get("/api/v1/auth/me", headers=user_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["email"] == registered_user["email"]
    assert data["role"] == "free"


async def test_update_profile(client: AsyncClient, user_headers: dict):
    r = await client.put(
        "/api/v1/auth/me",
        json={"name": "Updated Name"},
        headers=user_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Updated Name"


async def test_refresh_token(client: AsyncClient):
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "Eve"},
    )
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    refresh_token = login_r.json()["data"]["refresh_token"]

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]


async def test_refresh_with_access_token_fails(client: AsyncClient):
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "Frank"},
    )
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    access_token = login_r.json()["data"]["access_token"]

    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert r.status_code == 401
