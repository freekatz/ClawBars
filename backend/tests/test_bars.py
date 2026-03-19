"""Tests for bar listing, details, joining, and member management."""
import secrets

import pytest
from httpx import AsyncClient


async def test_list_bars_empty(client: AsyncClient):
    r = await client.get("/api/v1/bars")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


async def test_list_bars_returns_created_bars(client: AsyncClient, open_bar: dict):
    r = await client.get("/api/v1/bars")
    assert r.status_code == 200
    slugs = [b["slug"] for b in r.json()["data"]]
    assert open_bar["slug"] in slugs


async def test_get_bar_by_slug(client: AsyncClient, open_bar: dict):
    r = await client.get(f"/api/v1/bars/{open_bar['slug']}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["slug"] == open_bar["slug"]
    assert data["owner_type"] == "official"
    assert "content_schema" in data


async def test_get_bar_not_found(client: AsyncClient):
    r = await client.get("/api/v1/bars/nonexistent-bar-slug")
    assert r.status_code == 404


async def test_join_open_bar(client: AsyncClient, open_bar: dict, agent_headers: dict, registered_agent: dict):
    r = await client.post(
        f"/api/v1/bars/{open_bar['slug']}/join",
        json={},
        headers=agent_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["bar_id"] == open_bar["id"]
    assert data["agent_id"] == registered_agent["agent_id"]
    assert data["role"] == "member"


async def test_join_bar_requires_auth(client: AsyncClient, open_bar: dict):
    r = await client.post(f"/api/v1/bars/{open_bar['slug']}/join", json={})
    assert r.status_code == 401


async def test_join_bar_twice_returns_conflict(client: AsyncClient, open_bar: dict, agent_headers: dict):
    await client.post(
        f"/api/v1/bars/{open_bar['slug']}/join", json={}, headers=agent_headers
    )
    r = await client.post(
        f"/api/v1/bars/{open_bar['slug']}/join", json={}, headers=agent_headers
    )
    assert r.status_code == 409


async def test_list_members(client: AsyncClient, open_bar: dict, agent_headers: dict):
    await client.post(
        f"/api/v1/bars/{open_bar['slug']}/join", json={}, headers=agent_headers
    )
    r = await client.get(f"/api/v1/bars/{open_bar['slug']}/members")
    assert r.status_code == 200
    members = r.json()["data"]
    assert isinstance(members, list)
    assert len(members) >= 1


async def test_invite_only_bar_requires_token(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    slug = f"invite-bar-{secrets.token_hex(4)}"
    create_r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Invite Bar", "slug": slug, "join_mode": "invite_only"},
        headers=admin_headers,
    )
    assert create_r.status_code == 201

    r = await client.post(
        f"/api/v1/bars/{slug}/join",
        json={},
        headers=agent_headers,
    )
    assert r.status_code == 403
