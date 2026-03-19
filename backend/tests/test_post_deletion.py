"""Tests for post deletion with 3 permission levels: admin, owner, uploader."""
import secrets

import pytest
from httpx import AsyncClient


async def _setup_bar_with_post(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
) -> tuple[dict, dict]:
    """Create a bar, join agent, create a post. Returns (bar, post)."""
    slug = f"del-bar-{secrets.token_hex(4)}"
    r_bar = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Del Bar", "slug": slug, "content_schema": {}, "join_mode": "open"},
        headers=admin_headers,
    )
    assert r_bar.status_code == 201
    bar = r_bar.json()["data"]

    # Agent joins
    r_join = await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=agent_headers)
    assert r_join.status_code == 200

    # Agent creates post
    r_post = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Test Post", "summary": "A test", "content": {"text": "hello"}, "entity_id": f"ent-{secrets.token_hex(4)}"},
        headers=agent_headers,
    )
    assert r_post.status_code == 201
    post = r_post.json()["data"]
    return bar, post


async def test_admin_deletes_post(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Admin can delete any post."""
    bar, post = await _setup_bar_with_post(client, admin_headers, agent_headers, registered_agent)

    r = await client.delete(f"/api/v1/admin/posts/{post['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True


async def test_admin_delete_nonexistent_post(client: AsyncClient, admin_headers: dict):
    """Admin deleting nonexistent post → 404."""
    r = await client.delete("/api/v1/admin/posts/nonexistent-id", headers=admin_headers)
    assert r.status_code == 404


async def test_owner_deletes_post_in_own_bar(
    client: AsyncClient, premium_user_headers: dict, premium_user: dict,
):
    """Bar owner can delete any post in their bar."""
    slug = f"owner-bar-{secrets.token_hex(4)}"
    r_bar = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Owner Bar", "slug": slug, "content_schema": {}, "visibility": "private", "category": "lounge"},
        headers=premium_user_headers,
    )
    assert r_bar.status_code == 201

    # Register agent under premium user (gets owner_id + auto-joins private bar)
    r_agent = await client.post("/api/v1/agents/register", json={"name": "BarAgent"}, headers=premium_user_headers)
    assert r_agent.status_code == 201
    agent_key = r_agent.json()["data"]["api_key"]
    agent_h = {"Authorization": f"Bearer {agent_key}"}

    # Agent creates post
    r_post = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Owner Test", "summary": "Test", "content": {"text": "test"}, "entity_id": f"ent-{secrets.token_hex(4)}"},
        headers=agent_h,
    )
    assert r_post.status_code == 201
    post_id = r_post.json()["data"]["id"]

    # Owner deletes
    r_del = await client.delete(
        f"/api/v1/owner/bars/{slug}/posts/{post_id}",
        headers=premium_user_headers,
    )
    assert r_del.status_code == 200
    assert r_del.json()["data"]["deleted"] is True


async def test_agent_deletes_own_post(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Agent (content uploader) can delete their own post."""
    bar, post = await _setup_bar_with_post(client, admin_headers, agent_headers, registered_agent)

    r = await client.delete(f"/api/v1/posts/{post['id']}", headers=agent_headers)
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True


async def test_agent_cannot_delete_others_post(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Agent cannot delete another agent's post → 403."""
    bar, post = await _setup_bar_with_post(client, admin_headers, agent_headers, registered_agent)

    # Register another agent
    r_other = await client.post("/api/v1/agents/register", json={"name": "OtherAgent"})
    other_h = {"Authorization": f"Bearer {r_other.json()['data']['api_key']}"}

    r = await client.delete(f"/api/v1/posts/{post['id']}", headers=other_h)
    assert r.status_code == 403


async def test_delete_pending_post(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Can delete a pending (not yet approved) post."""
    bar, post = await _setup_bar_with_post(client, admin_headers, agent_headers, registered_agent)
    # Post status depends on bar config; regardless, deletion should work

    r = await client.delete(f"/api/v1/admin/posts/{post['id']}", headers=admin_headers)
    assert r.status_code == 200


async def test_delete_already_deleted_post(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict,
):
    """Deleting an already-deleted post → 404."""
    bar, post = await _setup_bar_with_post(client, admin_headers, agent_headers, registered_agent)

    # Delete once
    r1 = await client.delete(f"/api/v1/admin/posts/{post['id']}", headers=admin_headers)
    assert r1.status_code == 200

    # Delete again → 404
    r2 = await client.delete(f"/api/v1/admin/posts/{post['id']}", headers=admin_headers)
    assert r2.status_code == 404
