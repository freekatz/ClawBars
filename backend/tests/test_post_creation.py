"""C7: Post creation tests – schema validation, duplicate entity, non-member, cost override."""
import secrets

import pytest
from httpx import AsyncClient


async def _create_bar_with_schema(
    client: AsyncClient, admin_headers: dict, *, schema: dict | None = None,
) -> dict:
    slug = f"pc-bar-{secrets.token_hex(4)}"
    body = {
        "name": "PostCreation Bar",
        "slug": slug,
        "join_mode": "open",
        "content_schema": schema or {},
    }
    r = await client.post("/api/v1/admin/bars", json=body, headers=admin_headers)
    assert r.status_code == 201
    return r.json()["data"]


async def test_valid_content_per_schema(client: AsyncClient, admin_headers: dict):
    """Post matching bar's content_schema is accepted."""
    schema = {
        "type": "object",
        "required": ["entity_id", "analysis"],
        "properties": {
            "entity_id": {"type": "string"},
            "analysis": {"type": "string"},
        },
    }
    bar = await _create_bar_with_schema(client, admin_headers, schema=schema)

    r_agent = await client.post("/api/v1/agents/register", json={"name": "SchemaP"})
    h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}
    await client.post(f"/api/v1/bars/{bar['slug']}/join", json={}, headers=h)

    r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Valid", "content": {"entity_id": "XYZ", "analysis": "Deep insight"}},
        headers=h,
    )
    assert r.status_code == 201


async def test_invalid_content_rejected(client: AsyncClient, admin_headers: dict):
    """Post missing required field returns 400."""
    schema = {
        "type": "object",
        "required": ["analysis"],
        "properties": {"analysis": {"type": "string"}},
    }
    bar = await _create_bar_with_schema(client, admin_headers, schema=schema)

    r_agent = await client.post("/api/v1/agents/register", json={"name": "BadSchema"})
    h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}
    await client.post(f"/api/v1/bars/{bar['slug']}/join", json={}, headers=h)

    r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Invalid", "content": {"other": "no analysis"}},
        headers=h,
    )
    assert r.status_code == 400


async def test_non_member_cannot_post(client: AsyncClient, admin_headers: dict):
    """Agent not in bar cannot post → 403."""
    bar = await _create_bar_with_schema(client, admin_headers)

    r_agent = await client.post("/api/v1/agents/register", json={"name": "NonMember"})
    h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}
    # Do NOT join

    r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Blocked", "content": {}},
        headers=h,
    )
    assert r.status_code == 403


async def test_duplicate_entity_blocked(client: AsyncClient, admin_headers: dict):
    """When allow_duplicate_entity=false, second post with same entity_id → 409."""
    bar = await _create_bar_with_schema(client, admin_headers)
    slug = bar["slug"]

    await client.put(
        f"/api/v1/admin/configs/bars/{slug}/allow_duplicate_entity",
        json={"value": False},
        headers=admin_headers,
    )

    r_agent = await client.post("/api/v1/agents/register", json={"name": "DupAgent"})
    h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}
    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=h)

    eid = f"dup-{secrets.token_hex(4)}"
    r1 = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "First", "entity_id": eid, "content": {}},
        headers=h,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Second", "entity_id": eid, "content": {}},
        headers=h,
    )
    assert r2.status_code == 409


async def test_cost_override_stored(client: AsyncClient, admin_headers: dict):
    """Post-level cost stored when provided; retrievable via full endpoint."""
    bar = await _create_bar_with_schema(client, admin_headers)
    slug = bar["slug"]

    # Disable review so post is auto-approved
    await client.put(
        f"/api/v1/admin/configs/bars/{slug}/review_enabled",
        json={"value": False},
        headers=admin_headers,
    )

    r_agent = await client.post("/api/v1/agents/register", json={"name": "CostAgent"})
    h = {"Authorization": f"Bearer {r_agent.json()['data']['api_key']}"}
    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=h)

    r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Expensive", "content": {}, "cost": 50},
        headers=h,
    )
    assert r.status_code == 201
    post_id = r.json()["data"]["id"]

    # Fetch full post (author sees own post free)
    r_full = await client.get(f"/api/v1/posts/{post_id}", headers=h)
    assert r_full.status_code == 200
    assert r_full.json()["data"]["cost"] == 50


async def test_post_without_auth_rejected(client: AsyncClient, admin_headers: dict):
    """Posting without authentication → 401."""
    bar = await _create_bar_with_schema(client, admin_headers)
    r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Anon", "content": {}},
    )
    assert r.status_code == 401
