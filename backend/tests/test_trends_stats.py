"""Tests for trends, stats, and search endpoints."""
import secrets

import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_bar(client: AsyncClient, admin_headers: dict, slug: str | None = None) -> dict:
    slug = slug or f"ts-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Trends Bar", "slug": slug, "content_schema": {}, "join_mode": "open"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _join_and_post(
    client: AsyncClient,
    admin_headers: dict,
    agent_headers: dict,
    slug: str,
    title: str = "Sample Post",
) -> dict:
    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=agent_headers)
    r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": title, "summary": "A summary text for searching.", "content": {"body": "content"}},
        headers=agent_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


# ── Trends ─────────────────────────────────────────────────────────────────────

async def test_trends_returns_data(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar(client, admin_headers)
    await _join_and_post(client, admin_headers, agent_headers, bar["slug"])

    r = await client.get("/api/v1/trends?period=24h&top=5")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "bars" in data
    assert "posts" in data
    assert "agents" in data
    assert data["period"] == "24h"


async def test_trends_period_7d(client: AsyncClient):
    r = await client.get("/api/v1/trends?period=7d&top=3")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["period"] == "7d"


async def test_trends_all_time(client: AsyncClient):
    r = await client.get("/api/v1/trends?period=all")
    assert r.status_code == 200


# ── Platform Stats ─────────────────────────────────────────────────────────────

async def test_platform_stats(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar(client, admin_headers)
    await _join_and_post(client, admin_headers, agent_headers, bar["slug"])

    r = await client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "total_posts" in data
    assert "total_agents" in data
    assert "total_users" in data
    assert "total_coins_circulating" in data
    assert "bars" in data
    assert data["total_posts"] >= 1
    assert data["total_agents"] >= 1


async def test_platform_stats_no_auth_required(client: AsyncClient):
    r = await client.get("/api/v1/stats")
    assert r.status_code == 200


# ── Bar Stats ──────────────────────────────────────────────────────────────────

async def test_bar_stats(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar = await _create_bar(client, admin_headers)
    await _join_and_post(client, admin_headers, agent_headers, bar["slug"])

    r = await client.get(f"/api/v1/bars/{bar['slug']}/stats")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["slug"] == bar["slug"]
    assert data["total_posts"] >= 1
    assert data["member_count"] >= 1


async def test_bar_stats_not_found(client: AsyncClient):
    r = await client.get("/api/v1/bars/nonexistent-bar/stats")
    assert r.status_code == 404


# ── Global Search ──────────────────────────────────────────────────────────────

async def test_search_no_auth(client: AsyncClient):
    """Search without fulltext (SQLite doesn't support tsvector)."""
    r = await client.get("/api/v1/posts/search?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


async def test_search_with_agent_auth(client: AsyncClient, agent_headers: dict):
    r = await client.get("/api/v1/posts/search?limit=5", headers=agent_headers)
    assert r.status_code == 200


async def test_search_returns_pagination(client: AsyncClient):
    r = await client.get("/api/v1/posts/search?limit=5")
    assert r.status_code == 200
    meta = r.json()["meta"]
    assert "page" in meta
    assert "cursor" in meta["page"]
    assert "has_more" in meta["page"]


async def test_search_filter_by_entity(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    # Need knowledge+public bar for review/voting to work
    slug = f"ts-bar-{secrets.token_hex(4)}"
    r_bar = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Search Bar", "slug": slug, "content_schema": {}, "join_mode": "open",
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    assert r_bar.status_code == 201
    bar = r_bar.json()["data"]
    entity = f"ent-{secrets.token_hex(4)}"

    await client.post(f"/api/v1/bars/{bar['slug']}/join", json={}, headers=agent_headers)

    # Set review threshold to 1 so a single vote approves
    await client.put(
        f"/api/v1/admin/configs/bars/{bar['slug']}/review_threshold",
        json={"value": 1},
        headers=admin_headers,
    )

    r_post = await client.post(
        f"/api/v1/bars/{bar['slug']}/posts",
        json={"title": "Searchable Post", "entity_id": entity, "summary": "Some text", "content": {"body": "x"}},
        headers=agent_headers,
    )
    assert r_post.status_code == 201
    post = r_post.json()["data"]

    # Approve via a different agent's vote
    r_voter = await client.post("/api/v1/agents/register", json={"name": f"Voter-{secrets.token_hex(3)}"})
    voter_h = {"Authorization": f"Bearer {r_voter.json()['data']['api_key']}"}
    vote_r = await client.post(f"/api/v1/reviews/{post['id']}/vote", json={"verdict": "approve"}, headers=voter_h)
    assert vote_r.status_code == 200

    r = await client.get(f"/api/v1/posts/search?entity_id={entity}&limit=5")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) >= 1
    assert all(item["entity_id"] == entity for item in items)


# ── Admin Extended ─────────────────────────────────────────────────────────────

async def test_admin_list_agents(client: AsyncClient, admin_headers: dict, registered_agent: dict):
    r = await client.get("/api/v1/admin/agents", headers=admin_headers)
    assert r.status_code == 200
    agents = r.json()["data"]
    assert isinstance(agents, list)
    assert len(agents) >= 1
    ids = [a["id"] for a in agents]
    assert registered_agent["agent_id"] in ids


async def test_admin_list_agents_filter_status(client: AsyncClient, admin_headers: dict, registered_agent: dict):
    r = await client.get("/api/v1/admin/agents?status=active", headers=admin_headers)
    assert r.status_code == 200
    for agent in r.json()["data"]:
        assert agent["status"] == "active"


async def test_admin_update_agent_status(client: AsyncClient, admin_headers: dict, registered_agent: dict):
    agent_id = registered_agent["agent_id"]
    r = await client.put(
        f"/api/v1/admin/agents/{agent_id}/status",
        json={"status": "suspended"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "suspended"


async def test_admin_update_agent_invalid_status(client: AsyncClient, admin_headers: dict, registered_agent: dict):
    r = await client.put(
        f"/api/v1/admin/agents/{registered_agent['agent_id']}/status",
        json={"status": "invalid_status"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_admin_update_bar(client: AsyncClient, admin_headers: dict):
    bar = await _create_bar(client, admin_headers)
    r = await client.put(
        f"/api/v1/admin/bars/{bar['slug']}",
        json={"name": "Updated Name", "description": "Updated desc"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Updated Name"


async def test_admin_delete_bar(client: AsyncClient, admin_headers: dict):
    bar = await _create_bar(client, admin_headers)
    r = await client.delete(f"/api/v1/admin/bars/{bar['slug']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True

    r2 = await client.get(f"/api/v1/bars/{bar['slug']}")
    assert r2.status_code == 404


async def test_admin_bar_configs(client: AsyncClient, admin_headers: dict):
    bar = await _create_bar(client, admin_headers)
    r = await client.get(f"/api/v1/admin/configs/bars/{bar['slug']}", headers=admin_headers)
    assert r.status_code == 200
    configs = r.json()["data"]
    assert isinstance(configs, dict)


async def test_admin_update_bar_config(client: AsyncClient, admin_headers: dict):
    bar = await _create_bar(client, admin_headers)
    r = await client.put(
        f"/api/v1/admin/configs/bars/{bar['slug']}/post_cost",
        json={"value": 10},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["value"] == 10


async def test_admin_activity_log(client: AsyncClient, admin_headers: dict, registered_agent: dict):
    r = await client.get("/api/v1/admin/activity-log", headers=admin_headers)
    assert r.status_code == 200
    logs = r.json()["data"]
    assert isinstance(logs, list)
    if logs:
        assert "event_type" in logs[0]
        assert "created_at" in logs[0]


async def test_admin_activity_log_filter(client: AsyncClient, admin_headers: dict, registered_agent: dict):
    r = await client.get(
        "/api/v1/admin/activity-log?event_type=agent_register",
        headers=admin_headers,
    )
    assert r.status_code == 200
    for log in r.json()["data"]:
        assert log["event_type"] == "agent_register"


# ── Owner Config ───────────────────────────────────────────────────────────────

async def test_owner_update_bar_config(client: AsyncClient, premium_user_headers: dict, premium_user: dict):
    slug = f"cfg-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/owner/bars",
        json={"name": "Config Bar", "slug": slug, "content_schema": {}, "join_mode": "open", "visibility": "private"},
        headers=premium_user_headers,
    )
    assert r.status_code == 201

    # Owner can update whitelisted configs (coin_enabled, review_enabled)
    r2 = await client.put(
        f"/api/v1/owner/bars/{slug}/configs/review_enabled",
        json={"value": True},
        headers=premium_user_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["key"] == "review_enabled"


    # SSE streaming tests are skipped in SQLite tests since they require
    # a long-running connection; SSE is verified via manual curl testing.
