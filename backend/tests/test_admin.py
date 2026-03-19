"""Tests for admin endpoints."""
import secrets

import pytest
from httpx import AsyncClient


async def test_create_bar_as_admin(client: AsyncClient, admin_headers: dict):
    slug = f"admin-test-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={
            "name": "Official Bar",
            "slug": slug,
            "icon": "🏛️",
            "description": "Admin created bar",
            "content_schema": {},
            "join_mode": "open",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["slug"] == slug
    assert data["owner_type"] == "official"
    assert data["owner_id"] is None


async def test_create_bar_requires_admin(client: AsyncClient, user_headers: dict):
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Sneaky Bar", "slug": f"sneaky-{secrets.token_hex(4)}"},
        headers=user_headers,
    )
    assert r.status_code == 403


async def test_create_bar_invalid_slug(client: AsyncClient, admin_headers: dict):
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Bad Slug", "slug": "Invalid Slug With Spaces!"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_list_users(client: AsyncClient, admin_headers: dict, registered_user: dict):
    r = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert r.status_code == 200
    users = r.json()["data"]
    assert isinstance(users, list)
    emails = [u["email"] for u in users]
    assert registered_user["email"] in emails


async def test_list_users_requires_admin(client: AsyncClient, user_headers: dict):
    r = await client.get("/api/v1/admin/users", headers=user_headers)
    assert r.status_code == 403


async def test_update_user_role(client: AsyncClient, admin_headers: dict, registered_user: dict):
    user_id = registered_user["id"]
    r = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "premium"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["role"] == "premium"
    assert data["id"] == user_id


async def test_update_user_role_invalid(client: AsyncClient, admin_headers: dict, registered_user: dict):
    user_id = registered_user["id"]
    r = await client.put(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "superuser"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_grant_coins(client: AsyncClient, admin_headers: dict, registered_agent: dict, agent_headers: dict):
    agent_id = registered_agent["agent_id"]
    r = await client.post(
        "/api/v1/admin/coins/grant",
        json={"agent_id": agent_id, "amount": 50},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["amount"] == 50

    # Verify balance increased
    bal_r = await client.get("/api/v1/coins/balance", headers=agent_headers)
    assert bal_r.json()["data"]["balance"] >= 50


async def test_get_configs(client: AsyncClient, admin_headers: dict):
    r = await client.get("/api/v1/admin/configs", headers=admin_headers)
    assert r.status_code == 200
    configs = r.json()["data"]
    assert isinstance(configs, dict)
    # Should have default values
    assert "registration_bonus" in configs
    assert "coin_enabled" in configs


async def test_update_config(client: AsyncClient, admin_headers: dict):
    r = await client.put(
        "/api/v1/admin/configs/registration_bonus",
        json={"value": 50},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["key"] == "registration_bonus"
    assert data["value"] == 50

    # Verify it's persisted
    r2 = await client.get("/api/v1/admin/configs", headers=admin_headers)
    assert r2.json()["data"]["registration_bonus"] == 50


async def test_admin_with_x_admin_key(client: AsyncClient, admin_headers: dict):
    r = await client.get(
        "/api/v1/admin/users",
        headers=admin_headers,
    )
    assert r.status_code == 200


async def test_admin_wrong_key_rejected(client: AsyncClient):
    r = await client.get(
        "/api/v1/admin/users",
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert r.status_code == 403
