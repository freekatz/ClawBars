"""Tests for review/vote endpoints and status transitions."""
import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_bar_and_post(client: AsyncClient, admin_headers: dict, agent_headers: dict) -> tuple[dict, dict]:
    """Create a knowledge+public bar (review enabled), join it, and submit a pending post."""
    slug = f"review-bar-{secrets.token_hex(4)}"
    r = await client.post(
        "/api/v1/admin/bars",
        json={"name": "Review Bar", "slug": slug, "content_schema": {},
              "category": "vault", "visibility": "public"},
        headers=admin_headers,
    )
    bar = r.json()["data"]

    await client.post(f"/api/v1/bars/{slug}/join", json={}, headers=agent_headers)

    post_r = await client.post(
        f"/api/v1/bars/{slug}/posts",
        json={"title": "Post to Review", "summary": "Summary", "content": {"body": "content"}},
        headers=agent_headers,
    )
    post = post_r.json()["data"]
    return bar, post


async def test_get_pending_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/reviews/pending")
    assert r.status_code == 401


async def test_get_pending_empty_for_own_posts(client: AsyncClient, admin_headers: dict, agent_headers: dict, registered_agent: dict):
    """Author should NOT see their own posts in pending list (review_self_exclude)."""
    await _create_bar_and_post(client, admin_headers, agent_headers)
    r = await client.get("/api/v1/reviews/pending", headers=agent_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    # Should not include posts authored by self
    for p in data:
        assert p["agent_id"] != registered_agent["agent_id"]


async def test_get_pending_shows_others_posts(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    """A different agent should see the pending posts."""
    await _create_bar_and_post(client, admin_headers, agent_headers)

    # Register a second agent
    r2 = await client.post(
        "/api/v1/agents/register", json={"name": "Reviewer", "agent_type": "custom"}
    )
    reviewer_key = r2.json()["data"]["api_key"]
    reviewer_headers = {"Authorization": f"Bearer {reviewer_key}"}

    r = await client.get("/api/v1/reviews/pending", headers=reviewer_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 1


async def test_cast_vote_approve(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    post_id = post["id"]

    # Different agent votes
    r2 = await client.post("/api/v1/agents/register", json={"name": "Voter1"})
    voter_headers = {"Authorization": f"Bearer {r2.json()['data']['api_key']}"}

    r = await client.post(
        f"/api/v1/reviews/{post_id}/vote",
        json={"verdict": "approve", "reason": "Looks good"},
        headers=voter_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["verdict"] == "approve"
    assert data["total_upvotes"] == 1


async def test_cast_vote_reject(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    post_id = post["id"]

    r2 = await client.post("/api/v1/agents/register", json={"name": "Rejecter"})
    voter_headers = {"Authorization": f"Bearer {r2.json()['data']['api_key']}"}

    r = await client.post(
        f"/api/v1/reviews/{post_id}/vote",
        json={"verdict": "reject"},
        headers=voter_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["verdict"] == "reject"
    assert data["total_downvotes"] == 1


async def test_cannot_vote_own_post(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    r = await client.post(
        f"/api/v1/reviews/{post['id']}/vote",
        json={"verdict": "approve"},
        headers=agent_headers,
    )
    assert r.status_code == 403


async def test_cannot_vote_twice(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    post_id = post["id"]

    r2 = await client.post("/api/v1/agents/register", json={"name": "DoubleVoter"})
    voter_headers = {"Authorization": f"Bearer {r2.json()['data']['api_key']}"}

    await client.post(
        f"/api/v1/reviews/{post_id}/vote",
        json={"verdict": "approve"},
        headers=voter_headers,
    )
    r = await client.post(
        f"/api/v1/reviews/{post_id}/vote",
        json={"verdict": "approve"},
        headers=voter_headers,
    )
    assert r.status_code == 409


async def test_post_approved_after_threshold_votes(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, db_session: AsyncSession
):
    """After review_threshold approve votes, post should be approved."""
    from sqlalchemy import select, update
    from app.models.config import BarConfig
    from app.models.bar import Bar
    from nanoid import generate

    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    post_id = post["id"]

    # Set threshold to 2 — update existing or insert if missing
    result = await db_session.execute(select(Bar).where(Bar.slug == bar["slug"]))
    bar_obj = result.scalar_one()
    existing = await db_session.execute(
        select(BarConfig).where(BarConfig.bar_id == bar_obj.id, BarConfig.key == "review_threshold")
    )
    cfg = existing.scalar_one_or_none()
    if cfg:
        cfg.value = 2
    else:
        db_session.add(BarConfig(id=generate(size=21), bar_id=bar_obj.id, key="review_threshold", value=2))
    await db_session.commit()

    # Two different agents approve
    final_status = "pending"
    for i in range(2):
        r = await client.post("/api/v1/agents/register", json={"name": f"ApproverT{i}"})
        h = {"Authorization": f"Bearer {r.json()['data']['api_key']}"}
        vote_r = await client.post(
            f"/api/v1/reviews/{post_id}/vote",
            json={"verdict": "approve"},
            headers=h,
        )
        assert vote_r.status_code == 200
        final_status = vote_r.json()["data"]["status"]

    assert final_status == "approved"


async def test_post_rejected_after_threshold_votes(
    client: AsyncClient, admin_headers: dict, agent_headers: dict, db_session: AsyncSession
):
    from sqlalchemy import select
    from app.models.config import BarConfig
    from app.models.bar import Bar
    from nanoid import generate

    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    post_id = post["id"]

    result = await db_session.execute(select(Bar).where(Bar.slug == bar["slug"]))
    bar_obj = result.scalar_one()
    existing = await db_session.execute(
        select(BarConfig).where(BarConfig.bar_id == bar_obj.id, BarConfig.key == "review_reject_threshold")
    )
    cfg = existing.scalar_one_or_none()
    if cfg:
        cfg.value = 2
    else:
        db_session.add(BarConfig(id=generate(size=21), bar_id=bar_obj.id, key="review_reject_threshold", value=2))
    await db_session.commit()

    final_status = "pending"
    for i in range(2):
        r = await client.post("/api/v1/agents/register", json={"name": f"RejecterT{i}"})
        h = {"Authorization": f"Bearer {r.json()['data']['api_key']}"}
        vote_r = await client.post(
            f"/api/v1/reviews/{post_id}/vote",
            json={"verdict": "reject"},
            headers=h,
        )
        assert vote_r.status_code == 200, vote_r.text
        final_status = vote_r.json()["data"]["status"]

    assert final_status == "rejected"


async def test_invalid_verdict(client: AsyncClient, admin_headers: dict, agent_headers: dict):
    bar, post = await _create_bar_and_post(client, admin_headers, agent_headers)
    r2 = await client.post("/api/v1/agents/register", json={"name": "BadVoter"})
    h = {"Authorization": f"Bearer {r2.json()['data']['api_key']}"}
    r = await client.post(
        f"/api/v1/reviews/{post['id']}/vote",
        json={"verdict": "maybe"},
        headers=h,
    )
    assert r.status_code == 400
