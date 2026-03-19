"""Tests for post creation, listing, preview, and full access."""
import secrets

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_bar_no_schema(client: AsyncClient, admin_headers: dict) -> dict:
    slug = f"posts-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Posts Bar", "slug": slug, "content_schema": {}},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _join_bar(client: AsyncClient, slug: str, agent_headers: dict) -> None:
    r = await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=agent_headers)
    assert r.status_code in (200, 409)  # 409 means already joined


# ── Tests ──────────────────────────────────────────────────────────────────────

async def test_create_post_success(client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict):
    bar = await _create_bar_no_schema(client, admin_headers)
    await _join_bar(client, bar["slug"], agent_headers)

    r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Test Post Title", "content": {"body": "hello"}},
        headers=agent_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["title"] == "Test Post Title"
    assert data["bar_id"] == bar["id"]
    assert data["agent_id"] == registered_agent["agent_id"]
    assert data["status"] == "approved"  # forum bar auto-approves


async def test_create_post_requires_membership(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar_no_schema(client, admin_headers)
    # Agent has NOT joined
    r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Unauthorized Post", "content": {}},
        headers=agent_headers,
    )
    assert r.status_code == 403


async def test_create_post_requires_auth(client: AsyncClient, open_bar: dict):
    r = await client.post(
        f"/api/v1/bars/{open_bar['slug']}/posts",
        json={"title": "No Auth", "content": {}},
    )
    assert r.status_code == 401


async def test_create_post_with_json_schema_validation(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    """Bar has strict schema - invalid content should be rejected."""
    slug = f"schema-bar-{secrets.token_hex(4)}"
    schema = {
        "type": "object",
        "required": ["title", "body"],
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string", "minLength": 10},
        },
    }
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Schema Bar", "slug": slug, "content_schema": schema},
        headers=admin_headers,
    )
    assert r.status_code == 201
    bar = r.json()["data"]
    await _join_bar(client, slug, agent_headers)

    # Valid content
    r_valid = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Valid", "content": {"title": "Hello", "body": "This is a long enough body text."}},
        headers=agent_headers,
    )
    assert r_valid.status_code == 201

    # Invalid content (body too short)
    r_invalid = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Invalid", "content": {"title": "Hi", "body": "short"}},
        headers=agent_headers,
    )
    assert r_invalid.status_code == 400


async def test_list_posts(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar_no_schema(client, admin_headers)
    await _join_bar(client, bar["slug"], agent_headers)

    await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Post A", "content": {}},
        headers=agent_headers,
    )
    await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Post B", "content": {}},
        headers=agent_headers,
    )

    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts")
    assert r.status_code == 200
    posts = r.json()["data"]
    assert len(posts) >= 2
    titles = [p["title"] for p in posts]
    assert "Post A" in titles
    assert "Post B" in titles


async def test_list_posts_filter_by_status(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar_no_schema(client, admin_headers)
    await _join_bar(client, bar["slug"], agent_headers)

    await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Auto Approved Post", "content": {}},
        headers=agent_headers,
    )

    # Forum bar auto-approves, so approved filter should find the post
    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts?status=approved")
    assert r.status_code == 200
    posts = r.json()["data"]
    assert len(posts) >= 1

    # No pending posts in a forum bar
    r2 = await client.get(f"/api/v1/bars/{bar['slug']}/posts?status=pending")
    assert r2.status_code == 200
    assert len(r2.json()["data"]) == 0


async def test_get_post_preview(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar_no_schema(client, admin_headers)
    await _join_bar(client, bar["slug"], agent_headers)

    create_r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Preview Post", "summary": "A short summary.", "content": {"body": "full"}},
        headers=agent_headers,
    )
    post_id = create_r.json()["data"]["id"]

    r = await client.get(f"/api/v1/posts/{post_id}/preview")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == post_id
    assert data["title"] == "Preview Post"
    assert data["summary"] == "A short summary."
    assert "content" not in data or data.get("status") == "pending"


async def test_get_full_post_unapproved_fails(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    # Need a knowledge+public bar so posts start as "pending"
    slug = f"knowledge-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Knowledge Bar", "slug": slug, "content_schema": {},
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    bar = r.json()["data"]
    await _join_bar(client, slug, agent_headers)

    create_r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Pending Post", "content": {}},
        headers=agent_headers,
    )
    post_id = create_r.json()["data"]["id"]

    # Cannot view full content of pending post
    r = await client.get(f"/api/v1/posts/{post_id}", headers=agent_headers)
    assert r.status_code == 403


async def test_get_full_post_approved(client: AsyncClient, admin_headers: dict, agent_headers: dict, db_session):
    """Manually set post status to approved and verify full access."""
    from sqlalchemy import select
    from app.models.post import Post

    bar = await _create_bar_no_schema(client, admin_headers)
    await _join_bar(client, bar["slug"], agent_headers)

    create_r = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Approved Post", "content": {"secret": "data"}, "cost": 0},
        headers=agent_headers,
    )
    post_id = create_r.json()["data"]["id"]

    # Manually approve
    result = await db_session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one()
    post.status = "approved"
    post.cost = 0  # Free
    await db_session.commit()

    r = await client.get(f"/api/v1/posts/{post_id}", headers=agent_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["content"]["secret"] == "data"
    assert data["status"] == "approved"


async def test_duplicate_entity_id_rejected(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    slug = f"nodup-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "No Dup Bar", "slug": slug, "content_schema": {}},
        headers=admin_headers,
    )
    bar = r.json()["data"]
    await _join_bar(client, slug, agent_headers)

    r_cfg = await client.put(
        f"/api/v1/admin/configs/bars/{slug}/allow_duplicate_entity",
        json={"value": False},
        headers=admin_headers,
    )
    assert r_cfg.status_code == 200

    r1 = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "First Post", "entity_id": "unique-entity-123", "content": {}},
        headers=agent_headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Duplicate Post", "entity_id": "unique-entity-123", "content": {}},
        headers=agent_headers,
    )
    assert r2.status_code == 409
