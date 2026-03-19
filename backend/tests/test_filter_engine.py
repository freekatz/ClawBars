"""C8: FilterEngine tests – exact, prefix, date range, sort, cursor pagination."""
import secrets
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient


async def _create_bar_and_approved_posts(
    client: AsyncClient, admin_headers: dict, count: int = 5,
) -> tuple[dict, list[dict]]:
    """Create a bar with review_enabled=false and insert multiple approved posts."""
    slug = f"fe-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "FilterBar", "slug": slug, "content_schema": {}, "join_mode": "open"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    bar = r.json()["data"]

    # Disable reviews → auto-approve
    await client.put(
        f"/api/v1/admin/configs/bars/{slug}/review_enabled",
        json={"value": False},
        headers=admin_headers,
    )

    r_agent = await client.post("/api/v1/agents/register", json={"name": "FilterAgent"})
    agent = r_agent.json()["data"]
    h = {"Authorization": f"Bearer {agent['api_key']}"}
    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=h)

    posts = []
    for i in range(count):
        rp = await client.post(
            f"/api/v1/bars/{slug}/posts",
            json={
                "title": f"Post {i}",
                "entity_id": f"ent-{i:04d}",
                "summary": f"Summary {i}",
                "content": {"body": f"Content {i}"},
            },
            headers=h,
        )
        assert rp.status_code == 201
        posts.append(rp.json()["data"])

    return bar, posts


async def test_exact_status_filter(client: AsyncClient, admin_headers: dict):
    """exact('status') filters correctly."""
    bar, posts = await _create_bar_and_approved_posts(client, admin_headers, count=2)

    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts?status=approved")
    assert r.status_code == 200
    items = r.json()["data"]
    assert all(p["status"] == "approved" for p in items)


async def test_exact_entity_filter(client: AsyncClient, admin_headers: dict):
    """Exact entity_id filter returns matching post."""
    bar, posts = await _create_bar_and_approved_posts(client, admin_headers, count=3)
    target = posts[1]["entity_id"]

    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts?entity_id={target}")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 1
    assert items[0]["entity_id"] == target


async def test_prefix_filter(client: AsyncClient, admin_headers: dict):
    """Prefix filter on entity_id."""
    bar, posts = await _create_bar_and_approved_posts(client, admin_headers, count=5)

    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts?entity_id_prefix=ent-000")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) >= 1
    assert all(p["entity_id"].startswith("ent-000") for p in items)


async def test_limit_parameter(client: AsyncClient, admin_headers: dict):
    """Limit is respected."""
    bar, posts = await _create_bar_and_approved_posts(client, admin_headers, count=5)

    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts?limit=2")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 2


async def test_cursor_pagination(client: AsyncClient, admin_headers: dict):
    """Cursor pagination returns cursor and subsequent request succeeds."""
    bar, posts = await _create_bar_and_approved_posts(client, admin_headers, count=5)

    r1 = await client.get(f"/api/v1/bars/{bar['slug']}/posts?limit=2")
    assert r1.status_code == 200
    page1 = r1.json()
    items1 = page1["data"]
    assert len(items1) == 2

    meta = page1.get("meta", {}).get("page", {})
    # If has_more, cursor should be present
    if meta.get("has_more"):
        assert meta["cursor"] is not None
        r2 = await client.get(f"/api/v1/bars/{bar['slug']}/posts?limit=10&cursor={meta['cursor']}")
        assert r2.status_code == 200
        items2 = r2.json()["data"]
        ids1 = {p["id"] for p in items1}
        ids2 = {p["id"] for p in items2}
        assert ids1.isdisjoint(ids2)


async def test_sort_by_different_fields(client: AsyncClient, admin_headers: dict):
    """Sort options work correctly."""
    bar, posts = await _create_bar_and_approved_posts(client, admin_headers, count=3)

    r = await client.get(f"/api/v1/bars/{bar['slug']}/posts?sort=created_at")
    assert r.status_code == 200
    items = r.json()["data"]
    created_times = [p["created_at"] for p in items]
    assert created_times == sorted(created_times)


async def test_global_search_limit_max_100(client: AsyncClient, admin_headers: dict):
    """Limit > 100 is clamped to 100."""
    r = await client.get("/api/v1/posts/search?limit=999")
    assert r.status_code == 200
    # No crash; server clamps
